import {
  Banknote,
  Box,
  Check,
  Droplet,
  FileText,
  Link2,
  Play,
  Shield,
  Sparkles,
  Table2,
  X,
} from "lucide-react";
import { useState } from "react";
import { Link } from "@tanstack/react-router";
import scanwickLogo from "@/assets/Logos/Full Scanwick Logo Light Green.svg";
import { useAuth } from "@/hooks/use-auth";
import { Footer, Header, useScanwickChrome } from "./chrome";

const analyzerCards = [
  {
    id: "commerce",
    title: "E-Commerce Analyzer",
    description: "Find the products quietly losing you money.",
    icon: Link2,
    tone: "lime",
    points: [
      "True net margin per order",
      "Profit-leak & dead-stock detection",
      "RFM, churn & inventory forecast",
    ],
  },
  {
    id: "sales",
    title: "Sales Analyzer",
    description: "Forecast revenue and fix the pipeline before it leaks.",
    icon: Box,
    tone: "green",
    points: [
      "Confidence-adjusted forecast",
      "Stalled-deal & slippage alerts",
      "Rep trajectory & Win DNA",
    ],
  },
  {
    id: "bank",
    title: "Bank Statement Analyzer",
    description: "Turn your statement into a lender-ready brief.",
    icon: Banknote,
    tone: "teal",
    points: [
      "Loan readiness score & ABM",
      "Fraud-risk & integrity checks",
      "AI lender brief in 60 seconds",
    ],
  },
];

const featureCards = [
  {
    title: "AI Playbook Cards",
    description: "Specific actions with reasoning and revenue at stake.",
    icon: Sparkles,
    premium: true,
  },
  {
    title: "SKU Matrix",
    description: "Sales, cash cover, acquisition health, edge - all in glance.",
    icon: Table2,
  },
  {
    title: "Loan Score",
    description: "Your credit-worthiness, scored and explained 0-100.",
    icon: Banknote,
  },
  {
    title: "Fraud Risk Detection",
    description: "Unusual transactions flagged in plain language.",
    icon: Shield,
  },
  {
    title: "Top Leakage Table",
    description: "The products eroding margin, ranked worst-first.",
    icon: Droplet,
  },
  {
    title: "Lender Brief",
    description: "A bank-ready credit summary, generated for you.",
    icon: FileText,
    premium: true,
  },
];

const reviewCards = [
  {
    quote:
      "Scanwick found a best-selling lamp that was losing N200 a unit after returns. We re-priced it and recovered six figures in a quarter.",
    name: "Adanna Okonkwo",
    title: "Founder, Mina Home Lagos",
  },
  {
    quote:
      "The lender brief got our working-capital facility approved on the first try. The loan officer said it was the clearest statement summary they had seen.",
    name: "Babatunde Ade",
    title: "MD, Suncrest Supplies Ibadan",
  },
  {
    quote:
      "The forecast confidence score is the feature. It tells us when not to trust the number - and exactly why. Our quarter is less chaotic now.",
    name: "Nkiru Mensah",
    title: "Head of Sales, Cosmo & Co Accra",
  },
];

const ratingRows = [
  ["5", "78%"],
  ["4", "15%"],
  ["3", "5%"],
  ["2", "2%"],
  ["1", "0%"],
];

