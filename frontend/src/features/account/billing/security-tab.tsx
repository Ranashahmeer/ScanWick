import { useState } from "react";
import { toast } from "sonner";
import { Eye, EyeOff } from "lucide-react";
import {
  useChangePassword,
  useDisable2fa,
  useEnable2fa,
  useLoginHistory,
  useRevokeSession,
  useSessions,
  useSetup2fa,
} from "./security-api";
import { useAuth } from "@/hooks/use-auth";
import { authClient } from "@/lib/api-client";
import { authStore, type AuthUser } from "@/lib/auth-store";

function PasswordField({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="acct-password-input">
      <input
        type={visible ? "text" : "password"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <button
        type="button"
        className="acct-password-toggle"
        onClick={() => setVisible((current) => !current)}
        aria-label={visible ? "Hide password" : "Show password"}
      >
        {visible ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
    </div>
  );
}

function formatWhen(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function PasswordCard() {
  const changePassword = useChangePassword();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  function handleSubmit() {
    if (!currentPassword || !newPassword) {
      toast.error("Enter your current and new password.");
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error("New password and confirmation don't match.");
      return;
    }
    changePassword.mutate(
      { current_password: currentPassword, new_password: newPassword },
      {
        onSuccess: () => {
          toast.success("Password updated. Please log in again.");
          setCurrentPassword("");
          setNewPassword("");
          setConfirmPassword("");
        },
        onError: (error) => toast.error(error instanceof Error ? error.message : "Could not update your password."),
      }
    );
  }

  return (
    <div className="acct-card">
      <h2>Password</h2>
      <div className="acct-form-grid">
        <label className="acct-field acct-field-wide">
          <span>Current password</span>
          <PasswordField value={currentPassword} onChange={setCurrentPassword} />
        </label>
        <label className="acct-field">
          <span>New password</span>
          <PasswordField value={newPassword} onChange={setNewPassword} />
        </label>
        <label className="acct-field">
          <span>Confirm new</span>
          <PasswordField value={confirmPassword} onChange={setConfirmPassword} />
        </label>
      </div>
      <button
        type="button"
        className="dqr-action-primary acct-mt"
        onClick={handleSubmit}
        disabled={changePassword.isPending}
      >
        {changePassword.isPending ? "Updating…" : "Update password"}
      </button>
    </div>
  );
}

function TwoFactorCard() {
  const { user } = useAuth();
  const setup2fa = useSetup2fa();
  const enable2fa = useEnable2fa();
  const disable2fa = useDisable2fa();
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [confirmingDisable, setConfirmingDisable] = useState(false);

  function refreshUser(nextUser: AuthUser) {
    authStore.setAuthenticated(nextUser);
  }

  async function refetchMe() {
    const { data } = await authClient.get<AuthUser>("/me");
    refreshUser(data);
  }

  function handleStartSetup() {
    setup2fa.mutate(undefined, {
      onSuccess: (result) => setQrCode(result.qr_code_base64),
      onError: (error) => toast.error(error instanceof Error ? error.message : "Could not start 2FA setup."),
    });
  }

  function handleEnable() {
    if (code.length !== 6) {
      toast.error("Enter the 6-digit code from your authenticator app.");
      return;
    }
    enable2fa.mutate(code, {
      onSuccess: async () => {
        toast.success("Two-factor authentication is now enabled.");
        setQrCode(null);
        setCode("");
        await refetchMe();
      },
      onError: (error) => toast.error(error instanceof Error ? error.message : "Invalid code."),
    });
  }

  function handleDisable() {
    if (!confirmingDisable) {
      setConfirmingDisable(true);
      return;
    }
    if (!disablePassword) {
      toast.error("Enter your current password to disable 2FA.");
      return;
    }
    disable2fa.mutate(disablePassword, {
      onSuccess: async () => {
        toast.success("Two-factor authentication has been disabled.");
        setDisablePassword("");
        setConfirmingDisable(false);
        await refetchMe();
      },
      onError: (error) => toast.error(error instanceof Error ? error.message : "Could not disable 2FA."),
    });
  }

  if (user?.totp_enabled) {
    return (
      <div className="acct-card">
        <h2>Two-factor authentication</h2>
        <p className="acct-card-hint">Two-factor authentication is enabled on your account.</p>
        {confirmingDisable ? (
          <div className="acct-2fa-row">
            <label className="acct-field">
              <span>Current password</span>
              <PasswordField value={disablePassword} onChange={setDisablePassword} />
            </label>
            <button type="button" className="acct-btn-danger" onClick={handleDisable} disabled={disable2fa.isPending}>
              {disable2fa.isPending ? "Disabling…" : "Confirm disable"}
            </button>
            <button type="button" className="acct-btn-outline" onClick={() => setConfirmingDisable(false)}>
              Cancel
            </button>
          </div>
        ) : (
          <button type="button" className="acct-btn-outline acct-mt" onClick={handleDisable}>
            Disable 2FA
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="acct-card">
      <h2>Two-factor authentication</h2>
      <p className="acct-card-hint">Scan with an authenticator app, then enter the 6-digit code.</p>
      <div className="acct-2fa-row">
        {qrCode ? (
          <img className="acct-qr-image" src={qrCode} alt="Two-factor authentication QR code" />
        ) : (
          <div className="acct-qr-placeholder" aria-hidden="true" />
        )}
        {qrCode ? (
          <>
            <input
              type="text"
              className="acct-2fa-input"
              placeholder="123 456"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              maxLength={6}
            />
            <button type="button" className="dqr-action-primary" onClick={handleEnable} disabled={enable2fa.isPending}>
              {enable2fa.isPending ? "Verifying…" : "Enable 2FA"}
            </button>
          </>
        ) : (
          <button
            type="button"
            className="dqr-action-primary"
            onClick={handleStartSetup}
            disabled={setup2fa.isPending}
          >
            {setup2fa.isPending ? "Loading…" : "Set up 2FA"}
          </button>
        )}
      </div>
      <p className="acct-muted acct-mt-sm">Recommended for account owners with billing access.</p>
    </div>
  );
}

function SessionsCard() {
  const { data: sessions, isLoading } = useSessions();
  const revokeSession = useRevokeSession();

  return (
    <div className="acct-card">
      <h2>Active sessions</h2>
      <div className="acct-table acct-table-3col">
        <div className="acct-table-head">
          <span>Device</span>
          <span>IP address</span>
          <span>Last seen</span>
        </div>
        {isLoading ? <div className="acct-table-row">Loading…</div> : null}
        {!isLoading && sessions?.length === 0 ? <div className="acct-table-row">No active sessions.</div> : null}
        {sessions?.map((session) => (
          <div className="acct-table-row" key={session.id}>
            <span>
              {session.device ?? "Unknown device"}
              {session.is_current ? <span className="acct-tag-current">This device</span> : null}
            </span>
            <span className="acct-muted">{session.ip_address ?? "—"}</span>
            <span className="acct-session-last">
              <span className="acct-muted">{formatWhen(session.last_used_at ?? session.created_at)}</span>
              {!session.is_current ? (
                <button
                  type="button"
                  className="acct-btn-outline"
                  onClick={() => revokeSession.mutate(session.id)}
                  disabled={revokeSession.isPending}
                >
                  Revoke
                </button>
              ) : null}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LoginHistoryCard() {
  const { data: events, isLoading } = useLoginHistory();

  return (
    <div className="acct-card">
      <h2>Login history</h2>
      <div className="acct-table acct-table-3col">
        <div className="acct-table-head">
          <span>When</span>
          <span>Device</span>
          <span>Result</span>
        </div>
        {isLoading ? <div className="acct-table-row">Loading…</div> : null}
        {!isLoading && events?.length === 0 ? <div className="acct-table-row">No login attempts yet.</div> : null}
        {events?.map((event) => (
          <div className="acct-table-row" key={event.id}>
            <span>{formatWhen(event.when)}</span>
            <span className="acct-muted">{event.device ?? "Unknown"}</span>
            <span className={event.result === "success" ? "acct-status-success" : "acct-status-danger"}>
              {event.result === "success" ? "Success" : "Blocked"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SecurityTab() {
  return (
    <>
      <PasswordCard />
      <TwoFactorCard />
      <SessionsCard />
      <LoginHistoryCard />
    </>
  );
}
