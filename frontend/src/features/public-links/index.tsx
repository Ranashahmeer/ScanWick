/**
 * Public link surfaces — prototype screens 44 (recipient view) and 52
 * (consent request).
 *
 * Neither needs a Scanwick account. On the recipient view, provenance is
 * the second thing on the page, above the analysis, because a credit
 * officer's first question about a third party is how the data was gathered
 * and how confirmed it is — that belongs in a seal at the top, not in a
 * methodology appendix.
 *
 * The consent request is where most borrowers meet Scanwick, on a phone,
 * mid-application. Short sentences, no legal register, and the two things
 * that protect the borrower — one named recipient, and withdrawal at any
 * time — given equal weight to the agreement itself.
 */

import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { PublicShell } from "@/features/shell/app-shell";
import { Btn, Card, Hint, Kpi, Na, Pill, Row } from "@/components/sw";
import { Footer, Header, Mark } from "@/features/landing/chrome";

/* ---------------------------------------------------------- screen 44 */

export function RecipientView({ reference }: { reference: string }) {
  return (
    <PublicShell>
      <Header />
      <div style={{ padding: "26px 24px 60px", maxWidth: 1000, margin: "0 auto" }}>
        <Card style={{ padding: 0, overflow: "hidden" }}>
          {/* The verification header reads as a seal, not a disclaimer. */}
          <div
            style={{
              padding: "18px 24px",
              background: "var(--g50)",
              borderBottom: "1px solid var(--line)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 16,
              flexWrap: "wrap",
            }}
          >
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <Mark />
              <div>
                <b style={{ fontSize: 13 }}>Verified by Scanwick</b>
                <Hint>Generated from the account holder's own statements</Hint>
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="mono" style={{ fontSize: 11 }}>
                Ref {reference}
              </div>
              <Hint>Shared with a named recipient only</Hint>
            </div>
          </div>

          <div style={{ padding: "22px 24px" }}>
            <div
              style={{
                padding: 14,
                border: "1px solid #E4C77E",
                background: "var(--warnbg)",
                borderRadius: 8,
                marginBottom: 16,
              }}
            >
              <b style={{ fontSize: 12.5, color: "#5C4A16" }}>This link could not be opened</b>
              <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 6 }}>
                There is no analysis behind this reference. If you were expecting one, ask the person who sent it to
                generate a new link.
              </div>
            </div>

            <Row cols={4} style={{ marginBottom: 16 }}>
              <Kpi card={false} label="Turnover /mo" value={<Na reason="No analysis is attached to this link." />} valueStyle={{ fontSize: 15 }} />
              <Kpi card={false} label="Avg balance" value={<Na reason="No analysis is attached to this link." />} valueStyle={{ fontSize: 15 }} />
              <Kpi card={false} label="Debt service" value={<Na reason="No analysis is attached to this link." />} valueStyle={{ fontSize: 15 }} />
              <Kpi card={false} label="Accounts" value={<Na reason="No analysis is attached to this link." />} valueStyle={{ fontSize: 15 }} />
            </Row>

          </div>
        </Card>



        <div style={{ marginTop: 16, textAlign: "center" }}>
          <Link to="/contact" className="btn sec sm">
            Ask us about this link
          </Link>
        </div>
      </div>
      <Footer />
    </PublicShell>
  );
}

/* ---------------------------------------------------------- screen 52 */

export function ConsentRequestView({ token }: { token: string }) {
  const [decision, setDecision] = useState<"pending" | "agreed" | "declined">("pending");

  return (
    <PublicShell>
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "32px 20px 56px",
          gap: 26,
          flexWrap: "wrap",
        }}
      >
        <div className="mob">
          <div className="bar2" />
          <div style={{ padding: 18 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 16 }}>
              <Mark size={22} />
              <b style={{ fontSize: 12.5 }}>Scanwick</b>
            </div>

            {decision === "agreed" ? (
              <>
                <div style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.35, marginBottom: 9 }}>
                  Thank you — your consent is recorded
                </div>
                <div style={{ fontSize: 12, color: "var(--ink2)", lineHeight: 1.6, marginBottom: 14 }}>
                  Nothing about your money has been shared yet. The next step is providing your statements, and you can
                  withdraw this at any time from your Scanwick account.
                </div>
                <Link to="/register" className="btn blk">
                  Create my account
                </Link>
              </>
            ) : decision === "declined" ? (
              <>
                <div style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.35, marginBottom: 9 }}>
                  That is fine — nothing has happened
                </div>
                <div style={{ fontSize: 12, color: "var(--ink2)", lineHeight: 1.6, marginBottom: 14 }}>
                  No statement has been analysed and nothing has been shared. Whoever asked will need to speak to you
                  directly about your application. You can change your mind by asking them for a fresh link.
                </div>
                <Btn tone="gho" sm block onClick={() => setDecision("pending")}>
                  Go back
                </Btn>
              </>
            ) : (
              <>
                <div style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.35, marginBottom: 9 }}>
                  A lender wants to review your bank statements
                </div>
                <div style={{ fontSize: 12, color: "var(--ink2)", lineHeight: 1.6, marginBottom: 14 }}>
                  You applied for a loan. To assess it, they have asked Scanwick to analyse the statements you provide.
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
                  <b>You are agreeing that:</b>
                  <br />• Scanwick may analyse the statements you upload
                  <br />• The result is shared with <b>that lender only</b>
                  <br />• No other lender can see it
                  <br />• This expires in 30 days
                  <br />• You can withdraw it at any time
                </div>

                <div style={{ fontSize: 11.5, color: "var(--ink2)", marginBottom: 14 }}>
                  <b>This does not include monitoring.</b> If they lend to you, they will ask separately about tracking
                  your accounts afterwards.
                </div>

                <Btn block style={{ marginBottom: 8 }} onClick={() => setDecision("agreed")}>
                  I agree
                </Btn>
                <Btn tone="gho" sm block onClick={() => setDecision("declined")}>
                  Not now
                </Btn>
                <Hint style={{ textAlign: "center", marginTop: 11, fontSize: 10.5 }}>
                  Consent text v1.3 · reference <span className="mono">{token.slice(0, 8)}</span>
                </Hint>
              </>
            )}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 300, maxWidth: 420 }}>


          <Card title="What Scanwick will never do">
            <table>
              <tbody>
                <tr>
                  <td>Move money from your account</td>
                  <td className="num">
                    <Pill tone="d">Never</Pill>
                  </td>
                </tr>
                <tr>
                  <td>Give you or the lender a credit score</td>
                  <td className="num">
                    <Pill tone="d">Never</Pill>
                  </td>
                </tr>
                <tr>
                  <td>Share with a lender you did not name</td>
                  <td className="num">
                    <Pill tone="d">Never</Pill>
                  </td>
                </tr>
                <tr>
                  <td>Show you everything the lender sees</td>
                  <td className="num">
                    <Pill tone="a">Always, free</Pill>
                  </td>
                </tr>
              </tbody>
            </table>
          </Card>
        </div>
      </div>
    </PublicShell>
  );
}
