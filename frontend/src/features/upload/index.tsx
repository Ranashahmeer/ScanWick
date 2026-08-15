import { ArrowLeft, ArrowUp } from "lucide-react";
import {
  type ChangeEvent,
  type DragEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { useNavigate } from "@tanstack/react-router";
import { isAxiosError } from "axios";
import { useScanwickChrome } from "@/features/landing/chrome";
import { useAuth } from "@/hooks/use-auth";
import { AppTopbar } from "./components/topbar";
import { DataQualityReportPage } from "./components/data-quality-report";
import { MappingReviewPage } from "./components/mapping-review";
import {
  FileReadyCard,
  PasswordUnlockPanel,
  ProcessingStages,
  RejectedPanel,
  SourceGuide,
  SourceHub,
  formatFileSize,
} from "./components/ingestion-panels";
import { BANK_SOURCES, getSourceById, type BankSource } from "./sources";
import {
  type MappingDetail,
  type NormalizedQualityData,
  UploadApiError,
  confirmMapping,
  detectDatasetType,
  normalizeQualityReport,
  pollQualityReport,
  uploadBankPdf,
  uploadCsv,
  uploadMono,
} from "./uploads-api";

type Screen =
  | "hub"
  | "statement"
  | "mono"
  | "csv"
  | "password"
  | "processing"
  | "rejected"
  | "mapping-review"
  | "review";

type AnalyzerType = "finance" | "commerce";

const analyzerTypes: { id: AnalyzerType; label: string }[] = [
  { id: "finance", label: "Finance" },
  { id: "commerce", label: "Commerce" },
];

const analyzerTypeToBackend: Record<AnalyzerType, "bank" | "ecommerce"> = {
  finance: "bank",
  commerce: "ecommerce",
};
const analyzerTypeToSource: Record<AnalyzerType, string | null> = {
  finance: null,
  commerce: "generic_csv",
};
const backendToAnalyzerType: Record<"bank" | "ecommerce", AnalyzerType> = {
  bank: "finance",
  ecommerce: "commerce",
};
const analyzerTypeToDashboardRoute: Record<AnalyzerType, string> = {
  finance: "/dashboard",
  commerce: "/commerce-intelligence",
};

const STATEMENT_ACCEPT = ".pdf,.csv,.xls,.xlsx,application/pdf,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

function MonoPanel({
  source,
  merchantId,
  onConnected,
  onBack,
}: {
  source: BankSource;
  merchantId: string;
  onConnected: () => void;
  onBack: () => void;
}) {
  const [monoAccountId, setMonoAccountId] = useState("");
  const [authorising, setAuthorising] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAuthorise = async () => {
    if (!monoAccountId.trim()) {
      setError("Enter a Mono account id to connect (the Connect widget isn't wired up yet).");
      return;
    }
    setAuthorising(true);
    setError(null);
    try {
      await uploadMono({ merchantId, monoAccountId: monoAccountId.trim() });
      onConnected();
    } catch (err) {
      setError(err instanceof UploadApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setAuthorising(false);
    }
  };

  return (
    <div className="upload-mono">
      <button type="button" className="ing-back" onClick={onBack}>
        <ArrowLeft size={14} strokeWidth={2.4} />
        All sources
      </button>
      <h3 className="ing-statement-title">Connect {source.label}</h3>
      <p className="upload-mono-intro">
        You will be taken to a secure page to sign in with your bank. Scanwick
        never sees your bank password. Connecting gives Tier A confidence.
      </p>
      <div className="upload-mono-authorize">
        <strong>Authorise {source.label} → Scanwick</strong>
        <span>Read-only access to statements &amp; balances</span>
        <p>
          The Mono Connect widget is not wired yet — enter a Mono account id
          (sandbox/test) to exercise the connection:
        </p>
        <input
          type="text"
          value={monoAccountId}
          onChange={(event) => setMonoAccountId(event.target.value)}
          placeholder="e.g. acc_ng_1"
          className="upload-mono-input"
        />
        <button type="button" className="upload-mono-connect" onClick={handleAuthorise} disabled={authorising}>
          {authorising ? "Connecting…" : `Authorise ${source.label}`}
        </button>
      </div>
      {error ? <div className="upload-mono-toast upload-mono-toast-error">{error}</div> : null}
    </div>
  );
}

function isAllowedStatementFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return (
    name.endsWith(".pdf") ||
    name.endsWith(".csv") ||
    name.endsWith(".xls") ||
    name.endsWith(".xlsx")
  );
}

export function UploadPage() {
  const { theme, toggleTheme } = useScanwickChrome();
  const navigate = useNavigate();
  const { user } = useAuth();
  const merchantId = user?.merchant_id ?? null;

  const [screen, setScreen] = useState<Screen>("hub");
  const [selectedSourceId, setSelectedSourceId] = useState(BANK_SOURCES[0].id);
  const selectedSource: BankSource = getSourceById(selectedSourceId) ?? BANK_SOURCES[0];

  const [analyzerType, setAnalyzerType] = useState<AnalyzerType>("finance");
  const [dropState, setDropState] = useState<"idle" | "dragging" | "error">("idle");
  const [errorHeading, setErrorHeading] = useState("");
  const [errorDetail, setErrorDetail] = useState("");
  const [rejectTitle, setRejectTitle] = useState("");
  const [rejectDetail, setRejectDetail] = useState("");
  const [fileName, setFileName] = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pdfPassword, setPdfPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSubmitting, setPasswordSubmitting] = useState(false);
  const [processStage, setProcessStage] = useState(0);
  const [uploadedAt, setUploadedAt] = useState<Date | null>(null);
  const [qualityData, setQualityData] = useState<NormalizedQualityData | null>(null);
  const [analysing, setAnalysing] = useState(false);

  const [mappingUploadId, setMappingUploadId] = useState<string | null>(null);
  const [mappingDetail, setMappingDetail] = useState<MappingDetail | null>(null);
  const [mappingIsBank, setMappingIsBank] = useState(false);
  const [mappingAnalyzerType, setMappingAnalyzerType] = useState<"ecommerce" | "bank">("ecommerce");
  const [confirmingMapping, setConfirmingMapping] = useState(false);
  const [mappingErrorMessage, setMappingErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadGenerationRef = useRef(0);
  const uploadAbortRef = useRef<AbortController | null>(null);
  const stageTimerRef = useRef<number | null>(null);

  const abortActiveUpload = () => {
    uploadGenerationRef.current += 1;
    uploadAbortRef.current?.abort();
    uploadAbortRef.current = null;
    if (stageTimerRef.current != null) {
      window.clearInterval(stageTimerRef.current);
      stageTimerRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      abortActiveUpload();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clearFileState = () => {
    abortActiveUpload();
    setDropState("idle");
    setErrorHeading("");
    setErrorDetail("");
    setRejectTitle("");
    setRejectDetail("");
    setFileName("");
    setPendingFile(null);
    setPdfPassword("");
    setPasswordError(null);
    setPasswordSubmitting(false);
    setProcessStage(0);
    setUploadedAt(null);
    setQualityData(null);
    setAnalysing(false);
    setMappingUploadId(null);
    setMappingDetail(null);
    setConfirmingMapping(false);
    setMappingErrorMessage(null);
  };

  const goHub = () => {
    clearFileState();
    setScreen("hub");
  };

  const openUploadForSource = (sourceId: string) => {
    clearFileState();
    setSelectedSourceId(sourceId);
    setScreen("statement");
  };

  const openConnectForSource = (sourceId: string) => {
    clearFileState();
    setSelectedSourceId(sourceId);
    setScreen("mono");
  };

  const startStageTicker = () => {
    setProcessStage(0);
    if (stageTimerRef.current != null) window.clearInterval(stageTimerRef.current);
    stageTimerRef.current = window.setInterval(() => {
      setProcessStage((current) => (current < 3 ? current + 1 : current));
    }, 1400);
  };

  const classifyUploadFailure = (error: unknown) => {
    if (error instanceof UploadApiError) {
      if (error.code === "PASSWORD_REQUIRED") return "password" as const;
      if (error.code === "WRONG_PASSWORD") return "wrong-password" as const;
      if (
        error.code === "PDF_UNREADABLE" ||
        error.code === "UNSUPPORTED_FILE_TYPE" ||
        error.code === "PARSE_FAILED" ||
        /could not (identify|read|open)/i.test(error.message) ||
        /no extractable text/i.test(error.message) ||
        /Unsupported bank/i.test(error.message) ||
        /could not read any transactions/i.test(error.message)
      ) {
        return "rejected" as const;
      }
      return "error" as const;
    }
    return "error" as const;
  };

  const selectStatementFile = (file: File) => {
    if (!isAllowedStatementFile(file)) {
      setErrorHeading("Wrong file type");
      setErrorDetail("We expected a PDF, CSV, XLS or XLSX file. Choose another file to continue.");
      setDropState("error");
      setPendingFile(null);
      setFileName("");
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setErrorHeading("File too large");
      setErrorDetail("That file is over the 20MB limit. Choose another file to continue.");
      setDropState("error");
      setPendingFile(null);
      setFileName("");
      return;
    }

    setPendingFile(file);
    setFileName(file.name);
    setDropState("idle");
    setErrorHeading("");
    setErrorDetail("");
  };

  const runPdfUpload = async (file: File, password: string | null) => {
    if (!merchantId) {
      setErrorHeading("Upload failed — no account");
      setErrorDetail("Your account isn't fully set up yet. Please sign out and back in, then try again.");
      setDropState("error");
      setScreen("statement");
      return;
    }

    setAnalysing(true);
    setScreen("processing");
    startStageTicker();

    const generation = uploadGenerationRef.current + 1;
    uploadGenerationRef.current = generation;
    const controller = new AbortController();
    uploadAbortRef.current = controller;
    const isStale = () => uploadGenerationRef.current !== generation;

    try {
      const uploadResult = await uploadBankPdf({
        file,
        merchantId,
        bankName: selectedSource.bankName,
        password,
        signal: controller.signal,
      });
      if (isStale()) return;

      const report = await pollQualityReport(uploadResult.uploadId, true, { signal: controller.signal });
      if (isStale()) return;

      const normalized = normalizeQualityReport(report, true);
      if ((normalized.rowsParsed ?? 0) === 0 && (normalized.rowsRejected ?? 0) === 0) {
        setRejectTitle("This statement has no transactions");
        setRejectDetail(
          `The file read correctly for ${selectedSource.label}. The account simply had no activity in this period — an empty month is not ₦0 income.`,
        );
        setScreen("rejected");
        return;
      }

      setQualityData(normalized);
      setUploadedAt(new Date());
      setScreen("review");
    } catch (error) {
      if (isStale()) return;
      const kind = classifyUploadFailure(error);
      if (kind === "password" || kind === "wrong-password") {
        setPasswordError(
          kind === "wrong-password"
            ? error instanceof UploadApiError
              ? error.message
              : "Wrong password"
            : null,
        );
        setPdfPassword("");
        setScreen("password");
        return;
      }
      if (kind === "rejected") {
        setRejectTitle("We could not read this statement");
        setRejectDetail(
          error instanceof UploadApiError
            ? error.message
            : "Because we could not read the file reliably, we stopped rather than guess.",
        );
        setScreen("rejected");
        return;
      }
      setErrorHeading("Upload failed");
      setErrorDetail(error instanceof UploadApiError ? error.message : "Something went wrong. Please try again.");
      setDropState("error");
      setScreen("statement");
    } finally {
      if (stageTimerRef.current != null) {
        window.clearInterval(stageTimerRef.current);
        stageTimerRef.current = null;
      }
      setPasswordSubmitting(false);
      setAnalysing(false);
    }
  };

  const runCsvUpload = async (file: File) => {
    if (!merchantId) {
      setErrorHeading("Upload failed — no account");
      setErrorDetail("Your account isn't fully set up yet. Please sign out and back in, then try again.");
      setDropState("error");
      return;
    }

    setScreen("processing");
    startStageTicker();

    const generation = uploadGenerationRef.current + 1;
    uploadGenerationRef.current = generation;
    const controller = new AbortController();
    uploadAbortRef.current = controller;
    const isStale = () => uploadGenerationRef.current !== generation;

    try {
      let effectiveAnalyzerType = analyzerType;
      let effectiveSource = analyzerTypeToSource[analyzerType];

      try {
        const detection = await detectDatasetType(file, controller.signal);
        if (isStale()) return;
        if (detection.analyzerType && detection.confidence >= 0.4) {
          effectiveAnalyzerType = backendToAnalyzerType[detection.analyzerType];
          effectiveSource = detection.source ?? analyzerTypeToSource[effectiveAnalyzerType];
          setAnalyzerType(effectiveAnalyzerType);
        }
      } catch (error) {
        if (isAxiosError(error) && error.code === "ERR_CANCELED") throw error;
      }

      const isBank = effectiveAnalyzerType === "finance";
      const uploadResult = await uploadCsv({
        file,
        merchantId,
        analyzerType: analyzerTypeToBackend[effectiveAnalyzerType],
        source: effectiveSource,
        bankName: isBank ? selectedSource.bankName : null,
        signal: controller.signal,
      });

      const csvResult = uploadResult as { uploadId: string; status?: string; mapping?: MappingDetail };
      if (csvResult.status === "needs_mapping" && csvResult.mapping) {
        setMappingUploadId(uploadResult.uploadId);
        setMappingDetail(csvResult.mapping);
        setMappingIsBank(isBank);
        setMappingAnalyzerType(analyzerTypeToBackend[effectiveAnalyzerType]);
        setScreen("mapping-review");
        return;
      }

      const report = await pollQualityReport(uploadResult.uploadId, isBank, { signal: controller.signal });
      if (isStale()) return;

      setQualityData(normalizeQualityReport(report, isBank));
      setUploadedAt(new Date());
      setScreen("review");
    } catch (error) {
      if (isStale()) return;
      setErrorHeading("Upload failed");
      setErrorDetail(error instanceof UploadApiError ? error.message : "Something went wrong. Please try again.");
      setDropState("error");
      setScreen("csv");
    } finally {
      if (stageTimerRef.current != null) {
        window.clearInterval(stageTimerRef.current);
        stageTimerRef.current = null;
      }
    }
  };

  const analysePendingFile = async () => {
    if (!pendingFile) return;
    const name = pendingFile.name.toLowerCase();
    if (name.endsWith(".pdf")) {
      await runPdfUpload(pendingFile, null);
      return;
    }
    // CSV / Excel for this source — route through CSV ingest
    setAnalyzerType("finance");
    await runCsvUpload(pendingFile);
  };

  const handleConfirmMapping = async (mapping: Record<string, string>, valueRules: Record<string, string>) => {
    if (!mappingUploadId) return;
    const generation = uploadGenerationRef.current;
    const isStale = () => uploadGenerationRef.current !== generation;

    setConfirmingMapping(true);
    setMappingErrorMessage(null);
    try {
      await confirmMapping({ uploadId: mappingUploadId, mapping, valueRules });
      if (isStale()) return;

      setScreen("processing");
      startStageTicker();
      const report = await pollQualityReport(mappingUploadId, mappingIsBank, {});
      if (isStale()) return;

      setQualityData(normalizeQualityReport(report, mappingIsBank));
      setUploadedAt(new Date());
      setScreen("review");
    } catch (error) {
      if (isStale()) return;
      setMappingErrorMessage(
        error instanceof UploadApiError ? error.message : "Something went wrong. Please try again.",
      );
    } finally {
      if (!isStale()) setConfirmingMapping(false);
      if (stageTimerRef.current != null) {
        window.clearInterval(stageTimerRef.current);
        stageTimerRef.current = null;
      }
    }
  };

  const handleBrowse = () => fileInputRef.current?.click();

  const handleFileInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (screen === "csv") {
      void runCsvUpload(file);
      return;
    }
    selectStatementFile(file);
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (screen === "statement" || screen === "csv") setDropState("dragging");
  };

  const handleDragLeave = () => {
    setDropState((current) => (current === "dragging" ? "idle" : current));
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (!file) return;
    if (screen === "csv") {
      void runCsvUpload(file);
      return;
    }
    selectStatementFile(file);
  };

  if (screen === "mapping-review" && mappingDetail) {
    return (
      <MappingReviewPage
        theme={theme}
        onToggleTheme={toggleTheme}
        analyzerType={mappingAnalyzerType}
        mapping={mappingDetail}
        confirming={confirmingMapping}
        errorMessage={mappingErrorMessage}
        onConfirm={handleConfirmMapping}
        onCancel={goHub}
      />
    );
  }

  if (screen === "review" && qualityData) {
    return (
      <DataQualityReportPage
        theme={theme}
        onToggleTheme={toggleTheme}
        fileName={fileName}
        uploadedAt={uploadedAt}
        formatTab={pendingFile?.name.toLowerCase().endsWith(".pdf") ? "pdf" : "csv"}
        analyzerType={analyzerType}
        report={qualityData}
        onProceed={() => navigate({ to: analyzerTypeToDashboardRoute[analyzerType] })}
        onFixReupload={() => openUploadForSource(selectedSourceId)}
      />
    );
  }

  const stepperStep1 =
    screen === "hub" ? "on" : screen === "processing" || screen === "review" || screen === "statement" || screen === "password" || screen === "rejected" || screen === "mono" ? "done" : "on";
  const stepperStep2 = screen === "processing" ? "on" : screen === "review" ? "done" : "";
  const stepperStep3 = screen === "review" ? "on" : "";

  return (
    <main className={`scanwick-page upload-page ${theme === "light" ? "theme-light" : ""}`}>
      <AppTopbar theme={theme} onToggleTheme={toggleTheme} onReset={goHub} />

      <section className="upload-main">
        <div className="upload-inner upload-inner-wide">
          <div className="upload-heading">
            <h1>
              {screen === "hub"
                ? "Add accounts"
                : screen === "statement" || screen === "password" || screen === "rejected"
                  ? "Upload statement"
                  : screen === "mono"
                    ? "Connect account"
                    : screen === "csv"
                      ? "CSV upload"
                      : screen === "processing"
                        ? "Processing"
                        : "Add accounts"}
            </h1>
            <p>
              {screen === "hub"
                ? "13 sources · connect by API where available, upload a file otherwise"
                : screen === "statement"
                  ? "PDF, XLS, XLSX or CSV · including password-protected files"
                  : screen === "mono"
                    ? `Tier A · live connection for ${selectedSource.label}`
                    : "Bring in a statement or store export. Every upload is validated before you see a dashboard."}
            </p>
          </div>

          <div className="ing-stepper" aria-label="Ingestion steps">
            <div className={stepperStep1}>1 · Add accounts</div>
            <div className={stepperStep2}>2 · Processing</div>
            <div className={stepperStep3}>3 · Review coverage</div>
            <div>4 · Your money</div>
          </div>

          <div className="upload-card">
            {screen === "hub" ? (
              <>
                <div className="ing-hub-toolbar">
                  <button type="button" className="ing-btn ing-btn-ghost" onClick={() => { clearFileState(); setScreen("csv"); }}>
                    CSV / commerce upload
                  </button>
                </div>
                <SourceHub
                  sources={BANK_SOURCES}
                  onUpload={openUploadForSource}
                  onConnect={openConnectForSource}
                />
              </>
            ) : null}

            {screen === "mono" && merchantId ? (
              <MonoPanel
                source={selectedSource}
                merchantId={merchantId}
                onConnected={() => navigate({ to: "/dashboard" })}
                onBack={goHub}
              />
            ) : null}

            {screen === "mono" && !merchantId ? (
              <p className="upload-mono-intro">
                Your account isn't fully set up yet. Please sign out and back in, then try again.
              </p>
            ) : null}

            {screen === "processing" ? (
              <ProcessingStages
                fileName={fileName}
                sourceLabel={selectedSource.label}
                stageIndex={processStage}
              />
            ) : null}

            {screen === "password" && pendingFile ? (
              <PasswordUnlockPanel
                source={selectedSource}
                fileName={fileName}
                password={pdfPassword}
                error={passwordError}
                submitting={passwordSubmitting}
                onPasswordChange={setPdfPassword}
                onSubmit={() => {
                  setPasswordSubmitting(true);
                  void runPdfUpload(pendingFile, pdfPassword);
                }}
                onCancel={() => {
                  setScreen("statement");
                  setPasswordError(null);
                  setPdfPassword("");
                }}
              />
            ) : null}

            {screen === "rejected" ? (
              <RejectedPanel
                title={rejectTitle || "We could not read this statement"}
                detail={rejectDetail}
                actions={[
                  {
                    label: "Upload a different file",
                    onClick: () => openUploadForSource(selectedSourceId),
                    primary: true,
                  },
                  { label: "Choose another source", onClick: goHub, primary: false },
                ]}
              />
            ) : null}

            {screen === "statement" ? (
              <div className="ing-layout-split">
                <div className="ing-layout-main">
                  <button type="button" className="ing-back" onClick={goHub}>
                    <ArrowLeft size={14} strokeWidth={2.4} />
                    All sources
                  </button>
                  <h3 className="ing-statement-title">Upload your {selectedSource.label} statement</h3>
                  <p className="ing-statement-sub">
                    Download it from your bank app or internet banking, then drop it here.
                  </p>

                  {!pendingFile || dropState === "error" ? (
                    <div
                      className={`upload-dropzone upload-dropzone-${dropState}`}
                      role="button"
                      tabIndex={0}
                      onClick={handleBrowse}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") handleBrowse();
                      }}
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                    >
                      <ArrowUp size={26} strokeWidth={2.2} />
                      <strong>
                        {dropState === "dragging"
                          ? "Release to upload"
                          : dropState === "error"
                            ? errorHeading
                            : "Drop your statement here"}
                      </strong>
                      {dropState !== "error" ? (
                        <span>or click to browse — PDF, XLS, XLSX, CSV up to 20MB</span>
                      ) : (
                        <span>{errorDetail}</span>
                      )}
                      {dropState === "error" ? (
                        <button
                          type="button"
                          className="upload-choose-another"
                          onClick={(event) => {
                            event.stopPropagation();
                            setDropState("idle");
                            setErrorHeading("");
                            setErrorDetail("");
                          }}
                        >
                          Choose another file
                        </button>
                      ) : null}
                    </div>
                  ) : (
                    <FileReadyCard
                      fileName={fileName}
                      fileSizeLabel={formatFileSize(pendingFile.size)}
                      analysing={analysing}
                      onAnalyse={() => void analysePendingFile()}
                      onClear={() => {
                        setPendingFile(null);
                        setFileName("");
                        setDropState("idle");
                      }}
                    />
                  )}
                </div>
                <SourceGuide source={selectedSource} />
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={STATEMENT_ACCEPT}
                  className="upload-hidden-input"
                  onChange={handleFileInputChange}
                  aria-label="Upload a statement file"
                />
              </div>
            ) : null}

            {screen === "csv" ? (
              <div>
                <button type="button" className="ing-back" onClick={goHub}>
                  <ArrowLeft size={14} strokeWidth={2.4} />
                  All sources
                </button>
                <div className="upload-analyzer-row">
                  <span className="upload-analyzer-label">Analyzer type</span>
                  <div className="upload-analyzer-pills" role="radiogroup" aria-label="Analyzer type">
                    {analyzerTypes.map((analyzer) => (
                      <button
                        key={analyzer.id}
                        type="button"
                        role="radio"
                        aria-checked={analyzerType === analyzer.id}
                        className={`upload-pill ${analyzerType === analyzer.id ? "is-active" : ""}`}
                        onClick={() => setAnalyzerType(analyzer.id)}
                      >
                        {analyzer.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div
                  className={`upload-dropzone upload-dropzone-${dropState}`}
                  role="button"
                  tabIndex={0}
                  onClick={handleBrowse}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") handleBrowse();
                  }}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <ArrowUp size={26} strokeWidth={2.2} />
                  <strong>
                    {dropState === "dragging"
                      ? "Release to upload"
                      : dropState === "error"
                        ? errorHeading
                        : "Drag & drop, or click to browse"}
                  </strong>
                  {dropState !== "error" ? (
                    <span>
                      {analyzerType === "finance"
                        ? "CSV up to 10MB · bank transactions export"
                        : "CSV up to 10MB · store orders export"}
                    </span>
                  ) : (
                    <span>{errorDetail}</span>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  className="upload-hidden-input"
                  onChange={handleFileInputChange}
                  aria-label="Upload a CSV file"
                />
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </main>
  );
}