// Fixed USD reference prices — the actual source of truth for what each
// tier costs (see backend/app/config.py's basic_plan_price_usd /
// premium_plan_price_usd). What's displayed below is this converted to the
// visitor's own local currency for readability (see geo-currency.ts) — the
// real checkout charge is always computed server-side in NGN at the live
// rate, independent of whatever currency was shown here.
const pricingPlans = [
  {
    slug: "free" as const,
    priceUsd: 0,
    name: "Free",
    cadence: "",
    description: "No credit card required",
    cta: "Get Started Free",
    features: [
      { text: "Upload & data quality report", included: true },
      { text: "One summary dashboard per module", included: true },
      { text: "Monthly trend chart", included: true },
      {
        text: "One real insight per module (your biggest profit leak, deals going quiet, loan-readiness grade)",
        included: true,
      },
      { text: "Full analytics suite", included: false },
      { text: "AI playbooks & forecasts", included: false },
    ],
  },
  {
    slug: "basic" as const,
    priceUsd: 8.99,
    name: "Basic",
    cadence: "/mo",
    description: "For operators who want the full picture",
    cta: "Get Basic",
    featured: true,
    features: [
      { text: "Everything in Free", included: true },
      { text: "Profit leak, SKU matrix, channels", included: true },
      { text: "Pipeline, stage velocity, win/loss", included: true },
      {
        text: "Income stability + loan-readiness score (fraud removed)",
        included: true,
      },
      { text: "Forecasts, RFM, fraud score, AI playbooks", included: false },
    ],
  },
  {
    slug: "premium" as const,
    priceUsd: 16.99,
    name: "Premium",
    cadence: "/mo",
    description: "The full predictive + prescriptive suite",
    cta: "Get Premium",
    features: [
      { text: "Everything in Basic", included: true },
      { text: "Inventory forecast, RFM, churn, cohort", included: true },
      {
        text: "Confidence forecast, Win DNA, post-mortem",
        included: true,
      },
      {
        text: "Fraud score, 90-day forecast & full lender brief (PDF)",
        included: true,
      },
      { text: "AI playbooks + Explainability", included: true },
    ],
  },
];

const faqItems = [
  {
    id: "what-is-scanwick",
    question: "What is Scanwick AI and how does it help small business owners?",
    answer: [
      "Scanwick AI is a data intelligence platform built specifically for small and medium-sized businesses. It connects to your existing business data - your e-commerce store, your sales pipeline, or your bank statements - and automatically turns that data into clear, actionable insights without requiring any technical knowledge.",
      "Most business owners manage their data manually in spreadsheets. They export reports from Shopify, copy revenue numbers into Excel, and spend hours trying to figure out why profit is lower than expected. Scanwick eliminates that process entirely.",
      "For e-commerce sellers, Scanwick calculates true net margin per order after returns, refunds, shipping costs, payment processing fees, and ad spend. For sales teams, it analyzes your pipeline, predicts which deals are likely to close, and flags deals that are stalling. For business owners and CFOs, it reads your bank statement, calculates your average monthly balance, scores creditworthiness, detects unusual transactions, and generates a lender-ready brief.",
      "You do not need to hire a data analyst. Upload your file, and Scanwick does the rest - including AI-generated recommendations that tell you exactly what to do and why.",
    ],
  },
  {
    id: "profit-leaks",
    question:
      "How does Scanwick detect profit leaks in my e-commerce business?",
    answer: [
      "A profit leak happens when a product looks successful on the surface - high sales, high revenue - but is actually losing money after all costs are factored in. This is one of the most common and damaging problems in e-commerce, and it is almost impossible to spot without the right tools.",
      "Scanwick takes every order in your dataset and calculates true net margin using revenue, returns, refunds, COGS, shipping cost, payment processing fees, and allocated ad spend. It then ranks every product by revenue and flags products that sell well but have negative margin.",
      "It also shows which cost component is causing the leak. If the issue is ad spend rather than shipping, you see that immediately. Scanwick can also connect return patterns to logistics partners, damaged returns, or warehouse locations so you can see the financial impact.",
      "The result is a ranked list of your most dangerous products - the ones generating revenue but destroying margin - along with the breakdown of what is causing each leak and what you can do about it.",
    ],
  },
  {
    id: "business-loan",
    question:
      "Can Scanwick help me get a business loan using my bank statement?",
    answer: [
      "Yes. Scanwick reads your bank statement and turns it into a lender-ready summary that highlights the signals banks usually look for: average monthly balance, deposit consistency, cash-flow stability, revenue concentration, unusual withdrawals, and overall loan readiness.",
      "It does not guarantee approval, but it helps you understand how a lender may view your business before you apply. You also get a clear brief you can share with a bank, microfinance institution, or funding partner.",
    ],
  },
  {
    id: "sales-forecast",
    question:
      "How does Scanwick forecast sales revenue and identify pipeline problems?",
    answer: [
      "Scanwick analyzes your CRM export and looks at deal stage, deal age, expected close date, rep activity, stage velocity, historical win rates, and slippage patterns. It then creates a confidence-adjusted revenue forecast instead of treating every open deal as equally likely to close.",
      "It flags stalled deals, risky close dates, weak pipeline coverage, and reps who may need support. The goal is to show what will likely close, what may slip, and what needs attention before the quarter is already missed.",
    ],
  },
  {
    id: "rfm-analysis",
    question:
      "What is RFM analysis and how does Scanwick use it to reduce customer churn?",
    answer: [
      "RFM stands for recency, frequency, and monetary value. It groups customers by how recently they bought, how often they buy, and how much they spend. This helps you separate loyal customers from at-risk customers, one-time buyers, and high-value customers who are going quiet.",
      "Scanwick uses RFM analysis to identify churn risk and recommend practical actions: who to win back, who to reward, who to upsell, and which customer segments deserve more marketing attention.",
    ],
  },
];

