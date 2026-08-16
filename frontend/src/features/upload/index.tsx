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
import { useAuth } from "@/hooks/use-auth";
import { AppShell, Screen as ScreenFrame } from "@/features/shell/app-shell";
import { Btn, Card, Hint, Row, ScreenHead, Stepper } from "@/components/sw";
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
      setError("Enter your account reference to continue.");
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

  // Prototype screen 14 — connect by API. This screen is the gate on
  // Surface 3: post-disbursement monitoring is only possible on a connected
  // account, so it has to earn the connection rather than merely offer it.
  return (
    <>
      <button type="button" className="btn gho sm" style={{ marginBottom: 14 }} onClick={onBack}>
        <ArrowLeft size={14} strokeWidth={2.4} />
        All sources
      </button>

      <div style={{ display: "flex", gap: 26, flexWrap: "wrap" }}>
        <div className="mob">
          <div className="bar2" />
          <div style={{ padding: 18 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 16 }}>
              <div
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: 5,
                  background: "var(--g800)",
                  color: "#fff",
                  display: "grid",
                  placeItems: "center",
                  fontWeight: 800,
                  fontSize: 11,
                }}
              >
                S
              </div>
              <b style={{ fontSize: 12.5 }}>Scanwick</b>
            </div>

            <div style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.35, marginBottom: 9 }}>
              Connect your {source.label} account
            </div>
            <div style={{ fontSize: 12, color: "var(--ink2)", lineHeight: 1.6, marginBottom: 14 }}>
              You will be taken to a secure page to sign in with your bank. Scanwick never sees your bank password.
            </div>

            <div
              style={{
                padding: 11,
                background: "var(--g50)",
                borderRadius: 8,
                fontSize: 11.5,
                lineHeight: 1.65,
                marginBottom: 14,
              }}
            >
              <b>What we will be able to read:</b>
              <br />• Your account balance
              <br />• Your transaction history
              <br />• Your account name and number
              <br />
              <br />
              <b>What we will never be able to do:</b>
              <br />• Move money
              <br />• Make a payment
              <br />• Change anything in your account
            </div>

            <div className="field">
              <label htmlFor="mono-account">Account reference</label>
              <input
                id="mono-account"
                type="text"
                className="inp"
                value={monoAccountId}
                onChange={(event) => setMonoAccountId(event.target.value)}
                placeholder="e.g. acc_ng_1"
              />
            </div>

            <Btn block style={{ marginBottom: 8 }} onClick={handleAuthorise} disabled={authorising}>
              {authorising ? "Connecting…" : "Continue to my bank"}
            </Btn>
            <Btn tone="gho" sm block onClick={onBack}>
              Upload a statement instead
            </Btn>
            <Hint style={{ textAlign: "center", marginTop: 11, fontSize: 10.5 }}>
              Read-only access · you can disconnect any time
            </Hint>

            {error ? (
              <div
                role="alert"
                style={{
                  marginTop: 12,
                  padding: 10,
                  background: "var(--stopbg)",
                  border: "1px solid #E9C6C6",
                  borderRadius: 8,
                  fontSize: 11.5,
                  color: "var(--stop)",
                }}
              >
                {error}
              </div>
            ) : null}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 300 }}>
          <Card title="Why connect rather than upload" style={{ marginBottom: 14 }}>
            <table>
              <thead>
                <tr>
                  <th />
                  <th>Connected</th>
                  <th>Uploaded file</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Source tier</td>
                  <td>
                    <span className="pill a">A</span>
                  </td>
                  <td>
                    <span className="pill b">B</span>
                  </td>
                </tr>
                <tr>
                  <td>Effort per refresh</td>
                  <td>None</td>
                  <td>Download and upload each time</td>
                </tr>
                <tr>
                  <td>Always current</td>
                  <td>Yes</td>
                  <td>As at the file date</td>
                </tr>
                <tr>
                  <td>
                    <b>Can support monitoring</b>
                  </td>
                  <td>
                    <b>Yes</b>
                  </td>
                  <td>
                    <b>No</b>
                  </td>
                </tr>
                <tr>
                  <td>Works with all 13 sources</td>
                  <td>Yes</td>
                  <td>Yes</td>
                </tr>
              </tbody>
            </table>
          </Card>


        </div>
      </div>
    </>
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

  // 1 Add accounts · 2 Processing · 3 Review coverage · 4 Your money —
  // the prototype's stepper, shown on every ingestion screen.
  const currentStep = screen === "processing" ? 1 : screen === "review" ? 2 : 0;

  const heading =
    screen === "hub"
      ? { title: "Add accounts", meta: "13 sources · connect by API where available, upload a file otherwise" }
      : screen === "statement"
        ? { title: "Upload statement", meta: "PDF, XLS, XLSX or CSV · including password-protected files" }
        : screen === "password"
          ? { title: "Password-protected PDF", meta: "Common in Nigeria — most banks email statements locked" }
          : screen === "rejected"
            ? { title: "Rejected", meta: "Nothing was analysed from this file" }
            : screen === "mono"
              ? { title: "Connect account", meta: `Tier A · live connection for ${selectedSource.label}` }
              : screen === "csv"
                ? { title: "CSV upload", meta: "A transactions or orders export, mapped column by column" }
                : { title: "Processing", meta: "You can leave this page — we will email you when it is ready" };

  return (
    <AppShell>
      <ScreenFrame>
        <ScreenHead title={heading.title} meta={heading.meta} tag="Ingestion" />
        <Stepper steps={["Add accounts", "Processing", "Review coverage", "Your money"]} current={currentStep} />

        <div>
            {screen === "hub" ? (
              <>
                <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 14 }}>
                  <Btn
                    tone="gho"
                    sm
                    onClick={() => {
                      clearFileState();
                      setScreen("csv");
                    }}
                  >
                    CSV / commerce upload
                  </Btn>
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
              <Card>
                <Hint>Your account isn't fully set up yet. Please sign out and back in, then try again.</Hint>
              </Card>
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
              <>
                <Btn tone="gho" sm style={{ marginBottom: 14 }} onClick={goHub}>
                  <ArrowLeft size={14} strokeWidth={2.4} />
                  All sources
                </Btn>
                <Row cols="21">
                  <Card
                    title={`Upload your ${selectedSource.label} statement`}
                    sub="Download it from your bank app or internet banking, then drop it here."
                  >
                    {!pendingFile || dropState === "error" ? (
                      <div
                        className="ph"
                        style={{
                          height: 170,
                          flexDirection: "column",
                          gap: 9,
                          cursor: "pointer",
                          borderColor: dropState === "error" ? "var(--stop)" : undefined,
                          borderStyle: dropState === "dragging" ? "solid" : "dashed",
                          background: dropState === "error" ? "var(--stopbg)" : undefined,
                        }}
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
                        <b style={{ color: dropState === "error" ? "var(--stop)" : "var(--ink)" }}>
                          {dropState === "dragging"
                            ? "Release to upload"
                            : dropState === "error"
                              ? errorHeading
                              : "Drop your statement here"}
                        </b>
                        <span>
                          {dropState !== "error"
                            ? "or click to browse — PDF, XLS, XLSX, CSV up to 20MB"
                            : errorDetail}
                        </span>
                        {dropState === "error" ? (
                          <Btn
                            sm
                            tone="sec"
                            onClick={(event) => {
                              event.stopPropagation();
                              setDropState("idle");
                              setErrorHeading("");
                              setErrorDetail("");
                            }}
                          >
                            Choose another file
                          </Btn>
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
                  </Card>
                  <SourceGuide source={selectedSource} />
                </Row>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={STATEMENT_ACCEPT}
                  style={{ display: "none" }}
                  onChange={handleFileInputChange}
                  aria-label="Upload a statement file"
                />
              </>
            ) : null}

            {screen === "csv" ? (
              <>
                <Btn tone="gho" sm style={{ marginBottom: 14 }} onClick={goHub}>
                  <ArrowLeft size={14} strokeWidth={2.4} />
                  All sources
                </Btn>
                <Row cols="21">
                  <Card
                    title="Upload a CSV export"
                    sub="A transactions export from a bank, or an orders export from your shop."
                  >
                    <div className="field">
                      <label>What is in this file?</label>
                      <div role="radiogroup" aria-label="Analyzer type" style={{ display: "flex", gap: 8 }}>
                        {analyzerTypes.map((analyzer) => (
                          <button
                            key={analyzer.id}
                            type="button"
                            role="radio"
                            aria-checked={analyzerType === analyzer.id}
                            className={`btn sm ${analyzerType === analyzer.id ? "" : "gho"}`}
                            onClick={() => setAnalyzerType(analyzer.id)}
                          >
                            {analyzer.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div
                      className="ph"
                      style={{
                        height: 170,
                        flexDirection: "column",
                        gap: 9,
                        cursor: "pointer",
                        borderColor: dropState === "error" ? "var(--stop)" : undefined,
                        borderStyle: dropState === "dragging" ? "solid" : "dashed",
                        background: dropState === "error" ? "var(--stopbg)" : undefined,
                      }}
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
                      <b style={{ color: dropState === "error" ? "var(--stop)" : "var(--ink)" }}>
                        {dropState === "dragging"
                          ? "Release to upload"
                          : dropState === "error"
                            ? errorHeading
                            : "Drop your CSV here"}
                      </b>
                      <span>
                        {dropState !== "error"
                          ? analyzerType === "finance"
                            ? "or click to browse — CSV up to 10MB · bank transactions export"
                            : "or click to browse — CSV up to 10MB · store orders export"
                          : errorDetail}
                      </span>
                    </div>
                  </Card>


                </Row>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  style={{ display: "none" }}
                  onChange={handleFileInputChange}
                  aria-label="Upload a CSV file"
                />
              </>
            ) : null}
        </div>
      </ScreenFrame>
    </AppShell>
  );
}
