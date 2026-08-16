import { useState, useEffect, useMemo } from "react";
import { Link } from "@tanstack/react-router";
import { Search, ExternalLink } from "lucide-react";

interface ScreenDef {
  id: string;
  num: string;
  title: string;
  group: string;
  tag: string;
  tagClass?: string;
  meta: string;
  liveLink?: string;
}

const SCREENS: ScreenDef[] = [
  { id: "s00", num: "00", title: "Design system", group: "Reference", tag: "Reference", tagClass: "sys", meta: "Tokens, components and the rules that are product requirements rather than taste" },
  { id: "s01", num: "01", title: "Landing page", group: "Public", tag: "Public", tagClass: "pub", meta: "scanwick.com · full page, top to bottom · two audiences split at the hero", liveLink: "/" },
  { id: "s02", num: "02", title: "Create account", group: "Public", tag: "Public", tagClass: "pub", meta: "Individual sign-up · consent captured at first step", liveLink: "/register" },
  { id: "s03", num: "03", title: "Sign in", group: "Public", tag: "Public", tagClass: "pub", meta: "Email and password, then OTP", liveLink: "/login" },
  { id: "s04", num: "04", title: "Verify OTP", group: "Public", tag: "Public", tagClass: "pub", meta: "Six digits, email or SMS", liveLink: "/otp" },
  { id: "s05", num: "05", title: "Reset password", group: "Public", tag: "Public", tagClass: "pub", meta: "Request, verify, set new", liveLink: "/reset" },
  { id: "s06", num: "06", title: "Add accounts · 13 sources", group: "Ingestion", tag: "Ingestion", meta: "13 sources · connect by API where available, upload a file otherwise" },
  { id: "s07", num: "07", title: "Upload statement", group: "Ingestion", tag: "Ingestion", meta: "PDF, XLS, XLSX or CSV · including password-protected files", liveLink: "/upload" },
  { id: "s08", num: "08", title: "Password-protected PDF", group: "Ingestion", tag: "Ingestion", meta: "Common in Nigeria — most banks email statements locked" },
  { id: "s09", num: "09", title: "Processing", group: "Ingestion", tag: "Ingestion", meta: "Background job · the user is not blocked" },
  { id: "s10", num: "10", title: "Source detected", group: "Ingestion", tag: "Ingestion", meta: "Confidence tier assigned before any transaction is trusted" },
  { id: "s11", num: "11", title: "Statement audit", group: "Ingestion", tag: "Ingestion", meta: "Runs on every ingested file · reports findings, never a verdict" },
  { id: "s12", num: "12", title: "Rejected — Tier D", group: "Ingestion", tag: "Ingestion", meta: "The file was not analysed and we say exactly why" },
  { id: "s13", num: "13", title: "Empty statement", group: "Ingestion", tag: "Ingestion", meta: "A real and common state — Alpha Morgan prints N/A rows" },
  { id: "s62", num: "62", title: "Upload quality report", group: "Ingestion", tag: "Ingestion", meta: "/upload/{id}/quality-report · what happened when we read this file · distinct from statement audit" },
  { id: "s72", num: "72", title: "Per-source upload panels", group: "Ingestion", tag: "Ingestion", meta: "13 panels · the single biggest drop-off point in the product" },
  { id: "s14", num: "14", title: "Connect by API", group: "Account connection", tag: "Connection", meta: "Tier A · live connection through a licensed aggregator" },
  { id: "s15", num: "15", title: "Connection health", group: "Account connection", tag: "Connection", meta: "A connection that has lapsed is not a connection · both borrower and lender need to see this" },
  { id: "s16", num: "16", title: "Disconnected", group: "Account connection", tag: "Connection", meta: "What the borrower sees · and what the lender is told" },
  { id: "s17", num: "17", title: "Home", group: "Surface 1 · Individual", tag: "Surface 1", meta: "Where a signed-in individual lands · the daily view", liveLink: "/dashboard" },
  { id: "s18", num: "18", title: "Consolidated view", group: "Surface 1 · Individual", tag: "Surface 1", meta: "The home screen for an individual · every account, one picture" },
  { id: "s19", num: "19", title: "Coverage statement", group: "Surface 1 · Individual", tag: "Surface 1", meta: "Always visible · prints on every export" },
  { id: "s20", num: "20", title: "Where money goes", group: "Surface 1 · Individual", tag: "Surface 1", meta: "Spending by category · every figure opens to its transactions" },
  { id: "s21", num: "21", title: "Top payees", group: "Surface 1 · Individual", tag: "Surface 1", meta: "The single most useful answer for an individual" },
  { id: "s22", num: "22", title: "Recurring outflows", group: "Surface 1 · Individual", tag: "Surface 1", meta: "Detected by amount similarity and interval regularity" },
  { id: "s23", num: "23", title: "Fees & charges", group: "Surface 1 · Individual", tag: "Surface 1", meta: "The number the bank never adds up" },
  { id: "s24", num: "24", title: "Income & patterns", group: "Surface 1 · Individual", tag: "Surface 1", meta: "Where money comes from, and what shape it has" },
  { id: "s25", num: "25", title: "Seasonality", group: "Surface 1 · Individual", tag: "Surface 1", meta: "Recurring monthly and weekly patterns · suppressed below a minimum period" },
  { id: "s26", num: "26", title: "Business vs personal", group: "Surface 1 · Individual", tag: "Surface 1", meta: "With user override that persists" },
  { id: "s27", num: "27", title: "Balance behaviour", group: "Surface 1 · Individual", tag: "Surface 1", meta: "Average, minimum, retention, runway, lowest point" },
  { id: "s28", num: "28", title: "Unavailable state", group: "Surface 1 · Individual", tag: "Surface 1", meta: "The most important interface behaviour in the product" },
  { id: "s29", num: "29", title: "Obligations & ajo", group: "Surface 1 · Individual", tag: "Surface 1", meta: "What you already owe — and the ajo that counts in your favour" },
  { id: "s30", num: "30", title: "My readiness", group: "Surface 1 · Individual", tag: "Surface 1", meta: "The same analysis a lender would see, framed as your own position" },
  { id: "s31", num: "31", title: "Export preview", group: "Surface 1 · Individual", tag: "Surface 1", meta: "PDF carries the logo, the tiers, the audit result and coverage" },
  { id: "s64", num: "64", title: "Income stability", group: "Surface 1 · Individual", tag: "Surface 1", meta: "/diagnostic/income-stability · how consistent income is, month to month" },
  { id: "s63", num: "63", title: "Financial health playbook", group: "Surface 1 · Individual", tag: "Surface 1", meta: "/ai/financial-health-playbook · structured recommendations, not prose" },
  { id: "s69", num: "69", title: "Mobile layouts", group: "Surface 1 · Individual", tag: "Surface 1", meta: "Most people meet Scanwick on a phone, mid-application · these are the screens that matter at 375px" },
  { id: "s32", num: "32", title: "Account audit", group: "Audit", tag: "Audit", meta: "Statement audit consolidated across every account — not one file at a time" },
  { id: "s33", num: "33", title: "Borrower access trail", group: "Audit", tag: "Audit", meta: "The borrower’s access trail · required by rule R8" },
  { id: "s34", num: "34", title: "Institution access log", group: "Audit", tag: "Audit", meta: "Institution admin · which of your staff accessed which borrower" },
  { id: "s61", num: "61", title: "Analysis run record", group: "Audit", tag: "Audit", meta: "Reconciliation · one record per analysis run · the provenance behind every figure" },
  { id: "s35", num: "35", title: "Assessments", group: "Surface 2 · Lending", tag: "Surface 2", tagClass: "s2", meta: "Institution home · one assessment is one borrower across all their accounts" },
  { id: "s65", num: "65", title: "Institution home", group: "Surface 2 · Lending", tag: "Surface 2", tagClass: "s2", meta: "Where a lender lands after signing in · the equivalent of screen 17 for an institution" },
  { id: "s36", num: "36", title: "New assessment", group: "Surface 2 · Lending", tag: "Surface 2", tagClass: "s2", meta: "Consent first · then statements · then analysis" },
  { id: "s37", num: "37", title: "Signal set", group: "Surface 2 · Lending", tag: "Surface 2", tagClass: "s2", meta: "Adaeze Nwankwo · 3 accounts · created 02 Aug 2026 · valid to 01 Sep" },
  { id: "s38", num: "38", title: "Lender brief", group: "Surface 2 · Lending", tag: "Surface 2", tagClass: "s2", meta: "Written prose a credit officer can read in three minutes and take to committee" },
  { id: "s39", num: "39", title: "Traceability", group: "Surface 2 · Lending", tag: "Surface 2", tagClass: "s2", meta: "Any figure → the transactions → the original statement row and page" },
  { id: "s40", num: "40", title: "Loan stacking", group: "Surface 2 · Lending", tag: "Surface 2", tagClass: "s2", meta: "Detected in real time · a bureau cannot see this yet" },
  { id: "s41", num: "41", title: "Borrower type", group: "Surface 2 · Lending", tag: "Surface 2", tagClass: "s2", meta: "Descriptive classification with cited evidence · no score" },
  { id: "s42", num: "42", title: "Create share link", group: "Surface 2 · Lending", tag: "Surface 2", tagClass: "s2", meta: "The borrower generates it and names the recipient" },
  { id: "s43", num: "43", title: "Manage shares", group: "Surface 2 · Lending", tag: "Surface 2", tagClass: "s2", meta: "The borrower sees who holds what, and can revoke from one screen" },
  { id: "s44", num: "44", title: "Recipient view", group: "Surface 2 · Lending", tag: "Surface 2", tagClass: "s2", meta: "What the named lender sees when they open the link — no Scanwick account needed" },
  { id: "s45", num: "45", title: "Monitoring consent", group: "Surface 3 · Monitoring", tag: "Surface 3", tagClass: "s3", meta: "Two consents granted together at disbursement · connection and sharing" },
  { id: "s46", num: "46", title: "Portfolio", group: "Surface 3 · Monitoring", tag: "Surface 3", tagClass: "s3", meta: "The screen a portfolio officer opens every morning · sorted by severity" },
  { id: "s47", num: "47", title: "Facility detail", group: "Surface 3 · Monitoring", tag: "Surface 3", tagClass: "s3", meta: "Blessing Etim · ₦400,000 disbursed 12 Jun 2026 · monitored weekly" },
  { id: "s48", num: "48", title: "Signal detail", group: "Surface 3 · Monitoring", tag: "Surface 3", tagClass: "s3", meta: "Severity, evidence, recommended action and recommended timing" },
  { id: "s49", num: "49", title: "Acknowledge", group: "Surface 3 · Monitoring", tag: "Surface 3", tagClass: "s3", meta: "The only mechanism by which signal quality can be measured" },
  { id: "s50", num: "50", title: "Notifications", group: "Surface 3 · Monitoring", tag: "Surface 3", tagClass: "s3", meta: "Immediate for Act and Urgent · digest for Watch and Informational", liveLink: "/notifications" },
  { id: "s51", num: "51", title: "Consent centre", group: "Consent & Institution", tag: "Consent", meta: "The borrower's own view · rule R8" },
  { id: "s52", num: "52", title: "Consent request", group: "Consent & Institution", tag: "Consent", meta: "What a borrower receives when a lender initiates · mobile-first" },
  { id: "s53", num: "53", title: "Team & roles", group: "Consent & Institution", tag: "Account", meta: "Institution admin · role separation is a correctness requirement, not a convenience" },
  { id: "s54", num: "54", title: "Credit ledger", group: "Consent & Institution", tag: "Account", meta: "Append-only · quota enforced at creation, never at read" },
  { id: "s55", num: "55", title: "Plans", group: "Consent & Institution", tag: "Account", meta: "Assessments, not seats · priced against the value of the decision", liveLink: "/account" },
  { id: "s56", num: "56", title: "API & webhooks", group: "Consent & Institution", tag: "Account", meta: "Premium · server-to-server, so signals reach the lender's own system" },
  { id: "s57", num: "57", title: "User account", group: "Account", tag: "Account", meta: "Profile, security, plan, connections, data", liveLink: "/account" },
  { id: "s68", num: "68", title: "Delete account", group: "Account", tag: "Account", meta: "/delete-account · /delete-account/cancel · with a recovery window" },
  { id: "s67", num: "67", title: "Security & activity", group: "Account", tag: "Account", meta: "/2fa · /sessions · /login-history · asked for in institutional procurement" },
  { id: "s66", num: "66", title: "Billing & payments", group: "Account", tag: "Account", meta: "/checkout · /verify · /subscription · /history · /cancel", liveLink: "/account" },
  { id: "s58", num: "58", title: "Connect trading records", group: "Trading records", tag: "Conditional", meta: "Optional · order or sales data to compare against bank inflow" },
  { id: "s59", num: "59", title: "Cash-gap verification", group: "Trading records", tag: "Conditional", meta: "Did the money you recorded actually arrive?" },
  { id: "s73", num: "73", title: "Email templates", group: "Reference", tag: "Reference", tagClass: "sys", meta: "Seven transactional emails · plain text, no marketing" },
  { id: "s71", num: "71", title: "Empty states", group: "Reference", tag: "Reference", tagClass: "sys", meta: "A brand-new account, and every screen before it has data" },
  { id: "s70", num: "70", title: "Loading & skeletons", group: "Reference", tag: "Reference", tagClass: "sys", meta: "Every data screen needs one · a spinner with no state is not acceptable" },
  { id: "s60", num: "60", title: "Screen index & flows", group: "Reference", tag: "Reference", tagClass: "sys", meta: "61 screens · 13 sources · three surfaces" },
];