const loremInsight =
  "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer vitae tortor sed justo efficitur posuere. Curabitur non risus sed lectus feugiat luctus, and this space will later show the backend response.";

function IntelligenceCard() {
  return (
    <section
      className="intelligence-card"
      aria-label="Intelligence Center preview"
    >
      <div className="intel-top">
        <span className="intel-title">
          <span className="intel-dot" />
          Intelligence Center
        </span>
        <span className="intel-status">Lumio Living</span>
      </div>

      <div className="intel-grid">
        <div className="intel-metric">
          <span>Loan readiness</span>
          <strong>72 · B</strong>
        </div>
        <div className="intel-metric">
          <span>Next reserve</span>
          <strong>N1.82M</strong>
        </div>
      </div>

      <div className="intel-chart">
        <span>Revenue forecast · 90 days</span>
        <svg viewBox="0 0 410 74" role="img" aria-label="Revenue trend rising">
          <path
            className="chart-area"
            d="M3 58 L84 50 L145 52 L224 39 L309 32 L407 24 L407 72 L3 72 Z"
          />
          <path
            className="chart-line"
            d="M3 58 L84 50 L145 52 L224 39 L309 32 L407 24"
          />
        </svg>
      </div>

      <div className="intel-note">
        <strong>CDM</strong>
        <span>Reorder LMP-014 before 5 Jul - N1.24M at risk</span>
      </div>
    </section>
  );
}

