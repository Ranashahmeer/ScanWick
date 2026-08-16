/**
 * Account selection shared by every Surface 1 screen.
 *
 * The analysis endpoints are per-account, so each screen needs the same
 * three things: which merchant, which account is selected, and the full
 * account list (which the coverage statement renders on every screen).
 * The selection is held in sessionStorage so moving between screens does
 * not silently reset it.
 */

import { useCallback, useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useBankAccounts, type BankAccount } from "@/features/dashboard/bank-api";

const STORAGE_KEY = "scanwick-selected-account";

export interface SelectedAccount {
  merchantId: string | null;
  accountId: string | null;
  accounts: BankAccount[];
  account: BankAccount | null;
  isLoading: boolean;
  isError: boolean;
  select: (accountId: string) => void;
}

export function useSelectedAccount(): SelectedAccount {
  const { user } = useAuth();
  const merchantId = user?.merchant_id ?? null;
  const accounts = useBankAccounts(merchantId ?? "");
  const [accountId, setAccountId] = useState<string | null>(() => sessionStorage.getItem(STORAGE_KEY));

  const list = accounts.data ?? [];

  const select = useCallback((next: string) => {
    setAccountId(next);
    sessionStorage.setItem(STORAGE_KEY, next);
  }, []);

  // Derived rather than synced through an effect: a stored id that no longer
  // exists (account removed, different login) simply falls back to the first
  // account instead of leaving every screen querying a dead one.
  const resolved = accountId && list.some((a) => a.id === accountId) ? accountId : (list[0]?.id ?? null);

  return {
    merchantId,
    accountId: resolved,
    accounts: list,
    account: list.find((a) => a.id === resolved) ?? null,
    isLoading: accounts.isLoading,
    isError: accounts.isError,
    select,
  };
}

/**
 * Coverage rows for the <Coverage> component, built from the real account
 * list. Tier is B for every account today — every account in the system
 * arrives as an uploaded file; Tier A requires the live-connection path,
 * which no account has taken yet.
 */
export function coverageRows(accounts: BankAccount[]) {
  return accounts.map((a) => ({
    label: a.bank_name ?? "Account",
    source: "Uploaded file",
    period:
      a.statement_period_start && a.statement_period_end
        ? `${a.statement_period_start} – ${a.statement_period_end}`
        : "Period not stated",
    tier: "B" as const,
    audit: "See account audit",
  }));
}

/**
 * Which accounts report a running balance. OPay-style sources carry no
 * balance column, so every balance metric for them is unavailable rather
 * than zero — the rule the whole product rests on.
 */
export function balanceIsAvailable(account: BankAccount | null): boolean {
  return account?.closing_balance !== null && account?.closing_balance !== undefined;
}

export const NO_BALANCE_REASON =
  "This statement carries no running balance column, so any balance figure would be invented rather than measured.";
