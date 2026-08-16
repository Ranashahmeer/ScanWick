/**
 * Landing page — prototype screen 01.
 *
 * Full page, top to bottom, with the two audiences split at the hero. The
 * structure and copy are the prototype's; the only additions are real
 * routing on the calls to action and an auth-aware header (a signed-in
 * visitor is offered the app rather than a sign-in form).
 *
 * Claim rules binding on this page, from the prototype: no completion
 * percentage, no unverified market figure, no named institution from the
 * field research — the quote is attributed by role only — and nothing
 * implying Scanwick approves, declines, scores or rates anybody.
 */

import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useAuth } from "@/hooks/use-auth";
import { PublicShell } from "@/features/shell/app-shell";
import { Card, Hint, Row, Spark } from "@/components/sw";
import { Footer, Header, SOURCES } from "./chrome";

const problemStats = [
  [
    "8–9 in 10",
    "loan applications declined — most often because transactions are scattered across accounts and cannot be reconciled",
  ],
  ["13", "Nigerian banks and wallets read natively — each with its own date convention, layout and traps"],
  [
    "6",
    "different date conventions across those sources. One is month-first, one is day-first, and they appear in the same person's files",
  ],
] as const;

const individualBenefits = [
  ["Every account in one picture", "Transfers between your own accounts matched and removed, so your income is not double-counted"],
  ["Who you actually pay the most", "Ranked by value and by frequency — it is usually not what you think"],
  ["What the bank charged you", "Every fee, VAT line and levy separated from your spending and added up"],
  ["Is the business actually making money", "Business separated from household, and you can correct us"],
  ["How long your balance lasts", "Runway, retention and your lowest point in the month"],
  ["Your ajo counts in your favour", "Contributory savings read as discipline, not flagged as suspicious"],
] as const;

const lenderSteps = [
  [
    "01 · CONSOLIDATE",
    "Every account, one view",
    "Two to four accounts reconciled into a single financial picture, with internal transfers matched and removed. This is the reason most applications fail.",
  ],
  [
    "02 · ASSESS",
    "A brief, not a dashboard",
    "Written prose a credit officer reads in three minutes and takes to committee. Every figure opens to the transactions behind it. No score — the decision stays yours.",
  ],
  [
    "03 · MONITOR",
    "After the money goes out",
    "Eleven signals tracked against a baseline taken at disbursement, each with a recommended action and a deadline. Including new borrowing a bureau cannot see yet.",
  ],
] as const;

const howItWorks = [
  ["Connect or upload", "Link an account directly, or upload a statement — including password-protected PDFs."],
  [
    "We identify the source",
    "Before reading a single row, because the bank determines how dates are read. If we cannot tell, we stop rather than guess.",
  ],
  ["We check the statement", "Balances, totals, page continuity. We report what we found. We never tell you what it means."],
  ["You get the answer", "With coverage stated: which accounts, which periods, and what could not be determined."],
] as const;

const trustLeft = [
  [
    "We are not a credit bureau",
    "We analyse one consented person's data and return it to a recipient they named. Nothing flows sideways between lenders. There is no cross-lender search anywhere in the system.",
  ],
  [
    "We never produce a credit score",
    "No number, no grade, no rating. Signals with evidence attached. The lender exercises judgement.",
  ],
  ["We never accuse anyone", "A statement check reports what was detected and shows the rows. It never says fraud."],
] as const;

const trustRight = [
  [
    "Consent is per event and revocable",
    "Being assessed once does not authorise being watched for a year. Every permission is separate, time-bound and withdrawable.",
  ],
  [
    "You see everything a lender sees",
    "Free, from your own dashboard — including who opened your data and what they exported.",
  ],
  ["Read-only, always", "A connected account can be read. It can never be debited, and no payment can be made."],
] as const;

const plans = [
  { name: "FREE", price: "₦0", per: null, detail: "1 account · 1 analysis a month · 90 days history", featured: false },
  { name: "PLUS", price: "₦2,500", per: "/mo", detail: "4 accounts · 12 months · share links · export", featured: true },
  {
    name: "INSTITUTION BASIC",
    price: "₦75,000",
    per: "/mo",
    detail: "40 assessments · audit · briefs · 2 seats",
    featured: false,
  },
  {
    name: "INSTITUTION PREMIUM",
    price: "₦200,000",
    per: "/mo",
    detail: "150 assessments · monitoring · API · 10 seats",
    featured: false,
  },
] as const;