function AnalyzersSection() {
  const [expandedAnalyzer, setExpandedAnalyzer] = useState<string | null>(null);
  const [insights, setInsights] = useState<Record<string, string>>({});
  const [loadingAnalyzer, setLoadingAnalyzer] = useState<string | null>(null);

  const handleExplore = (id: string) => {
    if (expandedAnalyzer === id) {
      setExpandedAnalyzer(null);
      return;
    }

    setExpandedAnalyzer(id);

    if (insights[id]) return;

    setLoadingAnalyzer(id);

    window.setTimeout(() => {
      setInsights((currentInsights) => ({
        ...currentInsights,
        [id]: loremInsight,
      }));
      setLoadingAnalyzer(null);
    }, 320);
  };

  return (
    <section className="analyzers-section" id="analyzers">
      <div className="analyzers-inner">
        <div className="section-heading">
          <h2>One platform, three analyzers</h2>
          <p>
            Connect the data you already have. Scanwick turns it into decisions.
          </p>
        </div>

        <div className="analyzer-grid">
          {analyzerCards.map((analyzer) => {
            const Icon = analyzer.icon;
            const isExpanded = expandedAnalyzer === analyzer.id;

            return (
              <article
                key={analyzer.id}
                className={`analyzer-card analyzer-card-${analyzer.tone} ${
                  isExpanded ? "is-expanded" : ""
                }`}
              >
                <div className="analyzer-icon">
                  <Icon size={18} strokeWidth={2.35} />
                </div>
                <h3>{analyzer.title}</h3>
                <p>{analyzer.description}</p>

                <ul>
                  {analyzer.points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>

                <button
                  type="button"
                  className="explore-button"
                  onClick={() => handleExplore(analyzer.id)}
                  aria-expanded={isExpanded}
                >
                  {isExpanded ? "Collapse" : "Explore"} →
                </button>

                <div className="analyzer-details" aria-hidden={!isExpanded}>
                  <p>
                    {loadingAnalyzer === analyzer.id
                      ? "Loading insight..."
                      : insights[analyzer.id]}
                  </p>
                </div>
              </article>
            );
          })}
        </div>
      </div>

      <div className="how-section">
        <div className="how-inner">
          <div className="section-heading">
            <h2>How it works</h2>
            <p>No analyst, no setup, no waiting.</p>
          </div>

          <div className="steps-grid">
            <div>
              <span>1</span>
              <strong>Drop your CSV</strong>
              <p>Upload a Shopify export, CRM data, or a bank statement.</p>
            </div>
            <div>
              <span>2</span>
              <strong>AI analyses everything</strong>
              <p>
                Scanwick runs the full analysis automatically - margins,
                forecasts, risk.
              </p>
            </div>
            <div>
              <span>3</span>
              <strong>Get your report</strong>
              <p>A downloadable PDF or live dashboard in under 60 seconds.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ClarityFeaturesSection() {
  return (
    <section className="clarity-section" id="product">
      <div className="clarity-inner">
        <div className="section-heading">
          <h2>Everything you need to see clearly</h2>
          <p>The features that turn raw exports into action.</p>
        </div>

        <div className="feature-grid">
          {featureCards.map((feature) => {
            const Icon = feature.icon;

            return (
              <article className="feature-card" key={feature.title}>
                {feature.premium ? (
                  <span className="premium-badge">Premium</span>
                ) : null}
                <Icon className="feature-icon" size={16} strokeWidth={2.2} />
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function BusinessGlanceSection() {
  return (
    <section className="glance-section">
      <div className="glance-inner">
        <div className="section-heading">
          <h2>See your business at a glance</h2>
          <p>
            Upload a CSV or PDF and Scanwick instantly generates charts like
            these - no spreadsheets, no analysts.
          </p>
        </div>

        <div
          className="dashboard-preview"
          aria-label="Scanwick dashboard preview"
        >
          <div className="dashboard-topbar">
            <span>
              <img src={scanwickLogo} alt="" />
              Intelligence Center
            </span>
            <span className="dashboard-company">Lumio Living</span>
          </div>

          <div className="dashboard-grid">
            <div className="dashboard-panel channel-panel">
              <h3>Revenue by Channel</h3>
              {[
                ["Online", "38%"],
                ["Retail", "58%"],
                ["POS", "62%"],
                ["Organic", "55%"],
                ["Direct", "72%"],
              ].map(([label, width]) => (
                <div className="bar-row" key={label}>
                  <span>{label}</span>
                  <div>
                    <i style={{ width }} />
                  </div>
                  <strong>{width}</strong>
                </div>
              ))}
            </div>

            <div className="dashboard-panel forecast-panel">
              <h3>Revenue Forecast · 90 days</h3>
              <strong>
                N11.2M <span>+18%</span>
              </strong>
              <svg
                viewBox="0 0 420 175"
                role="img"
                aria-label="Rising revenue forecast"
              >
                <path d="M28 124 L140 104 L191 111 L275 72 L392 48" />
              </svg>
            </div>

            <div className="dashboard-panel readiness-panel">
              <h3>Loan Readiness Score</h3>
              <div className="score-wrap">
                <div className="score-ring">
                  <strong>72</strong>
                  <span>B</span>
                </div>
                <div className="score-lines">
                  <div>
                    <span>Revenue stability</span>
                    <strong>80%</strong>
                    <i style={{ width: "80%" }} />
                  </div>
                  <div>
                    <span>Avg. balance</span>
                    <strong>68%</strong>
                    <i style={{ width: "68%" }} />
                  </div>
                  <div>
                    <span>Fraud risk</span>
                    <strong>Low</strong>
                    <i style={{ width: "34%" }} />
                  </div>
                </div>
              </div>
            </div>

            <div className="dashboard-panel margin-panel">
              <h3>Monthly Revenue & Conversion Rate</h3>
              <svg
                viewBox="0 0 420 175"
                role="img"
                aria-label="Revenue and conversion chart"
              >
                <path
                  className="muted-line"
                  d="M24 121 L72 113 L118 119 L178 87 L232 78 L310 58 L394 38"
                />
                <path d="M24 139 L72 132 L118 136 L178 96 L232 86 L310 66 L394 48" />
              </svg>
            </div>
          </div>
        </div>

        <p className="demo-link">
          A live Scanwick Intelligence Center for the demo business, Lumio
          Living. <a href="#demo">Try it free →</a>
        </p>
      </div>
    </section>
  );
}

function RatingsReviewsSection() {
  const [reviewRating, setReviewRating] = useState(0);

  return (
    <section className="reviews-section" id="reviews">
      <div className="reviews-inner">
        <div className="section-heading">
          <h2>Ratings & reviews</h2>
          <p>What operators say after meeting Scanwick. Unfiltered.</p>
        </div>

        <div className="ratings-summary" aria-label="Scanwick rating summary">
          <div className="rating-score">
            <strong>4.8</strong>
            <span className="stars" aria-label="4.8 out of 5 stars">
              ★★★★★
            </span>
            <small>240+ reviews</small>
          </div>

          <div className="rating-bars">
            {ratingRows.map(([rating, width]) => (
              <div className="rating-bar-row" key={rating}>
                <span>{rating}★</span>
                <div>
                  <i style={{ width }} />
                </div>
                <strong>{width}</strong>
              </div>
            ))}
          </div>

          <div className="recommend-score">
            <strong>96%</strong>
            <span>would recommend Scanwick</span>
          </div>
        </div>

        <div className="review-grid">
          {reviewCards.map((review) => (
            <article className="review-card" key={review.name}>
              <span className="stars" aria-hidden="true">
                ★★★★★
              </span>
              <p>"{review.quote}"</p>
              <strong>{review.name}</strong>
              <small>{review.title}</small>
            </article>
          ))}
        </div>

        <form className="review-form">
          <h3>Leave a review</h3>
          <p>
            Used Scanwick? Tell other operators what you think. Your review is
            visible to everyone who opens this page.
          </p>

          <label>Your rating</label>
          <div className="review-stars" aria-label="Choose a star rating">
            {[1, 2, 3, 4, 5].map((rating) => (
              <button
                key={rating}
                type="button"
                className={rating <= reviewRating ? "is-active" : ""}
                onClick={() => setReviewRating(rating)}
                aria-label={`${rating} star${rating === 1 ? "" : "s"}`}
              >
                ★
              </button>
            ))}
          </div>

          <div className="review-form-grid">
            <input type="text" placeholder="Your name" aria-label="Your name" />
            <input
              type="text"
              placeholder="Company (optional)"
              aria-label="Company optional"
            />
          </div>
          <textarea
            placeholder="What did Scanwick help you do?"
            aria-label="Review text"
          />
          <button type="button" className="review-submit">
            Submit review
          </button>
        </form>
      </div>
    </section>
  );
}

// Landing page always shows the fixed USD reference price — no geolocation
// call here (kept simple/predictable for the first thing a visitor sees).
// Account -> Billing (subscription-tab.tsx) still shows each signed-in
// user's local currency, since that's a more considered, post-signup
// context where the extra precision is more useful than confusing.
function formatUsd(amount: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);
}

function PricingSection() {
  const { status } = useAuth();
  const isAuthenticated = status === "authenticated";

  return (
    <section className="pricing-section" id="pricing">
      <div className="pricing-inner">
        <div className="section-heading">
          <h2>Simple pricing</h2>
          <p>Start free. Upgrade when the insight pays for itself. Prices in USD, charged in NGN at checkout.</p>
        </div>

        <div className="pricing-grid">
          {pricingPlans.map((plan) => (
            <article
              className={`pricing-card ${plan.featured ? "is-featured" : ""}`}
              key={plan.name}
            >
              {plan.featured ? (
                <span className="plan-badge">Most popular</span>
              ) : null}
              <h3>{plan.name}</h3>
              <div className="plan-price">
                <strong>{formatUsd(plan.priceUsd)}</strong>
                {plan.cadence ? <span>{plan.cadence}</span> : null}
              </div>
              <p>{plan.description}</p>

              <ul>
                {plan.features.map((feature) => (
                  <li
                    key={feature.text}
                    className={feature.included ? "" : "is-excluded"}
                  >
                    {feature.included ? (
                      <Check size={11} strokeWidth={3} />
                    ) : (
                      <X size={11} strokeWidth={3} />
                    )}
                    {feature.text}
                  </li>
                ))}
              </ul>

              {/* Already signed in: skip registration entirely and go
                  straight to where the plan actually gets applied — Free
                  has nothing to check out, Basic/Premium land on the
                  Subscription tab which auto-starts checkout (see
                  AccountBilling/SubscriptionTab's initialUpgradeTier). Not
                  signed in: the existing register->otp handoff carries the
                  chosen plan through account creation instead. */}
              {isAuthenticated ? (
                plan.slug === "free" ? (
                  <Link to="/upload" className={`pricing-cta ${plan.featured ? "is-featured" : ""}`}>
                    {plan.cta}
                  </Link>
                ) : (
                  <Link
                    to="/account"
                    search={{ tab: "billing", upgrade: plan.slug }}
                    className={`pricing-cta ${plan.featured ? "is-featured" : ""}`}
                  >
                    {plan.cta}
                  </Link>
                )
              ) : (
                <Link
                  to="/register"
                  search={{ plan: plan.slug }}
                  className={`pricing-cta ${plan.featured ? "is-featured" : ""}`}
                >
                  {plan.cta}
                </Link>
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function FAQSection() {
  const [openFaqId, setOpenFaqId] = useState(faqItems[0].id);

  return (
    <section className="faq-section" id="faq">
      <div className="faq-inner">
        <div className="section-heading">
          <h2>Frequently asked questions</h2>
          <p>The essentials, answered.</p>
        </div>

        <div className="faq-list">
          {faqItems.map((item) => {
            const isOpen = openFaqId === item.id;

            return (
              <article
                className={`faq-item ${isOpen ? "is-open" : ""}`}
                key={item.id}
              >
                <button
                  type="button"
                  className="faq-question"
                  onClick={() => setOpenFaqId(isOpen ? "" : item.id)}
                  aria-expanded={isOpen}
                  aria-controls={`${item.id}-answer`}
                >
                  <span>{item.question}</span>
                  <strong aria-hidden="true">{isOpen ? "-" : "+"}</strong>
                </button>

                <div
                  className="faq-answer"
                  id={`${item.id}-answer`}
                  aria-hidden={!isOpen}
                >
                  <div>
                    {item.answer.map((paragraph) => (
                      <p key={paragraph}>{paragraph}</p>
                    ))}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export function HomePage() {
  const { theme, toggleTheme } = useScanwickChrome();

  return (
    <main className={`scanwick-page ${theme === "light" ? "theme-light" : ""}`}>
      <Header theme={theme} onToggleTheme={toggleTheme} />

      <section className="scanwick-hero">
        <div className="scanwick-hero-inner">
          <div className="scanwick-copy">
            <h1>Understand your business in 60 seconds.</h1>
            <p>
              Scanwick analyses your e-commerce data, sales pipeline, or bank
              statement and delivers a business intelligence report in about a
              minute.
            </p>

            <div className="hero-actions">
              <Link to="/upload" className="scanwick-upload hero-upload">
                Upload CV - It's Free
              </Link>
              <a href="#demo" className="demo-button">
                <Play size={14} fill="currentColor" strokeWidth={2.5} />
                See a live demo
              </a>
            </div>

            <div
              className="rating-line"
              aria-label="4.8 out of 5 stars from 240 plus businesses analysed"
            >
              <span className="stars">★★★★</span>
              <span className="star-muted">★</span>
              <strong>4.8/5</strong>
              <span>· 240+ businesses analysed</span>
            </div>
          </div>

          <IntelligenceCard />
        </div>
      </section>

      <section className="scanwick-stats" aria-label="Scanwick highlights">
        <div>
          <strong>60s</strong>
          <span>Full analysis in 60 seconds</span>
        </div>
        <div>
          <strong>3</strong>
          <span>Three analyzers in one platform</span>
        </div>
        <div>
          <strong>Gemini AI</strong>
          <span>Powered by Gemini AI</span>
        </div>
      </section>

      <AnalyzersSection />
      <ClarityFeaturesSection />
      <BusinessGlanceSection />
      <RatingsReviewsSection />
      <PricingSection />
      <FAQSection />
      <Footer />
    </main>
  );
}
