/**
 * Surface 3 — monitoring. Prototype screens 45 (monitoring consent), 46
 * (portfolio), 47 (facility detail), 48 (signal detail) and 49
 * (acknowledge & record outcome).
 *
 * Monitoring requires a live connection: a borrower who uploads a file once
 * can be assessed but cannot be monitored, because there is no way to see
 * week two. No account in the system holds a live connection yet, so the
 * portfolio is genuinely empty rather than populated with illustrative
 * facilities — and a quiet portfolio must say when it last checked, or
 * silence reads as a broken feed.
 *
 * Signal wording never recommends declining, restructuring, calling in or
 * enforcing. Those are the lender's decisions.
 */

import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { AppShell, Screen } from "@/features/shell/app-shell";
import {
  Btn,
  Card,
  Empty,
  Field,
  Hint,
  Inp,
  Kpi,
  Pill,
  Row,
  ScreenHead,
  Select,
  Sev,
  Textarea,
} from "@/components/sw";
import { fmtDate } from "@/components/sw/format";

export type PortfolioView = "portfolio" | "consent" | "facility" | "signal" | "acknowledge";

const HEADINGS: Record<PortfolioView, { title: string; meta: string }> = {
  portfolio: { title: "Portfolio", meta: "Facilities under monitoring · sorted by severity" },
  consent: { title: "Monitoring consent", meta: "Two consents granted together at disbursement · connection and sharing" },
  facility: { title: "Facility detail", meta: "Every monitored metric against its disbursement baseline" },
  signal: { title: "Signal detail", meta: "Severity, evidence, recommended action and recommended timing" },
  acknowledge: { title: "Acknowledge & record outcome", meta: "Record what you did and what came of it" },
};

export function PortfolioPage({ view = "portfolio" }: { view?: PortfolioView }) {
  const heading = HEADINGS[view] ?? HEADINGS.portfolio;
  const navigate = useNavigate();

  return (
    <AppShell>
      <Screen>
        <ScreenHead title={heading.title} meta={heading.meta} tag="Surface 3" tagTone="s3" />
        {view === "consent" ? (
          <MonitoringConsent />
        ) : view === "facility" ? (
          <FacilityDetail />
        ) : view === "signal" ? (
          <SignalDetail />
        ) : view === "acknowledge" ? (
          <Acknowledge />
        ) : (
          <Portfolio onConsent={() => navigate({ to: "/portfolio", search: { view: "consent" } })} />
        )}
      </Screen>
    </AppShell>
  );
}

/* ---------------------------------------------------------- screen 46 */

