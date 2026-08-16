/**
 * Formatting rules from the prototype's design system (screen 00).
 *
 * These live apart from the components so that a fast-refresh boundary is
 * not crossed by mixing value exports with component exports — and because
 * the money and date rules are product requirements that get referenced
 * outside rendering too.
 */

/**
 * Money. Naira sign, thousands separators, and a true minus sign on a
 * negative rather than a hyphen. Returns null when the value is not a
 * number, so a caller renders the unavailable chip instead of a zero.
 */
export function money(
  value: number | string | null | undefined,
  { currency = "₦", decimals = 0 }: { currency?: string; decimals?: number } = {},
): string | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return null;
  const body = Math.abs(n).toLocaleString("en-NG", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return `${n < 0 ? "−" : ""}${currency}${body}`;
}

/** Date as shown to the user: 15 Jul 2026. */
export function fmtDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

/** Short form for axis labels and dense rows: 15 Jul. */
export function fmtDateShort(value: string | null | undefined): string | null {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

/** Month label from a YYYY-MM or ISO date: Jul 2026. */
export function fmtMonth(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value.length === 7 ? `${value}-01` : value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-GB", { month: "short", year: "numeric" });
}

/** Two-letter source mark for the <Src> chip: "GTBank" -> "GT". */
export function srcMark(name: string | null | undefined): string {
  if (!name) return "··";
  const cleaned = name.replace(/[^A-Za-z ]/g, "").trim();
  if (!cleaned) return "··";
  const words = cleaned.split(/\s+/);
  if (words.length > 1) return (words[0][0] + words[1][0]).toUpperCase();
  return cleaned.slice(0, 2).toUpperCase();
}