export default function Playground() {
  const [activeScreenId, setActiveScreenId] = useState<string>("s00");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<string>("all");

  const groups = useMemo(() => {
    const set = new Set(SCREENS.map((s) => s.group));
    return ["all", ...Array.from(set)];
  }, []);

  const filteredScreens = useMemo(() => {
    return SCREENS.filter((s) => {
      const matchGroup = selectedGroup === "all" || s.group === selectedGroup;
      const matchSearch =
        searchTerm.trim() === "" ||
        s.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.num.includes(searchTerm) ||
        s.meta.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.group.toLowerCase().includes(searchTerm.toLowerCase());
      return matchGroup && matchSearch;
    });
  }, [selectedGroup, searchTerm]);

  const activeScreen = useMemo(() => {
    return SCREENS.find((s) => s.id === activeScreenId) || SCREENS[0];
  }, [activeScreenId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const currentIndex = filteredScreens.findIndex((s) => s.id === activeScreenId);
        if (currentIndex === -1) return;
        const nextIndex = e.key === "ArrowDown" ? Math.min(currentIndex + 1, filteredScreens.length - 1) : Math.max(currentIndex - 1, 0);
        const nextScreen = filteredScreens[nextIndex];
        if (nextScreen) {
          setActiveScreenId(nextScreen.id);
          window.scrollTo({ top: 0, behavior: "smooth" });
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeScreenId, filteredScreens]);

  const groupedScreens = useMemo(() => {
    const map = new Map<string, ScreenDef[]>();
    filteredScreens.forEach((s) => {
      if (!map.has(s.group)) map.set(s.group, []);
      map.get(s.group)!.push(s);
    });
    return map;
  }, [filteredScreens]);

  return (
    <div className="scanwick-proto-wrapper">
      <style>{`
        .scanwick-proto-wrapper {
          --g900: #00220F;
          --g800: #00361C;
          --g700: #0A4A2A;
          --g600: #12603A;
          --g500: #1B7A4B;
          --g300: #7FC7A3;
          --g100: #DCEFE4;
          --g50: #F1F8F4;
          --ink: #0E1512;
          --ink2: #3E4A44;
          --ink3: #6B7A72;
          --line: #DCE3DF;
          --bg: #F7F9F8;
          --white: #ffffff;
          --warn: #B45309;
          --warnbg: #FEF6E7;
          --stop: #9B2C2C;
          --stopbg: #FDECEC;
          --info: #1D4ED8;
          --infobg: #EEF3FF;
          --r: 10px;
          --sh: 0 1px 3px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.04);
          --f: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          --mono: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
          font-family: var(--f);
          background: var(--bg);
          color: var(--ink);
          font-size: 14px;
          line-height: 1.5;
          min-height: 100vh;
          display: flex;
        }

        .proto-side {
          width: 280px;
          flex: 0 0 280px;
          background: var(--g900);
          color: #CFE0D6;
          position: sticky;
          top: 0;
          height: 100vh;
          overflow-y: auto;
          padding: 16px 0 60px;
          border-right: 1px solid rgba(255,255,255,0.08);
          display: flex;
          flex-direction: column;
        }

        .proto-brand {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 0 18px 14px;
          border-bottom: 1px solid rgba(255,255,255,0.08);
        }

        .proto-brand .mk {
          width: 32px;
          height: 32px;
          border-radius: 7px;
          background: var(--g300);
          display: grid;
          place-items: center;
          color: var(--g900);
          font-weight: 800;
          font-size: 15px;
        }

        .proto-brand b {
          color: #fff;
          font-size: 15px;
          letter-spacing: -0.2px;
        }

        .proto-brand span {
          display: block;
          font-size: 10px;
          color: #7FA791;
          font-weight: 600;
          letter-spacing: 0.5px;
          text-transform: uppercase;
        }

        .proto-search-box {
          padding: 12px 14px 8px;
        }

        .proto-search-input {
          width: 100%;
          background: rgba(255,255,255,0.07);
          border: 1px solid rgba(255,255,255,0.12);
          border-radius: 6px;
          padding: 7px 10px 7px 30px;
          color: #fff;
          font-size: 12px;
          outline: none;
        }
        .proto-search-input:focus {
          border-color: var(--g300);
          background: rgba(255,255,255,0.1);
        }

        .proto-group-header {
          padding: 12px 18px 4px;
          font-size: 10px;
          letter-spacing: 0.9px;
          text-transform: uppercase;
          color: #6E9A81;
          font-weight: 700;
        }

        .proto-nav-link {
          display: flex;
          gap: 8px;
          align-items: center;
          padding: 6.5px 18px;
          color: #CFE0D6;
          text-decoration: none;
          font-size: 12.5px;
          border-left: 3px solid transparent;
          cursor: pointer;
          transition: background 0.15s ease, color 0.15s ease;
        }
        .proto-nav-link:hover {
          background: rgba(255,255,255,0.06);
          color: #fff;
        }
        .proto-nav-link.active {
          background: rgba(127,199,163,0.14);
          border-left-color: var(--g300);
          color: #fff;
          font-weight: 600;
        }
        .proto-nav-link i {
          font-style: normal;
          width: 20px;
          font-size: 10px;
          color: #6E9A81;
          font-family: var(--mono);
        }

        .proto-main {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
        }

        .proto-topbar {
          background: #fff;
          border-bottom: 1px solid var(--line);
          padding: 12px 32px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          position: sticky;
          top: 0;
          z-index: 10;
        }

        .proto-content-area {
          padding: 28px 36px 80px;
          max-width: 1240px;
          width: 100%;
          margin: 0 auto;
        }

        .scrhead {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 20px;
          padding-bottom: 14px;
          border-bottom: 1px solid var(--line);
          margin-bottom: 22px;
        }
        .scrhead h1 {
          font-size: 22px;
          letter-spacing: -0.4px;
          margin-bottom: 4px;
          font-weight: 700;
          color: var(--ink);
        }
        .scrhead .meta {
          font-size: 12.5px;
          color: var(--ink3);
        }

        .tag {
          display: inline-block;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 0.5px;
          text-transform: uppercase;
          padding: 3px 8px;
          border-radius: 20px;
          background: var(--g100);
          color: var(--g700);
        }
        .tag.s2 { background: #E8EEFB; color: #1D4ED8; }
        .tag.s3 { background: #F3EAFB; color: #6B21A8; }
        .tag.sys { background: #EFEFEF; color: #444; }
        .tag.pub { background: #FFF3E0; color: #8A5200; }

        .note {
          background: #FFFDF5;
          border: 1px solid #F0E4C0;
          border-left: 4px solid #D4A72C;
          padding: 12px 16px;
          border-radius: 8px;
          margin: 16px 0;
          font-size: 12.5px;
          color: #5C4A16;
          line-height: 1.6;
        }
        .note b {
          display: block;
          font-size: 10px;
          letter-spacing: 0.7px;
          text-transform: uppercase;
          color: #8A6D16;
          margin-bottom: 4px;
        }
        .note ul { margin: 6px 0 0 16px; }
        .note li { margin: 3px 0; }

        .card {
          background: var(--white);
          border: 1px solid var(--line);
          border-radius: var(--r);
          padding: 20px;
          box-shadow: var(--sh);
        }
        .card h3 {
          font-size: 13.5px;
          margin-bottom: 3px;
          letter-spacing: -0.1px;
          font-weight: 700;
        }
        .card .sub {
          font-size: 11.5px;
          color: var(--ink3);
          margin-bottom: 14px;
        }

        .row { display: grid; gap: 16px; }
        .r2 { grid-template-columns: 1fr 1fr; }
        .r3 { grid-template-columns: repeat(3, 1fr); }
        .r4 { grid-template-columns: repeat(4, 1fr); }
        .r21 { grid-template-columns: 2fr 1fr; }
        .r12 { grid-template-columns: 1fr 2fr; }

        @media (max-width: 900px) {
          .r2, .r3, .r4, .r21, .r12 { grid-template-columns: 1fr; }
          .proto-side { display: none; }
        }

        .kpi .lab {
          font-size: 10.5px;
          color: var(--ink3);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          font-weight: 700;
        }
        .kpi .val {
          font-size: 26px;
          font-weight: 700;
          letter-spacing: -0.8px;
          margin: 5px 0 2px;
          font-family: var(--mono);
        }
        .kpi .dt {
          font-size: 11.5px;
          color: var(--ink3);
        }
        .up { color: var(--g600); font-weight: 600; }
        .dn { color: var(--stop); font-weight: 600; }

        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12.5px;
        }
        th {
          text-align: left;
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0.6px;
          color: var(--ink3);
          font-weight: 700;
          padding: 8px 10px;
          border-bottom: 1px solid var(--line);
          background: var(--g50);
        }
        td {
          padding: 9px 10px;
          border-bottom: 1px solid #EEF2F0;
          vertical-align: top;
        }
        tr:last-child td { border-bottom: 0; }
        td.num, th.num {
          text-align: right;
          font-variant-numeric: tabular-nums;
          font-family: var(--mono);
          font-size: 12px;
        }

        .btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: var(--g800);
          color: #fff;
          border: 0;
          border-radius: 8px;
          padding: 9px 16px;
          font-size: 12.5px;
          font-weight: 600;
          cursor: pointer;
          font-family: var(--f);
          transition: background 0.15s ease;
        }
        .btn:hover { background: var(--g700); }
        .btn.sec {
          background: #fff;
          color: var(--g800);
          border: 1px solid var(--line);
        }
        .btn.sec:hover { background: var(--g50); }
        .btn.gho {
          background: transparent;
          color: var(--ink2);
          border: 1px solid var(--line);
        }
        .btn.gho:hover { background: var(--g50); color: var(--ink); }
        .btn.sm {
          padding: 6px 11px;
          font-size: 11.5px;
        }
        .btn.dgr {
          background: #fff;
          color: var(--stop);
          border: 1px solid #E9C6C6;
        }
        .btn.dgr:hover { background: var(--stopbg); }

        .pill {
          display: inline-block;
          font-size: 10.5px;
          font-weight: 700;
          padding: 2.5px 8px;
          border-radius: 20px;
          letter-spacing: 0.3px;
        }
        .pill.a { background: var(--g100); color: var(--g700); }
        .pill.b { background: #E8EEFB; color: #1D4ED8; }
        .pill.c { background: var(--warnbg); color: var(--warn); }
        .pill.d { background: var(--stopbg); color: var(--stop); }
        .pill.n { background: #EFEFEF; color: #555; }

        .na {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          font-size: 11.5px;
          font-weight: 700;
          color: var(--warn);
          background: var(--warnbg);
          border: 1px dashed #E4C77E;
          padding: 3px 9px;
          border-radius: 6px;
        }

        .bar {
          height: 7px;
          border-radius: 6px;
          background: #EDF2EF;
          overflow: hidden;
        }
        .bar i {
          display: block;
          height: 100%;
          background: var(--g500);
          border-radius: 6px;
        }

        .field { margin-bottom: 13px; }
        .field label {
          display: block;
          font-size: 11.5px;
          font-weight: 600;
          color: var(--ink2);
          margin-bottom: 5px;
        }
        .inp {
          width: 100%;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 9px 12px;
          font-size: 13px;
          font-family: var(--f);
          background: #fff;
          outline: none;
        }
        .inp:focus {
          border-color: var(--g500);
          box-shadow: 0 0 0 2px rgba(27,122,75,0.12);
        }
        .hint {
          font-size: 11px;
          color: var(--ink3);
          margin-top: 4px;
        }
        .mono {
          font-family: var(--mono);
          font-size: 11.5px;
        }
        .trace {
          border-left: 2px solid var(--g300);
          padding-left: 12px;
          margin-top: 8px;
        }
        .src {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: 11.5px;
          background: #fff;
          border: 1px solid var(--line);
          border-radius: 20px;
          padding: 3px 10px 3px 4px;
        }
        .src b {
          width: 19px;
          height: 19px;
          border-radius: 50%;
          background: var(--g700);
          color: #fff;
          display: grid;
          place-items: center;
          font-size: 8.5px;
          font-weight: 700;
        }

        .stepper {
          display: flex;
          gap: 0;
          margin-bottom: 20px;
        }
        .stepper div {
          flex: 1;
          padding: 9px 12px;
          font-size: 11.5px;
          border-bottom: 3px solid var(--line);
          color: var(--ink3);
        }
        .stepper div.on {
          border-bottom-color: var(--g600);
          color: var(--g800);
          font-weight: 700;
        }
        .stepper div.done {
          border-bottom-color: var(--g300);
          color: var(--g600);
        }

        .ph {
          background: repeating-linear-gradient(45deg, #F4F7F5, #F4F7F5 8px, #EDF2EF 8px, #EDF2EF 16px);
          border: 1px dashed var(--line);
          border-radius: 8px;
          display: grid;
          place-items: center;
          color: var(--ink3);
          font-size: 11.5px;
        }
        .spark {
          display: flex;
          align-items: flex-end;
          gap: 3px;
          height: 44px;
        }
        .spark i {
          flex: 1;
          background: var(--g300);
          border-radius: 2px 2px 0 0;
          display: block;
        }
        .sev {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          display: inline-block;
          margin-right: 6px;
        }
        .sev.i { background: #9AA6A0; }
        .sev.w { background: #D4A72C; }
        .sev.a { background: #D97706; }
        .sev.u { background: #B91C1C; }

        .mob {
          width: 300px;
          border: 9px solid #12211A;
          border-radius: 30px;
          background: #fff;
          overflow: hidden;
          box-shadow: var(--sh);
        }
        .mob .bar2 {
          height: 22px;
          background: var(--g900);
        }
        code {
          background: #F1F5F3;
          padding: 1px 5px;
          border-radius: 4px;
          font-family: var(--mono);
          font-size: 11.5px;
        }
        .legend {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
          font-size: 11.5px;
          color: var(--ink3);
          margin-top: 10px;
        }
        .swatch {
          height: 56px;
          border-radius: 8px;
          border: 1px solid rgba(0,0,0,0.06);
        }
      `}</style>

      {/* Sidebar */}
      <nav className="proto-side">
        <div className="proto-brand">
          <div className="mk">S</div>
          <div>
            <b>Scanwick</b>
            <span>Product Prototype · 61 Screens</span>
          </div>
        </div>

        <div className="proto-search-box">
          <div style={{ position: "relative" }}>
            <Search size={14} style={{ position: "absolute", left: 9, top: 9, color: "#7FA791" }} />
            <input
              type="text"
              placeholder="Search 61 screens..."
              className="proto-search-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 8 }}>
            {groups.map((grp) => (
              <button
                key={grp}
                type="button"
                onClick={() => setSelectedGroup(grp)}
                style={{
                  background: selectedGroup === grp ? "rgba(127,199,163,0.2)" : "rgba(255,255,255,0.05)",
                  color: selectedGroup === grp ? "#fff" : "#9FBFAE",
                  border: selectedGroup === grp ? "1px solid var(--g300)" : "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 12,
                  padding: "2px 8px",
                  fontSize: 10,
                  cursor: "pointer",
                  fontWeight: selectedGroup === grp ? 700 : 500,
                  textTransform: "capitalize",
                }}
              >
                {grp}
              </button>
            ))}
          </div>
        </div>

        <div style={{ overflowY: "auto", flex: 1, paddingBottom: 20 }}>
          {Array.from(groupedScreens.entries()).map(([grp, list]) => (
            <div key={grp}>
              <div className="proto-group-header">{grp}</div>
              {list.map((scr) => (
                <div
                  key={scr.id}
                  className={`proto-nav-link ${activeScreenId === scr.id ? "active" : ""}`}
                  onClick={() => {
                    setActiveScreenId(scr.id);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  <i>{scr.num}</i>
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {scr.title}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </nav>

      {/* Main content */}
      <main className="proto-main">
        {/* Top sticky bar */}
        <header className="proto-topbar">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="mono" style={{ background: "var(--g100)", color: "var(--g800)", padding: "3px 8px", borderRadius: 4, fontWeight: 700 }}>
              Screen {activeScreen.num}
            </span>
            <b style={{ fontSize: 15, color: "var(--ink)" }}>{activeScreen.title}</b>
            <span className={`tag ${activeScreen.tagClass || ""}`}>{activeScreen.tag}</span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {activeScreen.liveLink ? (
              <Link to={activeScreen.liveLink as any} className="btn sm sec" style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
                <span>Open Live Page</span>
                <ExternalLink size={12} />
              </Link>
            ) : null}
            <Link to="/" className="btn sm gho">
              Back to App
            </Link>
          </div>
        </header>

        {/* Screen viewer */}
        <div className="proto-content-area">
          {/* s00: Design System */}
          {activeScreenId === "s00" && (
            <section>
              <div className="scrhead">
                <div>
                  <h1>Design system</h1>
                  <div className="meta">Tokens, components and the rules that are product requirements rather than taste</div>
                </div>
                <span className="tag sys">Reference</span>
              </div>
              <div className="note">
                <b>Read this first</b>Three rules below are specified in the PRD and are not open to visual reinterpretation: an unavailable value never renders as zero or a dash; coverage is always visible, never hidden behind a tooltip; and audit findings never use alarm styling. Everything else is yours to improve.
              </div>
              <div className="card" style={{ marginBottom: 16 }}>
                <h3>Brand palette</h3>
                <div className="sub">Taken from the Scanwick wordmark. One dark base, one accent, restrained use.</div>
                <div className="row r4">
                  <div>
                    <div className="swatch" style={{ background: "#00220F" }} />
                    <div className="mono" style={{ marginTop: 6 }}>--g900 #00220F</div>
                  </div>
                  <div>
                    <div className="swatch" style={{ background: "#00361C" }} />
                    <div className="mono" style={{ marginTop: 6 }}>--g800 #00361C · brand</div>
                  </div>
                  <div>
                    <div className="swatch" style={{ background: "#12603A" }} />
                    <div className="mono" style={{ marginTop: 6 }}>--g600 #12603A</div>
                  </div>
                  <div>
                    <div className="swatch" style={{ background: "#7FC7A3" }} />
                    <div className="mono" style={{ marginTop: 6 }}>--g300 #7FC7A3</div>
                  </div>
                </div>
                <div className="row r4" style={{ marginTop: 14 }}>
                  <div>
                    <div className="swatch" style={{ background: "#DCEFE4" }} />
                    <div className="mono" style={{ marginTop: 6 }}>--g100 surface</div>
                  </div>
                  <div>
                    <div className="swatch" style={{ background: "#B45309" }} />
                    <div className="mono" style={{ marginTop: 6 }}>--warn unavailable</div>
                  </div>
                  <div>
                    <div className="swatch" style={{ background: "#9B2C2C" }} />
                    <div className="mono" style={{ marginTop: 6 }}>--stop urgent only</div>
                  </div>
                  <div>
                    <div className="swatch" style={{ background: "#0E1512" }} />
                    <div className="mono" style={{ marginTop: 6 }}>--ink text</div>
                  </div>
                </div>
              </div>

              <div className="row r2" style={{ marginBottom: 16 }}>
                <div className="card">
                  <h3>Type scale</h3>
                  <div className="sub">Inter. Numbers are tabular and monospaced everywhere money appears.</div>
                  <div style={{ fontSize: 25, fontWeight: 700, letterSpacing: -0.8 }}>
                    ₦4,182,600 <span style={{ fontSize: 12, color: "var(--ink3)", fontWeight: 400 }}>KPI · 25/700/-0.8</span>
                  </div>
                  <div style={{ fontSize: 20, letterSpacing: -0.4, marginTop: 8 }}>
                    Screen title <span style={{ fontSize: 12, color: "var(--ink3)" }}>20/600/-0.4</span>
                  </div>
                  <div style={{ fontSize: 14, marginTop: 8 }}>Body copy at 14/1.5 — the default</div>
                  <div style={{ fontSize: 12.5, marginTop: 6 }}>Table and dense UI at 12.5</div>
                  <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 0.6, color: "var(--ink3)", fontWeight: 700, marginTop: 6 }}>
                    Label · 10/700/.6 uppercase
                  </div>
                </div>
                <div className="card">
                  <h3>Money &amp; dates</h3>
                  <div className="sub">Non-negotiable formatting.</div>
                  <table>
                    <tbody>
                      <tr>
                        <td>Currency</td>
                        <td className="num">₦4,182,600.00</td>
                      </tr>
                      <tr>
                        <td>Negative</td>
                        <td className="num" style={{ color: "var(--stop)" }}>−₦58,200.00</td>
                      </tr>
                      <tr>
                        <td>Unavailable</td>
                        <td className="num"><span className="na">Unavailable</span></td>
                      </tr>
                      <tr>
                        <td>Date shown to user</td>
                        <td className="num">15 Jul 2026</td>
                      </tr>
                      <tr>
                        <td>Date as printed by bank</td>
                        <td className="num">15/07/26 <span className="pill n">Kuda</span></td>
                      </tr>
                    </tbody>
                  </table>
                  <div className="hint" style={{ marginTop: 8 }}>
                    Always show the bank's own date format alongside ours when a row is opened — a user checking against their statement needs to recognise it.
                  </div>
                </div>
              </div>

              <div className="row r3" style={{ marginBottom: 16 }}>
                <div className="card">
                  <h3>Source tier badge</h3>
                  <div className="sub">On every account, assessment and export.</div>
                  <p><span className="pill a">Tier A · Direct</span> API connection</p>
                  <p style={{ marginTop: 7 }}><span className="pill b">Tier B · Verified file</span> signature matched</p>
                  <p style={{ marginTop: 7 }}><span className="pill c">Tier C · Unverified</span> parses, provenance unknown</p>
                  <p style={{ marginTop: 7 }}><span className="pill d">Tier D · Rejected</span> not analysed</p>
                </div>
                <div className="card">
                  <h3>Signal severity</h3>
                  <div className="sub">Monitoring only. Never used for audit findings.</div>
                  <p><span className="sev i" />Informational — no action</p>
                  <p style={{ marginTop: 7 }}><span className="sev w" />Watch — observe next cycle</p>
                  <p style={{ marginTop: 7 }}><span className="sev a" />Act — contact within stated days</p>
                  <p style={{ marginTop: 7 }}><span className="sev u" />Urgent — immediate contact</p>
                </div>
                <div className="card">
                  <h3>Buttons</h3>
                  <div className="sub">One primary per screen.</div>
                  <p><button className="btn">Primary</button> <button className="btn sec">Secondary</button></p>
                  <p style={{ marginTop: 9 }}><button className="btn gho sm">Ghost small</button> <button className="btn dgr sm">Destructive</button></p>
                  <div className="hint" style={{ marginTop: 10 }}>Destructive is only for revoking consent or a share link.</div>
                </div>
              </div>

              <div className="note">
                <b>The three rules</b>
                <ul>
                  <li><b>Unavailable is a first-class state.</b> When the backend returns unavailable-with-reason, render the amber <span className="na">Unavailable</span> chip and the reason. Never a zero, never an em dash, never a blank cell.</li>
                  <li><b>Coverage is always on screen.</b> Which accounts, which periods, what could not be determined.</li>
                  <li><b>Audit findings use neutral styling.</b> No red, no warning triangles, no alarm language.</li>
                </ul>
              </div>
            </section>
          )}

          {/* s01: Landing Page */}
          {activeScreenId === "s01" && (
            <section>
              <div className="scrhead">
                <div>
                  <h1>Landing page</h1>
                  <div className="meta">scanwick.com · full page, top to bottom · two audiences split at the hero</div>
                </div>
                <span className="tag pub">Public</span>
              </div>
              <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                {/* Nav */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 32px", borderBottom: "1px solid var(--line)", background: "#fff" }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <div style={{ width: 26, height: 26, borderRadius: 6, background: "var(--g800)", color: "#fff", display: "grid", placeItems: "center", fontWeight: 800, fontSize: 13 }}>S</div>
                    <b style={{ fontSize: 15, letterSpacing: -0.3 }}>Scanwick</b>
                  </div>
                  <div style={{ display: "flex", gap: 22, alignItems: "center", fontSize: 12.5, color: "var(--ink2)" }}>
                    <span>For individuals</span><span>For lenders</span><span>Security</span><span>Pricing</span><span>About</span>
                    <Link to="/login" className="btn gho sm">Sign in</Link>
                    <Link to="/register" className="btn sm">Get started</Link>
                  </div>
                </div>

                {/* Hero */}
                <div style={{ background: "var(--g900)", color: "#fff", padding: "52px 32px 44px" }}>
                  <div style={{ maxWidth: 720, margin: "0 auto", textAlign: "center" }}>
                    <div style={{ fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", color: "var(--g300)", fontWeight: 700, marginBottom: 16 }}>Bank statement intelligence for Africa</div>
                    <h2 style={{ fontSize: 38, lineHeight: 1.15, letterSpacing: -1.4, fontWeight: 700 }}>Money moves through African accounts and nobody can read it.</h2>
                    <p style={{ marginTop: 16, fontSize: 15, color: "#CFE0D6", lineHeight: 1.65 }}>
                      Scanwick reads bank statements across every account a person holds — thirteen Nigerian banks and wallets — and turns them into an answer. For the person whose money it is, and for the institution deciding whether to lend.
                    </p>
                  </div>
                  <div className="row r2" style={{ maxWidth: 820, margin: "34px auto 0", gap: 18 }}>
                    <div style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(127,199,163,0.3)", borderRadius: 12, padding: 24 }}>
                      <div style={{ fontSize: 11, letterSpacing: 0.8, textTransform: "uppercase", color: "var(--g300)", fontWeight: 700, marginBottom: 9 }}>I want to understand my money</div>
                      <div style={{ fontSize: 17, fontWeight: 700, lineHeight: 1.35, marginBottom: 9 }}>Where did your money go last month?</div>
                      <div style={{ fontSize: 12.5, color: "#CFE0D6", lineHeight: 1.6, marginBottom: 16 }}>Every naira is in your statement. It is just spread across two hundred rows, in bank formatting, across three or four accounts that never meet.</div>
                      <Link to="/upload" className="btn" style={{ background: "var(--g300)", color: "var(--g900)", width: "100%", justifyContent: "center" }}>See my money — free</Link>
                    </div>
                    <div style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.14)", borderRadius: 12, padding: 24 }}>
                      <div style={{ fontSize: 11, letterSpacing: 0.8, textTransform: "uppercase", color: "#9FBFAE", fontWeight: 700, marginBottom: 9 }}>I assess borrowers</div>
                      <div style={{ fontSize: 17, fontWeight: 700, lineHeight: 1.35, marginBottom: 9 }}>Eight in ten applications fail on legibility, not affordability.</div>
                      <div style={{ fontSize: 12.5, color: "#CFE0D6", lineHeight: 1.6, marginBottom: 16 }}>Consolidate a borrower's accounts into one picture, with every figure traceable to the transaction behind it — then keep watching after you lend.</div>
                      <button className="btn sec" style={{ background: "transparent", color: "#fff", borderColor: "rgba(255,255,255,0.3)", width: "100%", justifyContent: "center" }}>Book a walkthrough</button>
                    </div>
                  </div>
                  <div style={{ textAlign: "center", marginTop: 26, fontSize: 11, color: "#7FA791", letterSpacing: 0.3 }}>
                    OPay · PalmPay · Kuda · Moniepoint · Wema · GTBank · UBA · Zenith · First Bank · Sterling · Access · Stanbic IBTC · Alpha Morgan
                  </div>
                </div>

                {/* Problem */}
                <div style={{ padding: "44px 32px", borderBottom: "1px solid var(--line)" }}>
                  <div style={{ maxWidth: 900, margin: "0 auto" }}>
                    <h3 style={{ fontSize: 23, letterSpacing: -0.6, marginBottom: 8 }}>Nigeria has a legibility problem, not a credit problem</h3>
                    <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.75, maxWidth: 640 }}>
                      The country is not short of borrowers who can repay. It is short of borrowers whose ability to repay can be read. A statement is a list of transactions, not an answer — and the average person holds three or four of them.
                    </p>
                    <div className="row r3" style={{ marginTop: 26 }}>
                      <div style={{ borderLeft: "3px solid var(--g500)", paddingLeft: 14 }}>
                        <div style={{ fontSize: 27, fontWeight: 700, letterSpacing: -0.9 }}>8–9 in 10</div>
                        <div style={{ fontSize: 12.5, color: "var(--ink3)", marginTop: 3 }}>loan applications declined — most often because transactions are scattered across accounts and cannot be reconciled</div>
                      </div>
                      <div style={{ borderLeft: "3px solid var(--g500)", paddingLeft: 14 }}>
                        <div style={{ fontSize: 27, fontWeight: 700, letterSpacing: -0.9 }}>13</div>
                        <div style={{ fontSize: 12.5, color: "var(--ink3)", marginTop: 3 }}>Nigerian banks and wallets read natively — each with its own date convention, layout and traps</div>
                      </div>
                      <div style={{ borderLeft: "3px solid var(--g500)", paddingLeft: 14 }}>
                        <div style={{ fontSize: 27, fontWeight: 700, letterSpacing: -0.9 }}>6</div>
                        <div style={{ fontSize: 12.5, color: "var(--ink3)", marginTop: 3 }}>different date conventions across those sources. One is month-first, one is day-first, and they appear in the same person's files</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* s02: Create Account */}
          {activeScreenId === "s02" && (
            <section>
              <div className="scrhead">
                <div>
                  <h1>Create account</h1>
                  <div className="meta">Individual sign-up · consent captured at first step</div>
                </div>
                <span className="tag pub">Public</span>
              </div>
              <div className="row r2">
                <div className="card" style={{ maxWidth: 420 }}>
                  <h3>Create your Scanwick account</h3>
                  <div className="sub">Free — one account, one analysis a month.</div>
                  <div className="field"><label>Full name</label><input className="inp" defaultValue="Adaeze Nwankwo" /></div>
                  <div className="field"><label>Email</label><input className="inp" defaultValue="adaeze.n@example.com" /></div>
                  <div className="field"><label>Phone number</label><input className="inp" defaultValue="0803 000 0000" /></div>
                  <div className="field"><label>Password</label><input className="inp" type="password" defaultValue="············" /><div className="hint">At least 10 characters.</div></div>
                  <div style={{ display: "flex", gap: 9, alignItems: "flex-start", margin: "14px 0" }}>
                    <input type="checkbox" defaultChecked style={{ marginTop: 3 }} />
                    <div style={{ fontSize: 12, color: "var(--ink2)" }}>
                      I have read and agree to the <a href="#" style={{ color: "var(--g700)" }}>Terms of Service</a> and <a href="#" style={{ color: "var(--g700)" }}>Privacy Policy</a>, and I consent to Scanwick creating an account for me.
                    </div>
                  </div>
                  <Link to="/register" className="btn" style={{ width: "100%", justifyContent: "center" }}>Create account</Link>
                  <div className="hint" style={{ textAlign: "center", marginTop: 12 }}>
                    Already have an account? <Link to="/login" style={{ color: "var(--g700)" }}>Sign in</Link>
                  </div>
                </div>
                <div>
                  <div className="note" style={{ marginTop: 0 }}>
                    <b>Consent design</b>This checkbox is ACCOUNT_CONNECTION consent only. It does not authorise analysis, sharing or monitoring — those are separate consent events captured later.
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* s03: Sign in */}
          {activeScreenId === "s03" && (
            <section>
              <div className="scrhead">
                <div>
                  <h1>Sign in</h1>
                  <div className="meta">Email and password, then OTP</div>
                </div>
                <span className="tag pub">Public</span>
              </div>
              <div className="row r2">
                <div className="card" style={{ maxWidth: 420 }}>
                  <h3>Welcome back</h3>
                  <div className="sub">Sign in to your Scanwick account.</div>
                  <div className="field"><label>Email</label><input className="inp" defaultValue="ranashahmeerali@gmail.com" /></div>
                  <div className="field"><label>Password</label><input className="inp" type="password" defaultValue="Rana1234pass" /></div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "6px 0 16px" }}>
                    <label style={{ fontSize: 12, display: "flex", gap: 7, alignItems: "center" }}><input type="checkbox" defaultChecked /> Keep me signed in</label>
                    <Link to="/getcode" style={{ fontSize: 12, color: "var(--g700)" }}>Forgot password?</Link>
                  </div>
                  <Link to="/login" className="btn" style={{ width: "100%", justifyContent: "center" }}>Continue to Live Login</Link>
                </div>
                <div className="card">
                  <h3>States to design</h3>
                  <table>
                    <tbody>
                      <tr><td>Wrong credentials</td><td>One generic message. Never reveal whether the email exists.</td></tr>
                      <tr><td>Rate limited</td><td>After repeated attempts — show wait time, not a lockout dead end</td></tr>
                      <tr><td>Account suspended</td><td>Explain and give a contact route</td></tr>
                      <tr><td>Session expired</td><td>Return the user to where they were after sign-in</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          )}

          {/* s06: Add accounts */}
          {activeScreenId === "s06" && (
            <section>
              <div className="scrhead">
                <div>
                  <h1>Add accounts</h1>
                  <div className="meta">13 sources · connect by API where available, upload a file otherwise</div>
                </div>
                <span className="tag">Ingestion</span>
              </div>
              <div className="stepper">
                <div className="on">1 · Add accounts</div>
                <div>2 · Processing</div>
                <div>3 · Review coverage</div>
                <div>4 · Your money</div>
              </div>
              <div className="row r21">
                <div className="card">
                  <h3>Wallets</h3>
                  <div className="sub">4 sources</div>
                  <div className="row r4" style={{ gap: 10 }}>
                    {["OPay", "PalmPay", "Kuda", "Moniepoint"].map((w) => (
                      <div key={w} className="ph" style={{ height: 78, flexDirection: "column", gap: 4, background: "#fff", borderStyle: "solid" }}>
                        <b style={{ color: "var(--ink)" }}>{w}</b>
                        <span className="pill a">Connect</span>
                        <span style={{ fontSize: 9.5 }}>or upload</span>
                      </div>
                    ))}
                  </div>
                  <h3 style={{ marginTop: 20 }}>Banks</h3>
                  <div className="sub">9 sources</div>
                  <div className="row r3" style={{ gap: 10 }}>
                    {["Wema / ALAT", "GTBank", "Sterling", "Alpha Morgan", "UBA", "Zenith", "First Bank", "Access", "Stanbic IBTC"].map((b) => (
                      <div key={b} className="ph" style={{ height: 78, flexDirection: "column", gap: 4, background: "#fff", borderStyle: "solid" }}>
                        <b style={{ color: "var(--ink)" }}>{b}</b>
                        <span className="pill a">Connect</span>
                        <span style={{ fontSize: 9.5 }}>or upload</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="card" style={{ marginBottom: 14 }}>
                    <h3>Added</h3>
                    <table>
                      <tbody>
                        <tr><td><span className="src"><b>GT</b>GTBank ····837</span><div className="hint">Connected 12 Jun</div></td><td className="num"><span className="pill a">A</span></td></tr>
                        <tr><td><span className="src"><b>OP</b>OPay 0803·····00</span><div className="hint">Connected 12 Jun</div></td><td className="num"><span className="pill a">A</span></td></tr>
                        <tr><td><span className="src"><b>KU</b>Kuda ····4412</span><div className="hint">File uploaded 12 Jun</div></td><td className="num"><span className="pill b">B</span></td></tr>
                      </tbody>
                    </table>
                    <Link to="/upload" className="btn sm" style={{ width: "100%", justifyContent: "center", marginTop: 12 }}>Upload Statements</Link>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* s18: Consolidated view */}
          {activeScreenId === "s18" && (
            <section>
              <div className="scrhead">
                <div>
                  <h1>Consolidated view</h1>
                  <div className="meta">The home screen for an individual · every account, one picture</div>
                </div>
                <span className="tag">Surface 1</span>
              </div>
              <div className="row r4" style={{ marginBottom: 16 }}>
                <div className="card kpi"><div className="lab">Money in</div><div className="val">₦4,182,600</div><div className="dt">6 months · <span className="up">▲ 8% vs prior 6</span></div></div>
                <div className="card kpi"><div className="lab">Money out</div><div className="val">₦3,914,180</div><div className="dt">6 months · <span className="dn">▲ 14% vs prior 6</span></div></div>
                <div className="card kpi"><div className="lab">Net position</div><div className="val" style={{ color: "var(--g600)" }}>+₦268,420</div><div className="dt">₦44,737 average per month</div></div>
                <div className="card kpi"><div className="lab">Closing balance</div><div className="val">₦312,880</div><div className="dt">across 3 accounts · 31 Jul</div></div>
              </div>
              <div className="card" style={{ marginBottom: 16, borderLeft: "4px solid var(--g500)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <b style={{ fontSize: 12.5 }}>Internal transfers removed: ₦1,240,000 across 34 movements</b>
                    <div className="hint">Money you moved between your own accounts is not income and not spending. We matched both sides and took them out of the totals above.</div>
                  </div>
                  <button className="btn gho sm">See them</button>
                </div>
              </div>
              <div className="row r21">
                <div className="card">
                  <h3>Month by month</h3>
                  <div className="sub">Inflow, outflow and net across all accounts</div>
                  <div className="spark" style={{ height: 110 }}>
                    <i style={{ height: "52%" }} /><i style={{ height: "64%" }} /><i style={{ height: "48%" }} /><i style={{ height: "79%" }} /><i style={{ height: "58%" }} /><i style={{ height: "88%" }} />
                  </div>
                  <div className="legend"><span>Feb</span><span>Mar</span><span>Apr</span><span>May</span><span>Jun</span><span>Jul</span></div>
                  <table style={{ marginTop: 14 }}>
                    <thead><tr><th>Month</th><th className="num">In</th><th className="num">Out</th><th className="num">Net</th></tr></thead>
                    <tbody>
                      <tr><td>Jul 2026</td><td className="num">₦842,300</td><td className="num">₦701,900</td><td className="num" style={{ color: "var(--g600)" }}>+₦140,400</td></tr>
                      <tr><td>Jun 2026</td><td className="num">₦561,200</td><td className="num">₦688,400</td><td className="num" style={{ color: "var(--stop)" }}>−₦127,200</td></tr>
                      <tr><td>May 2026</td><td className="num">₦758,900</td><td className="num">₦640,100</td><td className="num" style={{ color: "var(--g600)" }}>+₦118,800</td></tr>
                      <tr><td>Apr 2026</td><td className="num">₦461,700</td><td className="num">₦602,300</td><td className="num" style={{ color: "var(--stop)" }}>−₦140,600</td></tr>
                      <tr><td>Mar 2026</td><td className="num">₦614,800</td><td className="num">₦638,900</td><td className="num" style={{ color: "var(--stop)" }}>−₦24,100</td></tr>
                      <tr><td>Feb 2026</td><td className="num">₦943,700</td><td className="num">₦642,580</td><td className="num" style={{ color: "var(--g600)" }}>+₦301,120</td></tr>
                    </tbody>
                  </table>
                </div>
                <div>
                  <div className="card" style={{ marginBottom: 14 }}>
                    <h3>Your accounts</h3>
                    <table>
                      <tbody>
                        <tr><td><span className="src"><b>GT</b>GTBank ····837</span><div className="hint">Jan–Jul · 412 txns</div></td><td className="num"><span className="pill b">B</span><div className="mono" style={{ marginTop: 4 }}>₦186,400</div></td></tr>
                        <tr><td><span className="src"><b>OP</b>OPay 0803·····00</span><div className="hint">Feb–Jul · 918 txns</div></td><td className="num"><span className="pill b">B</span><div className="mono" style={{ marginTop: 4 }}><span className="na">n/a</span></div></td></tr>
                        <tr><td><span className="src"><b>KU</b>Kuda ····4412</span><div className="hint">Jan–Jul · 302 txns</div></td><td className="num"><span className="pill b">B</span><div className="mono" style={{ marginTop: 4 }}>₦126,480</div></td></tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* s38: Lender Brief */}
          {activeScreenId === "s38" && (
            <section>
              <div className="scrhead">
                <div>
                  <h1>Lender brief</h1>
                  <div className="meta">Written prose a credit officer can read in three minutes and take to committee</div>
                </div>
                <span className="tag s2">Surface 2</span>
              </div>
              <div className="row r21">
                <div className="card" style={{ lineHeight: 1.75, fontSize: 13.5 }}>
                  <div style={{ paddingBottom: 14, borderBottom: "1px solid var(--line)", marginBottom: 16 }}>
                    <b style={{ fontSize: 15 }}>Adaeze Nwankwo — assessment brief</b>
                    <div className="hint">Generated 02 Aug 2026 · 3 accounts · 01 Feb – 31 Jul 2026 · 1,632 transactions</div>
                  </div>
                  <p><b>The accounts analysed.</b> Three accounts were consolidated: a GTBank current account and Kuda account covering January to July, and an OPay wallet covering February to July. All three are Tier B — files whose structure matches what those institutions issue. Thirty-four movements between her own accounts, totalling ₦1,240,000, were matched and removed from the totals below.</p>
                  <p style={{ marginTop: 12 }}><b>What the money shows.</b> Average monthly turnover across the six months is ₦697,100, rising over the period rather than falling. Income arrives from 38 distinct paying counterparties with the largest accounting for 17.2%, so the business is not dependent on a single customer. Average balance over the last three months is ₦248,600. She has contributed ₦10,000 weekly to a contributory savings group for 24 consecutive weeks without a break.</p>
                  <p style={{ marginTop: 12 }}><b>What supports lending.</b> Turnover is consistent and rising. Income is well distributed across customers. Existing obligations of ₦63,500 a month represent 9.1% of income, which is low. Repayments to QUICKCASH have been made on time in all six instances. The 24-week savings record is a sustained pattern of financial discipline.</p>
                  <div style={{ marginTop: 16, padding: 13, background: "var(--g50)", borderRadius: 8, fontSize: 12, color: "var(--ink2)" }}>
                    This brief presents evidence from the borrower's own statements. It does not recommend approval or decline, does not state an amount to lend and does not score the borrower.
                  </div>
                </div>
                <div>
                  <div className="card" style={{ marginBottom: 14 }}>
                    <h3>Actions</h3>
                    <button className="btn sm" style={{ width: "100%", justifyContent: "center", marginBottom: 8 }}>Download PDF</button>
                    <button className="btn sec sm" style={{ width: "100%", justifyContent: "center", marginBottom: 8 }}>Re-run assessment</button>
                    <button className="btn gho sm" style={{ width: "100%", justifyContent: "center" }}>Add to monitoring</button>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* s55: Plans */}
          {activeScreenId === "s55" && (
            <section>
              <div className="scrhead">
                <div>
                  <h1>Plans</h1>
                  <div className="meta">Assessments, not seats · priced against the value of the decision</div>
                </div>
                <span className="tag">Account</span>
              </div>
              <div className="row r3" style={{ marginBottom: 16 }}>
                <div className="card">
                  <div className="lab" style={{ color: "var(--ink3)", fontSize: 11, fontWeight: 700 }}>INDIVIDUAL — FREE</div>
                  <div style={{ fontSize: 27, fontWeight: 700, margin: "7px 0" }}>₦0</div>
                  <table>
                    <tbody>
                      <tr><td>1 account</td></tr><tr><td>1 analysis a month</td></tr><tr><td>90 days of history</td></tr><tr><td>Full personal analysis</td></tr>
                    </tbody>
                  </table>
                  <button className="btn sec sm" style={{ width: "100%", justifyContent: "center", marginTop: 13 }}>Current plan</button>
                </div>
                <div className="card" style={{ border: "2px solid var(--g500)" }}>
                  <div className="lab" style={{ color: "var(--g700)", fontSize: 11, fontWeight: 700 }}>INDIVIDUAL — PLUS</div>
                  <div style={{ fontSize: 27, fontWeight: 700, margin: "7px 0" }}>₦2,500<span style={{ fontSize: 13, fontWeight: 500, color: "var(--ink3)" }}>/month</span></div>
                  <table>
                    <tbody>
                      <tr><td>Up to 4 accounts consolidated</td></tr><tr><td>12 months of history</td></tr><tr><td>Unlimited re-runs</td></tr><tr><td>1 verifiable share link a month</td></tr>
                    </tbody>
                  </table>
                  <Link to="/account" className="btn sm" style={{ width: "100%", justifyContent: "center", marginTop: 13 }}>Active Plan</Link>
                </div>
                <div className="card">
                  <div className="lab" style={{ color: "var(--ink3)", fontSize: 11, fontWeight: 700 }}>ENTERPRISE</div>
                  <div style={{ fontSize: 27, fontWeight: 700, margin: "7px 0" }}>Negotiated</div>
                  <table>
                    <tbody>
                      <tr><td>Unlimited seats</td></tr><tr><td>Custom quota</td></tr><tr><td>Dedicated support &amp; SLA</td></tr>
                    </tbody>
                  </table>
                  <button className="btn sec sm" style={{ width: "100%", justifyContent: "center", marginTop: 13 }}>Talk to us</button>
                </div>
              </div>
            </section>
          )}

          {/* Generic fallback / details for any other screen */}
          {activeScreenId !== "s00" && activeScreenId !== "s01" && activeScreenId !== "s02" && activeScreenId !== "s03" && activeScreenId !== "s06" && activeScreenId !== "s18" && activeScreenId !== "s38" && activeScreenId !== "s55" && (
            <section>
              <div className="scrhead">
                <div>
                  <h1>{activeScreen.title}</h1>
                  <div className="meta">{activeScreen.meta}</div>
                </div>
                <span className={`tag ${activeScreen.tagClass || ""}`}>{activeScreen.tag}</span>
              </div>

              <div className="note">
                <b>Screen {activeScreen.num} Specification</b>
                <p style={{ marginTop: 4 }}>This screen is part of the <b>{activeScreen.group}</b> flow in the Scanwick African Fintech Intelligence Suite.</p>
                <div className="mono" style={{ marginTop: 8, color: "var(--g700)" }}>Group: {activeScreen.group} · Tag: {activeScreen.tag} · ID: {activeScreen.id}</div>
              </div>

              <div className="row r2" style={{ marginBottom: 16 }}>
                <div className="card">
                  <h3>Overview &amp; Functional Behavior</h3>
                  <div className="sub">Specifications directly from PRD v3.0 &amp; prototype definitions</div>
                  <p style={{ fontSize: 13, color: "var(--ink2)", lineHeight: 1.7 }}>{activeScreen.meta}</p>
                  <div style={{ marginTop: 14, padding: 12, background: "var(--g50)", borderRadius: 8, fontSize: 12 }}>
                    <b>Design System Alignment:</b> All money fields use monospaced tabular numerals with Nigerian Naira (₦) conventions. Unavailable states render as amber badges rather than zeros or dashes.
                  </div>
                </div>
                <div className="card">
                  <h3>Key Actions &amp; Navigation</h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
                    {activeScreen.liveLink ? (
                      <Link to={activeScreen.liveLink as any} className="btn sm">
                        Open in Live App ({activeScreen.liveLink})
                      </Link>
                    ) : (
                      <button className="btn sm sec" onClick={() => setActiveScreenId("s18")}>
                        View in Consolidated View
                      </button>
                    )}
                    <button className="btn gho sm" onClick={() => setActiveScreenId("s00")}>
                      View Design System Tokens
                    </button>
                    <button className="btn gho sm" onClick={() => setActiveScreenId("s60")}>
                      View Full Screen Index &amp; Flows
                    </button>
                  </div>
                </div>
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
