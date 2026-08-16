/**
 * Consent centre — prototype screen 51.
 *
 * Six consent types. Each is separate, each has its own record, and each can
 * be withdrawn on its own. Bundling them into one tick is the exact failure
 * the design brief exists to prevent, so this screen always lists every type
 * — including the ones that have never been requested, shown greyed rather
 * than hidden, so a person can see what has *not* been asked of them.
 */

import { useNavigate } from "@tanstack/react-router";
import { AppShell, Screen } from "@/features/shell/app-shell";
import {
  Btn,
  Card,
  Hint,
  Pill,
  Row,
  ScreenHead,
  Tbl,
} from "@/components/sw";
import { fmtDate } from "@/components/sw/format";
import { useAuth } from "@/hooks/use-auth";
import { downloadDataExport } from "@/features/account/billing/privacy-api";

const CONSENT_TYPES = [
  {
    key: "ACCOUNT CONNECTION",
    what: "Scanwick may hold and read the statements you supply",
    granted: true,
    version: "v1.2",
  },
  {
    key: "ASSESSMENT",
    what: "Scanwick may analyse those statements into an assessment",
    granted: false,
    version: "v1.3",
  },
  {
    key: "SHARE TO NAMED RECIPIENT",
    what: "The result may go to one institution you name",
    granted: false,
    version: "v1.3",
  },
  {
    key: "MONITORING",
    what: "A named lender may see changes in your position after they lend",
    granted: false,
    version: "v1.3",
  },
  {
    key: "MONITORING EXTENSION",
    what: "Monitoring continues past the date first agreed",
    granted: false,
    version: "v1.3",
  },
  {
    key: "DATA RETENTION BEYOND DEFAULT",
    what: "Your data is kept longer than the 12-month default",
    granted: false,
    version: "v1.3",
  },
];

export function ConsentPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <AppShell>
      <Screen>
        <ScreenHead title="Consent centre" meta="Everything you have agreed to · and everything you have not" tag="Consent" />

        <Card
          title="Everything you have agreed to"
          sub="Six consent types. Each is separate, each has its own record, each can be withdrawn."
          style={{ marginBottom: 16 }}
        >
          <Tbl>
            <table className="stack">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>What it allows</th>
                  <th>When</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {CONSENT_TYPES.map((consent) => (
                  <tr key={consent.key} style={consent.granted ? undefined : { color: "var(--ink3)" }}>
                    <td data-l="Type">
                      <b>{consent.key}</b>
                    </td>
                    <td data-l="Allows">{consent.what}</td>
                    <td data-l="When" className="num">
                      {consent.granted ? fmtDate(new Date().toISOString()) : "—"}
                    </td>
                    <td data-l="Version" className="mono">
                      {consent.version}
                    </td>
                    <td data-l="Status">
                      {consent.granted ? <Pill tone="a">Active</Pill> : <Pill tone="n">Not requested</Pill>}
                    </td>
                    <td>
                      {consent.granted ? (
                        <Btn tone="dgr" sm onClick={() => navigate({ to: "/account", search: { tab: "delete" } })}>
                          Withdraw
                        </Btn>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Tbl>
          <Hint style={{ marginTop: 11 }}>
            The types you have not been asked for are listed too, greyed rather than hidden, so you can see what nobody
            has requested of you.
          </Hint>
        </Card>

        <Row cols={3}>
          <Card title="What each lender can see">
            <Hint>
              No lender can see anything about you that you did not grant to them by name. Nobody holds access to your
              analysis today.
            </Hint>
            <Btn tone="sec" sm block style={{ marginTop: 12 }} onClick={() => navigate({ to: "/shares" })}>
              Manage shares
            </Btn>
          </Card>

          <Card title="Your data rights" sub="Served from here, not an email queue. NDPA 2023.">
            <div style={{ display: "flex", flexDirection: "column", gap: 7, marginTop: 6 }}>
              <Btn tone="gho" sm style={{ justifyContent: "flex-start" }} onClick={() => void downloadDataExport()}>
                Download everything we hold
              </Btn>
              <Btn
                tone="gho"
                sm
                style={{ justifyContent: "flex-start" }}
                onClick={() => navigate({ to: "/account", search: { tab: "profile" } })}
              >
                Correct something
              </Btn>
              <Btn
                tone="gho"
                sm
                style={{ justifyContent: "flex-start" }}
                onClick={() => navigate({ to: "/audit", search: { view: "access-trail" } })}
              >
                See who has looked at your data
              </Btn>
              <Btn
                tone="dgr"
                sm
                style={{ justifyContent: "flex-start" }}
                onClick={() => navigate({ to: "/account", search: { tab: "delete" } })}
              >
                Delete my data
              </Btn>
            </div>
            {user?.deletion_requested_at ? (
              <Hint style={{ marginTop: 10, color: "var(--warn)" }}>
                Deletion is already scheduled for this account.
              </Hint>
            ) : null}
          </Card>

          <Card title="Read the exact text you agreed to">
            <table>
              <tbody>
                <tr>
                  <td className="mono">v1.2</td>
                  <td>Account connection</td>
                  <td>
                    <Btn tone="gho" sm onClick={() => navigate({ to: "/terms" })}>
                      Read
                    </Btn>
                  </td>
                </tr>
                <tr>
                  <td className="mono">v1.3</td>
                  <td>Assessment &amp; sharing</td>
                  <td>
                    <Btn tone="gho" sm onClick={() => navigate({ to: "/privacy" })}>
                      Read
                    </Btn>
                  </td>
                </tr>
              </tbody>
            </table>
            <Hint style={{ marginTop: 10 }}>
              Consent text is versioned. If the wording changes, you stay bound to the version you actually read.
            </Hint>
          </Card>
        </Row>


      </Screen>
    </AppShell>
  );
}

export default ConsentPage;
