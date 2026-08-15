// Informational-only local-currency price display (landing page pricing).
// Never used for the actual charge — that's always computed server-side in
// NGN, at a separately-synced live rate (see backend/app/services/fx_rates.py).
// This is purely "show the visitor a number that means something to them."
//
// Both APIs are free, keyless, and CORS-open (verified directly while
// building this) — no account/config needed:
//   - https://ipwho.is/               — IP geolocation -> country code
//   - https://open.er-api.com/v6/...  — live USD exchange rates for every currency

const GEO_API_URL = "https://ipwho.is/";
const RATES_API_URL = "https://open.er-api.com/v6/latest/USD";

// ISO 3166 country code -> ISO 4217 currency code. Not exhaustive — covers
// the markets this app is actually built for (Nigeria/Ghana/Kenya/South
// Africa, per the existing Mono open-banking integration) plus the other
// major English-speaking/global markets. Anything unmapped falls back to
// USD display, which is always a safe, correct default.
const COUNTRY_TO_CURRENCY: Record<string, string> = {
  NG: "NGN",
  GH: "GHS",
  KE: "KES",
  ZA: "ZAR",
  US: "USD",
  GB: "GBP",
  CA: "CAD",
  AU: "AUD",
  IE: "EUR",
  DE: "EUR",
  FR: "EUR",
  ES: "EUR",
  IT: "EUR",
  NL: "EUR",
  IN: "INR",
  PK: "PKR",
  AE: "AED",
  SA: "SAR",
  EG: "EGP",
  BR: "BRL",
  MX: "MXN",
  JP: "JPY",
  CN: "CNY",
  SG: "SGD",
};

export interface LocalPricing {
  currency: string;
  // 1 USD = `rate` units of `currency`. Always 1 when currency is "USD".
  rate: number;
}

interface GeoResponse {
  success: boolean;
  country_code?: string;
}

interface RatesResponse {
  result: string;
  rates?: Record<string, number>;
}

// Resolves once per page load — every pricing card shares one detection
// instead of each card independently hitting both APIs.
let cachedDetection: Promise<LocalPricing | null> | null = null;

async function detectLocalCurrencyUncached(): Promise<LocalPricing | null> {
  try {
    const geoResponse = await fetch(GEO_API_URL);
    const geo: GeoResponse = await geoResponse.json();
    if (!geo.success || !geo.country_code) return null;

    const currency = COUNTRY_TO_CURRENCY[geo.country_code];
    if (!currency || currency === "USD") return { currency: "USD", rate: 1 };

    const ratesResponse = await fetch(RATES_API_URL);
    const ratesData: RatesResponse = await ratesResponse.json();
    const rate = ratesData.result === "success" ? ratesData.rates?.[currency] : undefined;
    if (!rate) return null;

    return { currency, rate };
  } catch {
    // Any failure (network, geolocation blocked, unexpected response
    // shape) just means "show USD instead" — never breaks the pricing page.
    return null;
  }
}

export function detectLocalCurrency(): Promise<LocalPricing | null> {
  if (!cachedDetection) {
    cachedDetection = detectLocalCurrencyUncached();
  }
  return cachedDetection;
}

// `pricing: null` (detection still pending, or failed) formats as USD.
export function formatLocalPrice(usdAmount: number, pricing: LocalPricing | null): string {
  if (usdAmount === 0) {
    // Free is free in every currency — no conversion needed, and it avoids
    // an odd "₦0" vs "$0" mismatch flash while detection is still pending.
    return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(
      0
    );
  }

  if (!pricing || pricing.currency === "USD") {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(usdAmount);
  }

  const converted = usdAmount * pricing.rate;
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: pricing.currency,
      maximumFractionDigits: 0,
    }).format(converted);
  } catch {
    // Intl doesn't recognize the currency code for some reason — fall back
    // to a plain "CODE amount" string rather than throwing.
    return `${pricing.currency} ${converted.toFixed(0)}`;
  }
}
