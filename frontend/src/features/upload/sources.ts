/** Bank / wallet sources for Finance PDF ingestion.
 *  Nine have dedicated parsers in backend/app/services/pdf_parsers/.
 *  Four more appear in the product prototype without parsers yet —
 *  those stay selectable but are marked limited (generic PDF reader).
 */

export type SourceGroup = "wallet" | "bank";

export type ParserSupport = "dedicated" | "limited";

export interface BankSource {
  id: string;
  /** Value sent as bank_name to POST /bank/upload/pdf */
  bankName: string;
  label: string;
  short: string;
  group: SourceGroup;
  parser: ParserSupport;
  formats: string;
  /** How-to steps shown in the per-source panel */
  steps: string[];
  /** Password convention hint — shown on unlock screen and panel */
  passwordHint?: string;
  /** Extra product note (e.g. OPay has no balance column) */
  note?: string;
  noteTone?: "info" | "warn";
}

export const BANK_SOURCES: BankSource[] = [
  {
    id: "opay",
    bankName: "OPay",
    label: "OPay",
    short: "OP",
    group: "wallet",
    parser: "dedicated",
    formats: "App · PDF · no balance column",
    steps: [
      "Open OPay → Me → Transaction history",
      "Tap the export icon",
      "Choose the date range",
      "Send to email as PDF",
    ],
    note: "OPay statements carry no running balance, so balance figures show as unavailable for this account. Everything else works normally.",
    noteTone: "info",
  },
  {
    id: "palmpay",
    bankName: "PalmPay",
    label: "PalmPay",
    short: "PP",
    group: "wallet",
    parser: "dedicated",
    formats: "App · PDF",
    steps: [
      "Open PalmPay → Me → Bills & statements",
      "Select account statement",
      "Choose the period → Export",
    ],
  },
  {
    id: "kuda",
    bankName: "Kuda",
    label: "Kuda",
    short: "KU",
    group: "wallet",
    parser: "dedicated",
    formats: "App · PDF · includes savings pockets",
    steps: [
      "Open Kuda → Account → Statement",
      "Select the period",
      "Request statement",
      "Download from email",
    ],
    note: "Kuda includes your Spend account and any savings pockets in one file. Movements between them are not spending and we take them out.",
    noteTone: "info",
  },
  {
    id: "moniepoint",
    bankName: "Moniepoint",
    label: "Moniepoint",
    short: "MP",
    group: "wallet",
    parser: "dedicated",
    formats: "App or web · PDF / CSV",
    steps: [
      "Open Moniepoint → Transactions",
      "Filter to the period you want",
      "Export → choose PDF or CSV",
    ],
    note: "CSV imports faster and more reliably than PDF where a bank offers both.",
    noteTone: "info",
  },
  {
    id: "alat",
    bankName: "ALAT",
    label: "Wema / ALAT",
    short: "AL",
    group: "bank",
    parser: "dedicated",
    formats: "App or internet banking · PDF",
    steps: [
      "Open ALAT → Accounts → Account statement",
      "Select the account and period",
      "Send to registered email",
    ],
  },
  {
    id: "gtbank",
    bankName: "GTBank",
    label: "GTBank",
    short: "GT",
    group: "bank",
    parser: "dedicated",
    formats: "App · PDF · password-protected",
    steps: [
      "Open the GTBank app → Accounts",
      "Select the account → Statement",
      "Choose at least 6 months",
      "Send to email as PDF",
    ],
    passwordHint:
      "GTBank usually uses your date of birth as DDMMYYYY, or the last 6 digits of your account number.",
    noteTone: "warn",
  },
  {
    id: "sterling",
    bankName: "Sterling",
    label: "Sterling",
    short: "ST",
    group: "bank",
    parser: "dedicated",
    formats: "App or internet banking · PDF",
    steps: [
      "Open the Sterling app → Accounts",
      "Statement → select the period",
      "Send to email",
    ],
  },
  {
    id: "alpha-morgan",
    bankName: "Alpha Morgan",
    label: "Alpha Morgan",
    short: "AM",
    group: "bank",
    parser: "dedicated",
    formats: "Internet banking · PDF",
    steps: [
      "Sign in to internet banking",
      "Accounts → statement request",
      "Select the period → generate",
    ],
    note: "Alpha Morgan sometimes prints N/A rows for empty months — that is a real empty statement, not a parse error.",
    noteTone: "info",
  },
  {
    id: "stanbic",
    bankName: "Stanbic IBTC",
    label: "Stanbic IBTC",
    short: "SB",
    group: "bank",
    parser: "dedicated",
    formats: "App or internet banking · PDF",
    steps: [
      "Open the Stanbic app → Accounts",
      "Statements → select period",
      "Download or send to email",
    ],
  },
  // Prototype lists these four; dedicated parsers are not built yet — UI
  // stays honest (limited) and routes through the generic PDF reader.
  {
    id: "uba",
    bankName: "UBA",
    label: "UBA",
    short: "UB",
    group: "bank",
    parser: "limited",
    formats: "Internet banking · PDF",
    steps: [
      "Sign in to UBA internet banking",
      "Accounts → Statement of account",
      "Select the period → generate",
    ],
    note: "Dedicated UBA parser is not shipped yet — we will try a generic reader. Prefer CSV if your bank offers it.",
    noteTone: "warn",
  },
  {
    id: "zenith",
    bankName: "Zenith",
    label: "Zenith",
    short: "ZE",
    group: "bank",
    parser: "limited",
    formats: "App or internet banking · PDF",
    steps: [
      "Open the Zenith app → Account services",
      "Account statement → select period",
      "Send to email",
    ],
    note: "Dedicated Zenith parser is not shipped yet — we will try a generic reader.",
    noteTone: "warn",
  },
  {
    id: "first-bank",
    bankName: "First Bank",
    label: "First Bank",
    short: "FB",
    group: "bank",
    parser: "limited",
    formats: "FirstMobile / internet banking · PDF",
    steps: [
      "Open FirstMobile → Account services",
      "Request e-statement",
      "Choose the period → submit",
    ],
    note: "Dedicated First Bank parser is not shipped yet — we will try a generic reader.",
    noteTone: "warn",
  },
  {
    id: "access",
    bankName: "Access Bank",
    label: "Access",
    short: "AC",
    group: "bank",
    parser: "limited",
    formats: "App or internet banking · PDF",
    steps: [
      "Open the Access app → Accounts",
      "Account statement → choose period",
      "Send to email",
    ],
    note: "Dedicated Access parser is not shipped yet — we will try a generic reader.",
    noteTone: "warn",
  },
];

export const WALLET_SOURCES = BANK_SOURCES.filter((s) => s.group === "wallet");
export const BANK_ONLY_SOURCES = BANK_SOURCES.filter((s) => s.group === "bank");

export function getSourceById(id: string): BankSource | undefined {
  return BANK_SOURCES.find((s) => s.id === id);
}

export function getSourceByBankName(bankName: string): BankSource | undefined {
  return BANK_SOURCES.find((s) => s.bankName.toLowerCase() === bankName.toLowerCase());
}