const faqs = [
  [
    "Can Scanwick take money from my account?",
    "No. Access is read-only. We can see transactions and balances. We cannot move money, make a payment, or change anything.",
  ],
  [
    "Will a lender see my transactions without asking me?",
    "No. Nothing is shared with anyone you have not named yourself, and you can withdraw it at any time.",
  ],
  ["My bank is not on the list.", "Upload a statement anyway. If we cannot read it we will tell you exactly why, and we will add support."],
  ["Do you give me a credit score?", "No, and we never will. We show what your money says. Lenders decide."],
  ["What if my statement is password-protected?", "Enter the password when you upload. It is used once, in memory, and never stored."],
  [
    "What happens to my data if I leave?",
    "Delete your account and everything goes, including any access you granted a lender. Raw statement files are deleted after 90 days regardless.",
  ],
] as const;

export function HomePage() {
  const { status } = useAuth();
  const signedIn = status === "authenticated";
  const startHref = signedIn ? "/upload" : "/register";
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  return (
    <PublicShell>
      <div className="lp">
        <Header />

        {/* HERO + SPLIT ------------------------------------------------- */}
        <div className="lp-sec hero">
          <div style={{ maxWidth: 720, margin: "0 auto", textAlign: "center" }}>
            <div
              style={{
                fontSize: 11,
                letterSpacing: "1.2px",
                textTransform: "uppercase",
                color: "var(--g300)",
                fontWeight: 700,
                marginBottom: 16,
              }}
            >
              Bank statement intelligence for Africa
            </div>
            <h2 className="lp-h1">Money moves through African accounts and nobody can read it.</h2>
            <p style={{ marginTop: 16, fontSize: 15.5, color: "#CFE0D6", lineHeight: 1.65 }}>
              Scanwick reads bank statements across every account a person holds — thirteen Nigerian banks and wallets — and
              turns them into an answer. For the person whose money it is, and for the institution deciding whether to lend.
            </p>
          </div>

          <Row cols={2} style={{ maxWidth: 820, margin: "34px auto 0", gap: 18 }}>
            <div
              style={{
                background: "rgba(255,255,255,.06)",
                border: "1px solid rgba(127,199,163,.3)",
                borderRadius: 12,
                padding: 24,
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  letterSpacing: ".8px",
                  textTransform: "uppercase",
                  color: "var(--g300)",
                  fontWeight: 700,
                  marginBottom: 9,
                }}
              >
                I want to understand my money
              </div>
              <div style={{ fontSize: 17, fontWeight: 700, lineHeight: 1.35, marginBottom: 9 }}>
                Where did your money go last month?
              </div>
              <div style={{ fontSize: 12.5, color: "#CFE0D6", lineHeight: 1.6, marginBottom: 16 }}>
                Every naira is in your statement. It is just spread across two hundred rows, in bank formatting, across three
                or four accounts that never meet.
              </div>
              <Link
                to={startHref}
                className="btn blk"
                style={{ background: "var(--g300)", color: "var(--g900)" }}
              >
                See my money — free
              </Link>
            </div>

            <div
              style={{
                background: "rgba(255,255,255,.06)",
                border: "1px solid rgba(255,255,255,.14)",
                borderRadius: 12,
                padding: 24,
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  letterSpacing: ".8px",
                  textTransform: "uppercase",
                  color: "#9FBFAE",
                  fontWeight: 700,
                  marginBottom: 9,
                }}
              >
                I assess borrowers
              </div>
              <div style={{ fontSize: 17, fontWeight: 700, lineHeight: 1.35, marginBottom: 9 }}>
                Eight in ten applications fail on legibility, not affordability.
              </div>
              <div style={{ fontSize: 12.5, color: "#CFE0D6", lineHeight: 1.6, marginBottom: 16 }}>
                Consolidate a borrower's accounts into one picture, with every figure traceable to the transaction behind it —
                then keep watching after you lend.
              </div>
              <Link
                to="/contact"
                className="btn sec blk"
                style={{ background: "transparent", color: "#fff", borderColor: "rgba(255,255,255,.3)" }}
              >
                Book a walkthrough
              </Link>
            </div>
          </Row>

          <div
            id="sources"
            style={{ textAlign: "center", marginTop: 26, fontSize: 11, color: "#7FA791", letterSpacing: ".3px" }}
          >
            {SOURCES}
          </div>
        </div>

        {/* PROBLEM ------------------------------------------------------ */}
        <div className="lp-sec">
          <div className="lp-inner">
            <h3 className="lp-h2" style={{ marginBottom: 8 }}>
              Nigeria has a legibility problem, not a credit problem
            </h3>
            <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.75, maxWidth: 640 }}>
              The country is not short of borrowers who can repay. It is short of borrowers whose ability to repay can be
              read. A statement is a list of transactions, not an answer — and the average person holds three or four of them.
            </p>
            <Row cols={3} style={{ marginTop: 26 }}>
              {problemStats.map(([figure, detail]) => (
                <div key={figure} style={{ borderLeft: "3px solid var(--g500)", paddingLeft: 14 }}>
                  <div style={{ fontSize: 27, fontWeight: 700, letterSpacing: "-.9px" }}>{figure}</div>
                  <div style={{ fontSize: 12.5, color: "var(--ink3)", marginTop: 3 }}>{detail}</div>
                </div>
              ))}
            </Row>
          </div>
        </div>

        {/* FOR INDIVIDUALS ---------------------------------------------- */}
        <div id="individuals" className="lp-sec alt">
          <div className="lp-inner">
            <div
              style={{
                fontSize: 11,
                letterSpacing: ".8px",
                textTransform: "uppercase",
                color: "var(--g700)",
                fontWeight: 700,
              }}
            >
              For individuals and businesses
            </div>
            <h3 style={{ fontSize: 23, letterSpacing: "-.6px", margin: "8px 0 20px" }}>Your own money, finally readable</h3>

            <Row cols={2} style={{ gap: 26 }}>
              <div>
                <table>
                  <tbody>
                    {individualBenefits.map(([title, detail]) => (
                      <tr key={title}>
                        <td>
                          <b>{title}</b>
                          <Hint>{detail}</Hint>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <Link to={startHref} className="btn" style={{ marginTop: 18 }}>
                  Start free — one account
                </Link>
              </div>

              <Card style={{ background: "#fff" }}>
                <Row cols={2} style={{ gap: 12 }}>
                  <div className="kpi">
                    <div className="lab">Money in</div>
                    <div className="val" style={{ fontSize: 19 }}>
                      ₦4,182,600
                    </div>
                  </div>
                  <div className="kpi">
                    <div className="lab">Money out</div>
                    <div className="val" style={{ fontSize: 19 }}>
                      ₦3,914,180
                    </div>
                  </div>
                </Row>
                <Spark values={[52, 64, 48, 79, 58, 88]} height={56} style={{ marginTop: 14 }} />
                <div
                  style={{
                    marginTop: 14,
                    padding: 11,
                    background: "var(--g50)",
                    borderRadius: 8,
                    fontSize: 11.5,
                    color: "var(--ink2)",
                  }}
                >
                  <b>Internal transfers removed:</b> ₦1,240,000 across 34 movements. Money you moved between your own accounts
                  is not income.
                </div>
              </Card>
            </Row>
          </div>
        </div>

        {/* FOR LENDERS -------------------------------------------------- */}
        <div id="lenders" className="lp-sec">
          <div className="lp-inner">
            <div style={{ fontSize: 11, letterSpacing: ".8px", textTransform: "uppercase", color: "#1D4ED8", fontWeight: 700 }}>
              For lenders
            </div>
            <h3 style={{ fontSize: 23, letterSpacing: "-.6px", margin: "8px 0 20px" }}>Assess, then keep watching</h3>

            <Row cols={3}>
              {lenderSteps.map(([step, title, body]) => (
                <Card key={step}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ink3)", letterSpacing: ".5px" }}>{step}</div>
                  <div style={{ fontWeight: 700, margin: "7px 0 5px" }}>{title}</div>
                  <div style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.6 }}>{body}</div>
                </Card>
              ))}
            </Row>

            <div
              style={{
                marginTop: 24,
                padding: 20,
                border: "1px solid var(--line)",
                borderLeft: "4px solid var(--g500)",
                borderRadius: 10,
                background: "#fff",
              }}
            >
              <div style={{ fontSize: 14.5, lineHeight: 1.7, color: "var(--ink)", fontStyle: "italic" }}>
                "Lending isn't the problem but the risk. Is there any technology that can capture this person to pay back,
                track them and mentor them. Once one can create that, there is billions of naira to cash on that."
              </div>
              <Hint style={{ marginTop: 9 }}>Credit manager, Nigerian microfinance bank · field research, July 2026</Hint>
            </div>

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 20 }}>
              <Link to="/contact" className="btn">
                Book a walkthrough
              </Link>
              <Link to="/contact" className="btn sec">
                See a sample brief
              </Link>
            </div>
          </div>
        </div>

        {/* HOW IT WORKS -------------------------------------------------- */}
        <div className="lp-sec alt">
          <div className="lp-inner">
            <h3 className="lp-h2" style={{ marginBottom: 20 }}>How it works</h3>
            <Row cols={4}>
              {howItWorks.map(([title, body], i) => (
                <div key={title}>
                  <div
                    style={{
                      width: 30,
                      height: 30,
                      borderRadius: "50%",
                      background: "var(--g800)",
                      color: "#fff",
                      display: "grid",
                      placeItems: "center",
                      fontWeight: 700,
                      fontSize: 13,
                    }}
                  >
                    {i + 1}
                  </div>
                  <div style={{ fontWeight: 700, margin: "10px 0 5px" }}>{title}</div>
                  <div style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.6 }}>{body}</div>
                </div>
              ))}
            </Row>
          </div>
        </div>

        {/* TRUST --------------------------------------------------------- */}
        <div id="trust" className="lp-sec">
          <div className="lp-inner">
            <h3 style={{ fontSize: 23, letterSpacing: "-.6px", marginBottom: 6 }}>What Scanwick will never do</h3>
            <p style={{ fontSize: 13.5, color: "var(--ink2)", maxWidth: 620, marginBottom: 22 }}>
              More important than any feature list. These are structural — enforced in the software, not stated as policy.
            </p>

            <Row cols={2} style={{ gap: 26 }}>
              {[trustLeft, trustRight].map((column, index) => (
                <table key={index}>
                  <tbody>
                    {column.map(([title, detail]) => (
                      <tr key={title}>
                        <td>
                          <b>{title}</b>
                          <Hint>{detail}</Hint>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ))}
            </Row>

            <div style={{ marginTop: 22, display: "flex", gap: 22, flexWrap: "wrap", fontSize: 11.5, color: "var(--ink3)" }}>
              <span>NDPA 2023 · registered data controller</span>
              <span>Encrypted at rest and in transit</span>
              <span>Read-only account access</span>
              <span>RC 9458339 · Lagos, Nigeria</span>
            </div>
          </div>
        </div>

        {/* PRICING ------------------------------------------------------- */}
        <div id="pricing" className="lp-sec alt">
          <div className="lp-inner">
            <h3 style={{ fontSize: 23, letterSpacing: "-.6px", marginBottom: 20 }}>Pricing</h3>
            <Row cols={4}>
              {plans.map((plan) => (
                <Card key={plan.name} style={plan.featured ? { border: "2px solid var(--g500)" } : undefined}>
                  <div
                    className="lab"
                    style={{ fontSize: 10.5, color: plan.featured ? "var(--g700)" : "var(--ink3)", fontWeight: 700 }}
                  >
                    {plan.name}
                  </div>
                  <div style={{ fontSize: 22, fontWeight: 700, margin: "6px 0" }}>
                    {plan.price}
                    {plan.per ? (
                      <span style={{ fontSize: 12, fontWeight: 500, color: "var(--ink3)" }}>{plan.per}</span>
                    ) : null}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--ink2)" }}>{plan.detail}</div>
                </Card>
              ))}
            </Row>
            <Hint style={{ marginTop: 14 }}>
              Assessments, not seats. One assessment is one borrower across all their accounts, valid 30 days, re-runnable
              free.
            </Hint>
          </div>
        </div>

        {/* FAQ ----------------------------------------------------------- */}
        <div className="lp-sec">
          <div className="lp-inner narrow">
            <h3 style={{ fontSize: 23, letterSpacing: "-.6px", marginBottom: 20 }}>Questions people actually ask</h3>
            <table>
              <tbody>
                {faqs.map(([question, answer], i) => (
                  <tr key={question}>
                    <td>
                      <button
                        type="button"
                        onClick={() => setOpenFaq(openFaq === i ? null : i)}
                        aria-expanded={openFaq === i}
                        style={{
                          background: "none",
                          border: 0,
                          padding: 0,
                          font: "inherit",
                          fontWeight: 700,
                          color: "inherit",
                          cursor: "pointer",
                          textAlign: "left",
                          width: "100%",
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 12,
                        }}
                      >
                        {question}
                        <span style={{ color: "var(--ink3)", fontWeight: 400 }}>{openFaq === i ? "−" : "+"}</span>
                      </button>
                      {openFaq === i ? <Hint>{answer}</Hint> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* CTA ----------------------------------------------------------- */}
        <div className="lp-sec cta">
          <h3 style={{ fontSize: 26, letterSpacing: "-.8px", fontWeight: 700 }}>Start with one statement</h3>
          <p style={{ fontSize: 13.5, color: "#CFE0D6", marginTop: 9, maxWidth: 460, marginLeft: "auto", marginRight: "auto" }}>
            Free, one account, no card. See where your money went before you decide anything else.
          </p>
          <div style={{ marginTop: 20, display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
            <Link to={startHref} className="btn" style={{ background: "var(--g300)", color: "var(--g900)" }}>
              See my money
            </Link>
            <Link
              to="/contact"
              className="btn sec"
              style={{ background: "transparent", color: "#fff", borderColor: "rgba(255,255,255,.25)" }}
            >
              I assess borrowers
            </Link>
          </div>
        </div>

        <Footer />
      </div>
    </PublicShell>
  );
}

export default HomePage;