function Portfolio({ onConsent }: { onConsent: () => void }) {
  const checkedAt = new Date();

  return (
    <>
      <Row cols={4} style={{ marginBottom: 16 }}>
        <Kpi label="Facilities monitored" value={0} detail="nothing disbursed under monitoring yet" />
        <Kpi label="Open signals" value={0} detail="0 urgent · 0 act · 0 watch" />
        <Kpi
          label="Acknowledged"
          value={<span style={{ fontSize: 16 }}>Not yet measurable</span>}
          detail="needs signals to have been raised"
        />
        <Kpi
          label="Outcome captured"
          value={<span style={{ fontSize: 16 }}>Not yet measurable</span>}
          detail="of acknowledged signals"
        />
      </Row>

      <Card title="Facilities needing attention" sub="Highest open signal first">
        <Empty title="Nothing needs attention" actionLabel="How monitoring starts" onAction={onConsent}>
          No facility is under monitoring, so there is nothing to watch. Monitoring begins when a borrower grants
          monitoring consent at disbursement and keeps an account connected.
        </Empty>
        <Hint style={{ marginTop: 10, textAlign: "center" }}>Last checked {fmtDate(checkedAt.toISOString())}</Hint>
      </Card>

      <Row cols={2} style={{ marginTop: 16 }}>
        <Card title="The eleven monitored metrics" sub="Each tracked against the baseline taken at disbursement">
          <table>
            <tbody>
              {[
                "Inflow level",
                "Inflow composition",
                "Balance trajectory",
                "Repayment — this facility",
                "Repayment — other obligations",
                "New borrowing",
                "Obligation load",
                "Contributory savings",
                "Account activity",
                "Consent state",
                "Statement audit per refresh",
              ].map((metric) => (
                <tr key={metric}>
                  <td>{metric}</td>
                  <td className="num">
                    <Pill tone="n">Awaiting a baseline</Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <div>
          <Card title="Severity, and what each one means" style={{ marginBottom: 14 }}>
            <table>
              <tbody>
                <tr>
                  <td>
                    <Sev level="i" />
                    Informational
                  </td>
                  <td>No action</td>
                </tr>
                <tr>
                  <td>
                    <Sev level="w" />
                    Watch
                  </td>
                  <td>Observe next cycle</td>
                </tr>
                <tr>
                  <td>
                    <Sev level="a" />
                    Act
                  </td>
                  <td>Contact within the stated days</td>
                </tr>
                <tr>
                  <td>
                    <Sev level="u" />
                    Urgent
                  </td>
                  <td>Immediate contact</td>
                </tr>
              </tbody>
            </table>
          </Card>


        </div>
      </Row>
    </>
  );
}

/* ---------------------------------------------------------- screen 45 */

function MonitoringConsent() {
  const [agreed, setAgreed] = useState(false);

  return (
    <div style={{ display: "flex", gap: 26, flexWrap: "wrap" }}>
      <div className="mob">
        <div className="bar2" />
        <div style={{ padding: 18 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 14 }}>
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
            Before your lender releases your loan
          </div>
          <div style={{ fontSize: 12, color: "var(--ink2)", lineHeight: 1.6, marginBottom: 13 }}>
            Two things are needed, and you are agreeing to both.
          </div>

          <div style={{ padding: 11, background: "var(--g50)", borderRadius: 8, fontSize: 11.5, lineHeight: 1.6, marginBottom: 10 }}>
            <b>1 · Keep your accounts connected</b>
            <br />
            Your accounts stay connected to Scanwick while the loan is outstanding. Read-only. We can never move your
            money.
          </div>
          <div style={{ padding: 11, background: "var(--g50)", borderRadius: 8, fontSize: 11.5, lineHeight: 1.6, marginBottom: 13 }}>
            <b>2 · Share signals with your lender</b>
            <br />
            They see changes in your income, balance, repayments, new borrowing and savings — not your individual
            transactions.
          </div>
          <div
            style={{
              padding: 11,
              background: "var(--warnbg)",
              borderRadius: 8,
              fontSize: 11.5,
              lineHeight: 1.6,
              marginBottom: 13,
              color: "#5C4A16",
            }}
          >
            <b>Until the loan is repaid, or the date your lender states.</b>
            <br />
            You can withdraw at any time. <b>If you do, or if an account disconnects, your lender is told.</b> We are
            saying this now so it is not a surprise later.
          </div>

          <label style={{ fontSize: 11.5, display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 12, cursor: "pointer" }}>
            <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} style={{ marginTop: 2 }} />
            <span>I agree to both.</span>
          </label>
          <Btn block disabled={!agreed}>
            Agree and connect accounts
          </Btn>
          <Hint style={{ textAlign: "center", marginTop: 10, fontSize: 10.5 }}>v1.3 · saved to your account</Hint>
        </div>
      </div>

      <div style={{ flex: 1, minWidth: 300 }}>
        <Card title="What happens if they refuse">
          <table>
            <tbody>
              <tr>
                <td>Can still be assessed</td>
                <td>
                  <Pill tone="a">Yes</Pill>
                </td>
              </tr>
              <tr>
                <td>Can still receive the loan</td>
                <td>
                  <Pill tone="a">Lender's decision</Pill>
                </td>
              </tr>
              <tr>
                <td>Can be monitored</td>
                <td>
                  <Pill tone="d">No</Pill>
                </td>
              </tr>
            </tbody>
          </table>
          <Hint style={{ marginTop: 10 }}>A borrower who will not connect cannot be monitored.</Hint>
        </Card>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------- screen 47 */

function FacilityDetail() {
  return (
    <>
      <Card title="No facility selected" style={{ marginBottom: 16 }}>
        <Empty title="No facility is under monitoring">
          A facility appears here once a loan has been disbursed against an assessment and the borrower has granted
          monitoring consent. Every figure on that screen is compared against the snapshot taken at disbursement.
        </Empty>
      </Card>

      <Card title="Coverage">
        <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>
          Monitoring only ever sees the accounts within its scope. Cash is invisible, and activity moved to an account
          outside that scope shows as dormancy rather than as an absence of risk.
        </div>
      </Card>
    </>
  );
}

/* ---------------------------------------------------------- screen 48 */

function SignalDetail() {
  return (
    <>
      <Card title="No signal selected" style={{ marginBottom: 16 }}>
        <Empty title="No signal has been raised">
          No facility is under monitoring, so nothing has been detected. When a signal is raised it names what changed,
          shows the transactions that evidence it, and states who to contact by when.
        </Empty>
      </Card>

    </>
  );
}

/* ---------------------------------------------------------- screen 49 */

const ACTIONS = [
  "Contacted borrower — spoke",
  "Contacted borrower — no response",
  "Escalated internally",
  "Verified with borrower, no concern",
  "No action taken",
];

const OUTCOMES = [
  "Explained satisfactorily — continue monitoring",
  "Restructured",
  "Repayment schedule changed",
  "Borrower uncontactable",
  "Went into arrears",
  "Too early to say",
];

function Acknowledge() {
  const [action, setAction] = useState(ACTIONS[0]);
  const [outcome, setOutcome] = useState(OUTCOMES[0]);
  const [when, setWhen] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");

  return (
    <Row cols={2}>
      <Card title="Record what you did" sub="Notes are optional">
        <Field label="Action taken" id="ack-action">
          <Select id="ack-action" value={action} onChange={(e) => setAction(e.target.value)}>
            {ACTIONS.map((option) => (
              <option key={option}>{option}</option>
            ))}
          </Select>
        </Field>

        <Field label="Date of action" id="ack-date">
          <Inp id="ack-date" type="date" value={when} onChange={(e) => setWhen(e.target.value)} />
        </Field>

        <Field label="What happened" id="ack-notes" optional>
          <Textarea id="ack-notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>

        <Field label="Outcome" id="ack-outcome">
          <Select id="ack-outcome" value={outcome} onChange={(e) => setOutcome(e.target.value)}>
            {OUTCOMES.map((option) => (
              <option key={option}>{option}</option>
            ))}
          </Select>
        </Field>

        <Btn disabled>Save outcome</Btn>
        <Hint style={{ marginTop: 10 }}>There is no signal to acknowledge yet.</Hint>
      </Card>

      <Card title="Signals, last 90 days">
        <table>
          <tbody>
            <tr>
              <td>Raised</td>
              <td className="num">0</td>
            </tr>
            <tr>
              <td>Acknowledged</td>
              <td className="num">—</td>
            </tr>
            <tr>
              <td>Outcome recorded</td>
              <td className="num">—</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </Row>
  );
}

export default PortfolioPage;
