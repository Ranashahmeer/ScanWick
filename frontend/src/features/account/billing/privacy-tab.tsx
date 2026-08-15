import { useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/use-auth";
import { Toggle } from "../components/toggle";
import {
  downloadDataExport,
  useCancelDeleteAccount,
  useDeleteAccount,
  useDeleteAllData,
} from "./privacy-api";

interface ConnectedApp {
  id: string;
  name: string;
  detail: string;
}

const initialApps: ConnectedApp[] = [
  { id: "mono", name: "Mono", detail: "Open banking · GTBank, Access" },
  { id: "klaviyo", name: "Klaviyo", detail: "RFM segment sync" },
  { id: "metaads", name: "Meta Ads", detail: "Ad-Kill Switch" },
];

const COOKIE_PREFS_KEY = "scanwick-cookie-preferences";

interface CookiePreferences {
  analytics: boolean;
  preference: boolean;
  marketing: boolean;
}

function loadCookiePreferences(): CookiePreferences {
  try {
    const raw = localStorage.getItem(COOKIE_PREFS_KEY);
    if (raw) return { analytics: true, preference: true, marketing: false, ...JSON.parse(raw) };
  } catch {
    // Ignore malformed/inaccessible storage — fall through to defaults.
  }
  return { analytics: true, preference: true, marketing: false };
}

function CookiePreferencesModal({ onClose }: { onClose: () => void }) {
  const [prefs, setPrefs] = useState<CookiePreferences>(loadCookiePreferences);

  function handleSave() {
    localStorage.setItem(COOKIE_PREFS_KEY, JSON.stringify(prefs));
    toast.success("Cookie preferences saved.");
    onClose();
  }

  return (
    <div className="acct-modal-overlay" onClick={onClose}>
      <div className="acct-modal" onClick={(event) => event.stopPropagation()}>
        <h2>Cookie preferences</h2>
        <div className="acct-modal-row">
          <div>
            <strong>Essential</strong>
            <p className="acct-muted">Required for the site to function. Always on.</p>
          </div>
          <Toggle checked={true} onChange={() => {}} label="Essential cookies (always on)" />
        </div>
        <div className="acct-modal-row">
          <div>
            <strong>Analytics</strong>
            <p className="acct-muted">Helps us understand how the product is used.</p>
          </div>
          <Toggle
            checked={prefs.analytics}
            onChange={(checked) => setPrefs((current) => ({ ...current, analytics: checked }))}
            label="Analytics cookies"
          />
        </div>
        <div className="acct-modal-row">
          <div>
            <strong>Preference</strong>
            <p className="acct-muted">Remembers settings like language and layout.</p>
          </div>
          <Toggle
            checked={prefs.preference}
            onChange={(checked) => setPrefs((current) => ({ ...current, preference: checked }))}
            label="Preference cookies"
          />
        </div>
        <div className="acct-modal-row">
          <div>
            <strong>Marketing</strong>
            <p className="acct-muted">Used to measure and improve marketing campaigns.</p>
          </div>
          <Toggle
            checked={prefs.marketing}
            onChange={(checked) => setPrefs((current) => ({ ...current, marketing: checked }))}
            label="Marketing cookies"
          />
        </div>
        <div className="acct-modal-actions">
          <button type="button" className="acct-btn-outline" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="dqr-action-primary" onClick={handleSave}>
            Save preferences
          </button>
        </div>
      </div>
    </div>
  );
}

export function PrivacyTab() {
  const { user } = useAuth();
  const [apps, setApps] = useState(initialApps);
  const [cookieModalOpen, setCookieModalOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [confirmingDeleteData, setConfirmingDeleteData] = useState(false);
  const [confirmingDeleteAccount, setConfirmingDeleteAccount] = useState(false);

  const deleteAllData = useDeleteAllData();
  const deleteAccount = useDeleteAccount();
  const cancelDeleteAccount = useCancelDeleteAccount();

  const disconnect = (id: string) => {
    setApps((current) => current.filter((app) => app.id !== id));
  };

  async function handleExport() {
    setExporting(true);
    try {
      await downloadDataExport();
    } catch {
      toast.error("Could not export your data. Please try again.");
    } finally {
      setExporting(false);
    }
  }

  function handleDeleteAllData() {
    if (!confirmingDeleteData) {
      setConfirmingDeleteData(true);
      return;
    }
    deleteAllData.mutate(undefined, {
      onSuccess: () => {
        toast.success("Your uploaded data and analysis outputs have been deleted.");
        setConfirmingDeleteData(false);
      },
      onError: (error) => {
        toast.error(error instanceof Error ? error.message : "Could not delete your data.");
        setConfirmingDeleteData(false);
      },
    });
  }

  function handleDeleteAccount() {
    if (!confirmingDeleteAccount) {
      setConfirmingDeleteAccount(true);
      return;
    }
    deleteAccount.mutate(undefined, {
      onSuccess: () => {
        toast.success("Your account is scheduled for deletion.");
        setConfirmingDeleteAccount(false);
      },
      onError: (error) => {
        toast.error(error instanceof Error ? error.message : "Could not schedule account deletion.");
        setConfirmingDeleteAccount(false);
      },
    });
  }

  function handleCancelDeleteAccount() {
    cancelDeleteAccount.mutate(undefined, {
      onSuccess: () => toast.success("Account deletion has been cancelled."),
      onError: (error) => toast.error(error instanceof Error ? error.message : "Could not cancel deletion."),
    });
  }

  return (
    <>
      <div className="acct-card">
        <h2>Data retention</h2>
        <p className="acct-card-hint">
          Your uploaded data and analysis outputs are retained while your plan is active and for
          up to 90 days after expiry. Account/profile details are kept up to 12 months after
          closure, then deleted. Processed in line with the NDPA 2023, GAID 2025, and GDPR where
          applicable.
        </p>
      </div>

      <div className="acct-card">
        <h2>Your data</h2>
        <div className="acct-privacy-row">
          <div>
            <strong>Download my data</strong>
            <p>Export your uploads and generated reports (machine-readable)</p>
          </div>
          <button type="button" className="acct-btn-outline" onClick={handleExport} disabled={exporting}>
            {exporting ? "Preparing…" : "Request export"}
          </button>
        </div>
        <div className="acct-privacy-row">
          <div>
            <strong>Delete all data</strong>
            <p>Permanently removes uploaded datasets and analysis. This can't be undone.</p>
          </div>
          <button
            type="button"
            className="acct-btn-danger"
            onClick={handleDeleteAllData}
            disabled={deleteAllData.isPending}
          >
            {deleteAllData.isPending
              ? "Deleting…"
              : confirmingDeleteData
                ? "Are you sure? Click to confirm"
                : "Delete all data"}
          </button>
        </div>
        <div className="acct-privacy-row">
          <div>
            <strong>Delete account</strong>
            {user?.deletion_requested_at ? (
              <p>
                Deletion pending since {new Date(user.deletion_requested_at).toLocaleDateString()}.
              </p>
            ) : (
              <p>Closes your account with a 30-day grace period before permanent deletion.</p>
            )}
          </div>
          {user?.deletion_requested_at ? (
            <button
              type="button"
              className="acct-btn-outline"
              onClick={handleCancelDeleteAccount}
              disabled={cancelDeleteAccount.isPending}
            >
              {cancelDeleteAccount.isPending ? "Cancelling…" : "Cancel deletion"}
            </button>
          ) : (
            <button
              type="button"
              className="acct-btn-outline"
              onClick={handleDeleteAccount}
              disabled={deleteAccount.isPending}
            >
              {deleteAccount.isPending
                ? "Scheduling…"
                : confirmingDeleteAccount
                  ? "Are you sure? Click to confirm"
                  : "Delete account"}
            </button>
          )}
        </div>
      </div>

      <div className="acct-card">
        <h2>Connected apps</h2>
        <div className="acct-app-list">
          {apps.map((app) => (
            <div className="acct-app-row" key={app.id}>
              <div>
                <strong>{app.name}</strong>
                <span>{app.detail}</span>
              </div>
              <button type="button" className="acct-btn-outline" onClick={() => disconnect(app.id)}>
                Disconnect
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="acct-cookie-note">
        <span>
          Essential cookies are always on. You can manage Analytics, Preference, and Marketing
          cookies here.
        </span>
        <button type="button" className="acct-link" onClick={() => setCookieModalOpen(true)}>
          Manage
        </button>
      </div>

      {cookieModalOpen ? <CookiePreferencesModal onClose={() => setCookieModalOpen(false)} /> : null}
    </>
  );
}
