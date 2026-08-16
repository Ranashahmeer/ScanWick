/**
 * Sharing — prototype screens 42 (create share link) and 43 (manage
 * shares).
 *
 * The individual initiates every share; a lender can never pull. Each share
 * is a consent event that records who, when, what scope, which consent text
 * version and the expiry — and revocation is immediate, within the same
 * request cycle rather than on the next scheduled job.
 */

import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { AppShell, Screen } from "@/features/shell/app-shell";
import {
  Btn,
  Card,
  Check,
  Empty,
  Field,
  Hint,
  Inp,
  Row,
  ScreenHead,
  Select,
  Tbl,
} from "@/components/sw";

export type SharesView = "manage" | "create";

export function SharesPage({ view = "manage" }: { view?: SharesView }) {
  const navigate = useNavigate();

  return (
    <AppShell>
      <Screen>
        <ScreenHead
          title={view === "create" ? "Create share link" : "Manage shares"}
          meta={
            view === "create"
              ? "You generate it and you name the recipient"
              : "You can always see everything a lender can see about you"
          }
          tag="Sharing"
          action={
            view === "manage" ? (
              <Btn onClick={() => navigate({ to: "/shares", search: { view: "create" } })}>Create share link</Btn>
            ) : (
              <Btn tone="sec" sm onClick={() => navigate({ to: "/shares" })}>
                All shares
              </Btn>
            )
          }
        />
        {view === "create" ? <CreateShare /> : <ManageShares onCreate={() => navigate({ to: "/shares", search: { view: "create" } })} />}
      </Screen>
    </AppShell>
  );
}

/* ---------------------------------------------------------- screen 42 */

function CreateShare() {
  const [recipient, setRecipient] = useState("");
  const [email, setEmail] = useState("");
  const [expiry, setExpiry] = useState("14");
  const [includeDetail, setIncludeDetail] = useState(true);
  const [includeClassification, setIncludeClassification] = useState(false);

  return (
    <Row cols={2}>
      <Card title="Share your analysis" sub="You choose who sees it. You can revoke at any time.">
        <Field
          label="Who are you sharing with?"
          id="recipient"
          hint="Name the specific institution. The link only works for the recipient you name."
        >
          <Inp
            id="recipient"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            placeholder="e.g. a microfinance bank, named branch"
          />
        </Field>

        <Field label="Recipient email" id="recipient-email">
          <Inp
            id="recipient-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="credit@example-mfb.ng"
          />
        </Field>

        <Field label="Link expires" id="expiry">
          <Select id="expiry" value={expiry} onChange={(e) => setExpiry(e.target.value)}>
            <option value="7">7 days</option>
            <option value="14">14 days</option>
            <option value="30">30 days</option>
          </Select>
        </Field>

        <div className="field">
          <label>What they will see</label>
          <Check label="Your consolidated analysis and signals" checked disabled />
          <Check label="Source tiers, audit result and coverage" checked disabled />
          <Check
            label="Transaction-level detail behind each figure"
            checked={includeDetail}
            onChange={(e) => setIncludeDetail(e.target.checked)}
          />
          <Check
            label="Your business/personal classification"
            checked={includeClassification}
            onChange={(e) => setIncludeClassification(e.target.checked)}
          />
        </div>

        <div style={{ padding: 13, background: "var(--g50)", borderRadius: 8, fontSize: 12, color: "var(--ink2)", margin: "14px 0" }}>
          By creating this link you would be giving <b>{recipient || "the recipient you name"}</b> permission to view this
          analysis for {expiry} days. No other lender can see it. You can revoke it at any time, and we will tell you if
          it is opened.
        </div>

        <Btn disabled>Create link</Btn>
      </Card>

      <div>
        <Card title="Consent record" style={{ marginBottom: 14 }}>
          <table>
            <tbody>
              <tr>
                <td>Recipient</td>
                <td className="num">{recipient || "—"}</td>
              </tr>
              <tr>
                <td>Scope</td>
                <td className="num">
                  Analysis, coverage{includeDetail ? ", transactions" : ""}
                  {includeClassification ? ", classification" : ""}
                </td>
              </tr>
              <tr>
                <td>Expires</td>
                <td className="num">{expiry} days from creation</td>
              </tr>
              <tr>
                <td>Consent record</td>
                <td className="num mono">SHARE v1.3</td>
              </tr>
              <tr>
                <td>Revocable</td>
                <td className="num">Immediately, at any time</td>
              </tr>
            </tbody>
          </table>
        </Card>


      </div>
    </Row>
  );
}

/* ---------------------------------------------------------- screen 43 */

function ManageShares({ onCreate }: { onCreate: () => void }) {
  return (
    <>
      <Card title="Who you have shared with" sub="You can always see everything a lender can see about you">
        <Empty title="You have not shared with anyone" actionLabel="Create a share link" onAction={onCreate}>
          When you are ready, you choose the lender by name and can revoke at any time.
        </Empty>
      </Card>

      <Row cols={2} style={{ marginTop: 16 }}>
        <Card title="What revoking does">
          <div style={{ padding: 14, border: "1px solid #E9C6C6", borderRadius: 8, background: "var(--stopbg)" }}>
            <b style={{ fontSize: 12.5, color: "var(--stop)" }}>Revoking is immediate and cannot be undone</b>
            <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 7 }}>
              The recipient stops being able to open your analysis straight away. If they are in the middle of reviewing
              an application, this may affect their decision. To share again you would create a new link.
            </div>
          </div>
        </Card>

        <Card title="Consent trail" sub="Every event, retrievable">
          <Tbl>
            <table>
              <tbody>
                <tr>
                  <td colSpan={2} style={{ color: "var(--ink3)" }}>
                    No consent event has been recorded on this account beyond the account-connection consent given at
                    sign-up.
                  </td>
                </tr>
              </tbody>
            </table>
          </Tbl>
          <Hint style={{ marginTop: 10 }}>
            Consent text is versioned. If the wording changes you stay bound to the version you actually read.
          </Hint>
        </Card>
      </Row>
    </>
  );
}

export default SharesPage;
