/**
 * Account — prototype screens 57 (user account), 66 (billing & payments),
 * 67 (security & activity), 68 (delete account) and 55 (plans).
 *
 * Two rules from the specification govern the billing screens and are not
 * negotiable in the interface:
 *   - Downgrade never deletes. A failed renewal moves the account to Free
 *     at the end of the paid period; it does not remove data.
 *   - Reading is never gated. An analysis already produced stays readable
 *     whatever happens to the subscription. Never a paywall on a read path.
 *
 * And on screen 68: never let a deletion silently break an obligation the
 * user made to a third party. Say what it will do, then let them decide.
 */

import { useEffect, useState } from "react";
import { getRouteApi, useNavigate } from "@tanstack/react-router";
import { AppShell, Screen } from "@/features/shell/app-shell";
import {
  Btn,
  Card,
  Field,
  Hint,
  Inp,
  LoadFailed,
  Money,
  Na,
  Pill,
  Row,
  ScreenHead,
  SkeletonRows,
  Tbl,
} from "@/components/sw";
import { fmtDate } from "@/components/sw/format";
import { useAuth } from "@/hooks/use-auth";
import { ContextualMarkers } from "./contextual-markers";
import { WorkspaceSettings } from "./workspace-settings";
import { useUpdateProfile, useUploadAvatar } from "./billing/profile-api";
import {
  useChangePassword,
  useDisable2fa,
  useEnable2fa,
  useLoginHistory,
  useRevokeSession,
  useSessions,
  useSetup2fa,
} from "./billing/security-api";
import {
  useBillingHistory,
  useCancelSubscription,
  useStartCheckout,
  useSubscription,
  useVerifyPayment,
  type PaidTier,
} from "./billing/payments-api";
import {
  downloadDataExport,
  useCancelDeleteAccount,
  useDeleteAccount,
} from "./billing/privacy-api";
import { useNotificationPreferences, useSaveNotificationPreferences } from "./billing/notifications-api";

export type AccountTab = "profile" | "security" | "billing" | "plans" | "delete" | "markers" | "settings";

const accountRoute = getRouteApi("/_app/account/");

const HEADINGS: Record<AccountTab, { title: string; meta: string }> = {
  profile: { title: "User account", meta: "Profile, plan, notifications and your data" },
  security: { title: "Security & activity", meta: "Two-factor, sessions and sign-in history" },
  billing: { title: "Billing & payments", meta: "Checkout, subscription, history and cancellation" },
  plans: { title: "Plans", meta: "Priced by assessment, not by seat" },
  delete: { title: "Delete account", meta: "What deletion affects, and the 30-day recovery window" },
  markers: { title: "Contextual markers", meta: "Tag unusual periods so they are read in context" },
  settings: { title: "Workspace settings", meta: "Configuration for this workspace" },
};

const TABS: { id: AccountTab; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "security", label: "Security" },
  { id: "billing", label: "Billing" },
  { id: "plans", label: "Plans" },
  { id: "markers", label: "Markers" },
  { id: "settings", label: "Settings" },
  { id: "delete", label: "Delete account" },
];

/* --------------------------------------------------------- screen 57 */

function ProfileTab() {
  const { user } = useAuth();
  const updateProfile = useUpdateProfile();
  const uploadAvatar = useUploadAvatar();
  const subscription = useSubscription();
  const preferences = useNotificationPreferences();
  const savePreferences = useSaveNotificationPreferences();
  const navigate = useNavigate();

  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [company, setCompany] = useState(user?.company ?? "");
  const [saved, setSaved] = useState(false);

  const initials =
    [user?.first_name?.[0], user?.last_name?.[0]].filter(Boolean).join("").toUpperCase() ||
    user?.email?.[0]?.toUpperCase() ||
    "·";

  return (
    <>
      <Row cols={3} style={{ marginBottom: 16 }}>
        <Card title="Profile">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              setSaved(false);
              updateProfile.mutate(
                { first_name: firstName, last_name: lastName, company },
                { onSuccess: () => setSaved(true) },
              );
            }}
          >
            <Field label="First name" id="first-name">
              <Inp id="first-name" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </Field>
            <Field label="Last name" id="last-name">
              <Inp id="last-name" value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </Field>
            <Field label="Email" id="email" hint="Changing this requires re-verification">
              <Inp id="email" value={user?.email ?? ""} readOnly disabled />
            </Field>
            <Field label="Business name" id="company" optional>
              <Inp id="company" value={company} onChange={(e) => setCompany(e.target.value)} />
            </Field>

            <Btn sm type="submit" disabled={updateProfile.isPending}>
              {updateProfile.isPending ? "Saving…" : "Save changes"}
            </Btn>
            {saved ? <Hint style={{ color: "var(--g600)" }}>Saved.</Hint> : null}
            {updateProfile.isError ? (
              <div className="errmsg" role="alert">
                {(updateProfile.error as Error).message}
              </div>
            ) : null}
          </form>

          <h3 style={{ marginTop: 20 }}>Profile photo</h3>
          <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 10 }}>
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt=""
                style={{ width: 52, height: 52, borderRadius: "50%", objectFit: "cover" }}
              />
            ) : (
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: "50%",
                  background: "var(--g700)",
                  color: "#fff",
                  display: "grid",
                  placeItems: "center",
                  fontWeight: 700,
                  fontSize: 18,
                }}
              >
                {initials}
              </div>
            )}
            <div>
              <label className="btn gho sm" style={{ cursor: "pointer" }}>
                {uploadAvatar.isPending ? "Uploading…" : "Upload"}
                <input
                  type="file"
                  accept="image/png,image/jpeg"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    e.target.value = "";
                    if (file) uploadAvatar.mutate(file);
                  }}
                />
              </label>
              <Hint style={{ marginTop: 5 }}>JPG or PNG, up to 2MB</Hint>
            </div>
          </div>
        </Card>

        <Card title="Security" sub="Managed in full on the security screen">
          <table>
            <tbody>
              <tr>
                <td>Two-factor</td>
                <td className="num">
                  <Pill tone={user?.totp_enabled ? "a" : "c"}>{user?.totp_enabled ? "On" : "Off"}</Pill>
                </td>
                <td>
                  <Btn tone="gho" sm onClick={() => navigate({ to: "/account", search: { tab: "security" } })}>
                    Manage
                  </Btn>
                </td>
              </tr>
              <tr>
                <td>Sign-in method</td>
                <td className="num">{user?.google_id ? "Google" : "Email and password"}</td>
                <td />
              </tr>
              <tr>
                <td>Email verified</td>
                <td className="num">
                  <Pill tone={user?.is_verified ? "a" : "c"}>{user?.is_verified ? "Yes" : "Pending"}</Pill>
                </td>
                <td />
              </tr>
            </tbody>
          </table>
        </Card>

        <Card title="Your plan">
          {subscription.isLoading ? (
            <SkeletonRows rows={4} />
          ) : (
            <>
              <div
                style={{
                  padding: 13,
                  border: "1px solid var(--g300)",
                  borderRadius: 8,
                  background: "var(--g50)",
                  marginBottom: 13,
                }}
              >
                <b style={{ fontSize: 13, textTransform: "capitalize" }}>{subscription.data?.tier ?? "Free"}</b>
                <Hint>
                  {subscription.data?.current_period_end
                    ? `Renews ${fmtDate(subscription.data.current_period_end)}`
                    : "No renewal date"}
                </Hint>
              </div>
              <table>
                <tbody>
                  <tr>
                    <td>Status</td>
                    <td className="num">
                      <Pill tone={subscription.data?.status === "active" ? "a" : "c"}>
                        {subscription.data?.status ?? "free"}
                      </Pill>
                    </td>
                  </tr>
                  <tr>
                    <td>Cancels at period end</td>
                    <td className="num">{subscription.data?.cancel_at_period_end ? "Yes" : "No"}</td>
                  </tr>
                </tbody>
              </table>
              <Btn tone="sec" sm block style={{ marginTop: 12 }} onClick={() => navigate({ to: "/account", search: { tab: "billing" } })}>
                Manage billing
              </Btn>
            </>
          )}
        </Card>
      </Row>

      <Row cols={2} style={{ marginBottom: 16 }}>
        <Card title="Notifications" sub="Per user, not per workspace">
          {preferences.isLoading ? (
            <SkeletonRows rows={5} />
          ) : preferences.isError ? (
            <LoadFailed onRetry={() => preferences.refetch()} />
          ) : (
            <>
              <Tbl>
                <table className="stack">
                  <thead>
                    <tr>
                      <th>Event</th>
                      <th>Email</th>
                      <th>In-app</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(preferences.data ?? []).map((pref) => (
                      <tr key={pref.event_key}>
                        <td data-l="Event">{pref.label}</td>
                        <td data-l="Email">
                          <input
                            type="checkbox"
                            checked={pref.email}
                            aria-label={`${pref.label} by email`}
                            onChange={(e) =>
                              savePreferences.mutate(
                                (preferences.data ?? []).map((p) =>
                                  p.event_key === pref.event_key ? { ...p, email: e.target.checked } : p,
                                ),
                              )
                            }
                          />
                        </td>
                        <td data-l="In-app">
                          <input
                            type="checkbox"
                            checked={pref.in_app}
                            aria-label={`${pref.label} in app`}
                            onChange={(e) =>
                              savePreferences.mutate(
                                (preferences.data ?? []).map((p) =>
                                  p.event_key === pref.event_key ? { ...p, in_app: e.target.checked } : p,
                                ),
                              )
                            }
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Tbl>
              {savePreferences.isError ? (
                <div className="errmsg" role="alert">
                  {(savePreferences.error as Error).message}
                </div>
              ) : null}
            </>
          )}
        </Card>

        <Card title="Your data" sub="Data subject rights under the NDPA 2023, served here rather than through an email queue">
          <table>
            <tbody>
              <tr>
                <td>Raw statement files deleted after</td>
                <td className="num">90 days</td>
              </tr>
              <tr>
                <td>Analysis kept for</td>
                <td className="num">12 months</td>
              </tr>
              <tr>
                <td>Shared with</td>
                <td className="num">Only recipients you name</td>
              </tr>
            </tbody>
          </table>
          <div style={{ display: "flex", flexDirection: "column", gap: 7, marginTop: 13 }}>
            <Btn tone="gho" sm style={{ justifyContent: "flex-start" }} onClick={() => void downloadDataExport()}>
              Download everything we hold about you
            </Btn>
            <Btn
              tone="gho"
              sm
              style={{ justifyContent: "flex-start" }}
              onClick={() => navigate({ to: "/consent" })}
            >
              Manage what you have consented to
            </Btn>
            <Btn
              tone="dgr"
              sm
              style={{ justifyContent: "flex-start" }}
              onClick={() => navigate({ to: "/account", search: { tab: "delete" } })}
            >
              Delete my account and all data
            </Btn>
          </div>
        </Card>
      </Row>
    </>
  );
}

/* --------------------------------------------------------- screen 67 */

function SecurityTab() {
  const { user } = useAuth();
  const sessions = useSessions();
  const history = useLoginHistory();
  const revokeSession = useRevokeSession();
  const changePassword = useChangePassword();
  const setup2fa = useSetup2fa();
  const enable2fa = useEnable2fa();
  const disable2fa = useDisable2fa();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");

  const failures = (history.data ?? []).filter((event) => event.result === "blocked");

  return (
    <>
      <Row cols={3} style={{ marginBottom: 16 }}>
        <Card title="Two-factor authentication" sub={user?.totp_enabled ? "Currently on" : "Currently off"}>
          {!user?.totp_enabled ? (
            <>
              <div
                style={{
                  padding: 13,
                  background: "var(--warnbg)",
                  borderRadius: 8,
                  fontSize: 12.5,
                  color: "#5C4A16",
                  marginBottom: 13,
                }}
              >
                Your account holds analysis of your bank statements. Two-factor makes it much harder for someone with
                your password to reach it.
              </div>

              {setup2fa.data ? (
                <>
                  <img
                    src={`data:image/png;base64,${setup2fa.data.qr_code_base64}`}
                    alt="Two-factor setup QR code"
                    style={{ width: 160, height: 160, display: "block", margin: "0 auto 10px" }}
                  />
                  <Hint style={{ textAlign: "center", wordBreak: "break-all" }}>
                    Or enter this secret manually: <span className="mono">{setup2fa.data.secret}</span>
                  </Hint>
                  <Field label="Code from your authenticator app" id="totp-enable">
                    <Inp
                      id="totp-enable"
                      inputMode="numeric"
                      maxLength={6}
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                      style={{ fontFamily: "var(--mono)", letterSpacing: "4px", textAlign: "center" }}
                    />
                  </Field>
                  <Btn
                    sm
                    block
                    disabled={enable2fa.isPending || totpCode.length !== 6}
                    onClick={() => enable2fa.mutate(totpCode)}
                  >
                    {enable2fa.isPending ? "Turning on…" : "Turn on two-factor"}
                  </Btn>
                  {enable2fa.isError ? (
                    <div className="errmsg" role="alert">
                      {(enable2fa.error as Error).message}
                    </div>
                  ) : null}
                </>
              ) : (
                <Btn sm block disabled={setup2fa.isPending} onClick={() => setup2fa.mutate()}>
                  {setup2fa.isPending ? "Preparing…" : "Set up two-factor"}
                </Btn>
              )}
              <Hint style={{ marginTop: 10 }}>An authenticator app is stronger than SMS and works offline.</Hint>
            </>
          ) : (
            <>
              <Pill tone="a">On</Pill>
              <Field label="Confirm your password to turn it off" id="disable-2fa" hint="We ask for the password so a stolen session cannot weaken your account.">
                <Inp
                  id="disable-2fa"
                  type="password"
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                />
              </Field>
              <Btn
                tone="dgr"
                sm
                block
                disabled={disable2fa.isPending || !disablePassword}
                onClick={() => disable2fa.mutate(disablePassword)}
              >
                {disable2fa.isPending ? "Turning off…" : "Turn off two-factor"}
              </Btn>
              {disable2fa.isError ? (
                <div className="errmsg" role="alert">
                  {(disable2fa.error as Error).message}
                </div>
              ) : null}
            </>
          )}
        </Card>

        <Card title="Active sessions" sub="Everywhere you are signed in">
          {sessions.isLoading ? (
            <SkeletonRows rows={3} />
          ) : sessions.isError ? (
            <LoadFailed onRetry={() => sessions.refetch()} />
          ) : (
            <table>
              <tbody>
                {(sessions.data ?? []).map((session) => (
                  <tr key={session.id}>
                    <td>
                      <b>{session.device ?? "Unknown device"}</b>
                      <Hint>
                        {session.ip_address ?? "IP not recorded"} ·{" "}
                        {session.is_current ? "this device" : `last active ${fmtDate(session.last_used_at) ?? "—"}`}
                      </Hint>
                    </td>
                    <td className="num">
                      {session.is_current ? (
                        <Pill tone="a">Current</Pill>
                      ) : (
                        <Btn tone="gho" sm onClick={() => revokeSession.mutate(session.id)}>
                          End
                        </Btn>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card title="Change password">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              changePassword.mutate(
                { current_password: currentPassword, new_password: newPassword },
                {
                  onSuccess: () => {
                    setCurrentPassword("");
                    setNewPassword("");
                  },
                },
              );
            }}
          >
            <Field label="Current password" id="cur-pass">
              <Inp
                id="cur-pass"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </Field>
            <Field label="New password" id="new-pass" hint="At least 10 characters.">
              <Inp
                id="new-pass"
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </Field>
            <Btn sm block type="submit" disabled={changePassword.isPending || !currentPassword || !newPassword}>
              {changePassword.isPending ? "Updating…" : "Update password"}
            </Btn>
            {changePassword.isError ? (
              <div className="errmsg" role="alert">
                {(changePassword.error as Error).message}
              </div>
            ) : null}
            {changePassword.isSuccess ? <Hint style={{ color: "var(--g600)" }}>Password updated.</Hint> : null}
          </form>
        </Card>
      </Row>

      <Card title="Sign-in history" sub="Every attempt, successful or not — append-only">
        {history.isLoading ? (
          <SkeletonRows rows={5} />
        ) : history.isError ? (
          <LoadFailed onRetry={() => history.refetch()} />
        ) : (
          <>
            <Tbl>
              <table className="stack">
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Device</th>
                    <th>IP</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {(history.data ?? []).map((event) => (
                    <tr key={event.id} style={event.result === "blocked" ? { background: "var(--stopbg)" } : undefined}>
                      <td className="mono" data-l="When">
                        {fmtDate(event.when) ?? event.when}
                      </td>
                      <td data-l="Device">{event.device ?? <Na reason="No device was recorded for this attempt." />}</td>
                      <td className="mono" data-l="IP">
                        {event.ip_address ?? <Na reason="No IP was recorded for this attempt." />}
                      </td>
                      <td data-l="Result">
                        <Pill tone={event.result === "success" ? "a" : "d"}>
                          {event.result === "success" ? "Success" : `Failed${event.reason ? ` — ${event.reason}` : ""}`}
                        </Pill>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Tbl>

            {failures.length > 0 ? (
              <div
                style={{
                  marginTop: 14,
                  padding: 12,
                  background: "var(--warnbg)",
                  borderRadius: 8,
                  fontSize: 12.5,
                  color: "#5C4A16",
                }}
              >
                <b>
                  {failures.length} failed attempt{failures.length === 1 ? "" : "s"} on this account.
                </b>{" "}
                If that was not you, change your password and turn on two-factor.
              </div>
            ) : null}
          </>
        )}
      </Card>


    </>
  );
}

/* --------------------------------------------------------- screen 66 */

function BillingTab({ upgrade }: { upgrade?: PaidTier }) {
  const subscription = useSubscription();
  const history = useBillingHistory();
  const checkout = useStartCheckout();
  const cancel = useCancelSubscription();
  const verify = useVerifyPayment();
  const [confirmCancel, setConfirmCancel] = useState(false);

  // The provider redirects back here with its own reference param, which
  // isn't part of the route's search schema — read it off the URL directly
  // so the tier reflects a successful payment without waiting on a webhook.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const reference = params.get("reference") ?? params.get("tx_ref");
    if (reference) verify.mutate(reference);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const tier = subscription.data?.tier ?? "free";

  return (
    <Row cols="21">
      <div>
        {upgrade || tier === "free" ? (
          <Card title="Checkout" sub={upgrade ? `Upgrading to ${upgrade}` : "Move to a paid plan"} style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <Btn disabled={checkout.isPending} onClick={() => checkout.mutate("basic")}>
                {checkout.isPending ? "Opening checkout…" : "Pay for Basic"}
              </Btn>
              <Btn tone="sec" disabled={checkout.isPending} onClick={() => checkout.mutate("premium")}>
                Pay for Premium
              </Btn>
            </div>
            {checkout.isError ? (
              <div className="errmsg" role="alert">
                {(checkout.error as Error).message}
              </div>
            ) : null}
            <Hint style={{ marginTop: 10 }}>
              Processed by our payment provider. We never see or store your full card number.
            </Hint>
          </Card>
        ) : null}

        <Card title="Payment history">
          {history.isLoading ? (
            <SkeletonRows rows={4} />
          ) : history.isError ? (
            <LoadFailed onRetry={() => history.refetch()} />
          ) : (history.data ?? []).length === 0 ? (
            <Hint>No payment has been taken on this account.</Hint>
          ) : (
            <Tbl>
              <table className="stack">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Provider</th>
                    <th className="num">Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(history.data ?? []).map((payment) => (
                    <tr
                      key={payment.id}
                      style={payment.status === "failed" ? { background: "var(--warnbg)" } : undefined}
                    >
                      <td data-l="Date">{fmtDate(payment.created_at) ?? <Na />}</td>
                      <td data-l="Provider" style={{ textTransform: "capitalize" }}>
                        {payment.provider}
                      </td>
                      <td className="num" data-l="Amount">
                        <Money
                          value={payment.amount}
                          currency={payment.currency === "NGN" ? "₦" : `${payment.currency} `}
                        />
                      </td>
                      <td data-l="Status">
                        <Pill tone={payment.status === "success" ? "a" : payment.status === "pending" ? "c" : "d"}>
                          {payment.status === "success" ? "Paid" : payment.status}
                        </Pill>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Tbl>
          )}
        </Card>
      </div>

      <div>
        <Card title="Your subscription" style={{ marginBottom: 14 }}>
          {subscription.isLoading ? (
            <SkeletonRows rows={5} />
          ) : (
            <table>
              <tbody>
                <tr>
                  <td>Plan</td>
                  <td className="num" style={{ textTransform: "capitalize" }}>
                    {tier}
                  </td>
                </tr>
                <tr>
                  <td>Status</td>
                  <td className="num">
                    <Pill tone={subscription.data?.status === "active" ? "a" : "c"}>
                      {subscription.data?.status ?? "free"}
                    </Pill>
                  </td>
                </tr>
                <tr>
                  <td>Renews</td>
                  <td className="num">
                    {fmtDate(subscription.data?.current_period_end) ?? (
                      <Na reason="No renewal date — this account is on the free plan." />
                    )}
                  </td>
                </tr>
                <tr>
                  <td>Provider</td>
                  <td className="num" style={{ textTransform: "capitalize" }}>
                    {subscription.data?.provider ?? <Na reason="No payment method on file." />}
                  </td>
                </tr>
              </tbody>
            </table>
          )}
        </Card>

        {tier !== "free" ? (
          <Card title="Cancelling — what actually happens" style={{ marginBottom: 14 }}>
            <div
              style={{
                padding: 13,
                border: "1px solid var(--line)",
                borderRadius: 8,
                fontSize: 12.5,
                color: "var(--ink2)",
                lineHeight: 1.7,
              }}
            >
              You keep your current plan until{" "}
              <b>{fmtDate(subscription.data?.current_period_end) ?? "the end of the period you have paid for"}</b>.
              <br />
              <br />
              After that you move to Free: one account, one analysis a month, 90 days of history.
              <br />
              <br />
              <b>Nothing is deleted.</b> Your existing analyses stay readable, and any share link a lender is relying on
              stays valid until it expires.
            </div>

            {subscription.data?.cancel_at_period_end ? (
              <Hint style={{ marginTop: 12 }}>Already scheduled to end at the close of this period.</Hint>
            ) : confirmCancel ? (
              <>
                <Btn tone="dgr" sm block style={{ marginTop: 12 }} disabled={cancel.isPending} onClick={() => cancel.mutate()}>
                  {cancel.isPending ? "Cancelling…" : "Yes, cancel at end of period"}
                </Btn>
                <Btn tone="gho" sm block style={{ marginTop: 8 }} onClick={() => setConfirmCancel(false)}>
                  Keep my plan
                </Btn>
              </>
            ) : (
              <Btn tone="dgr" sm block style={{ marginTop: 12 }} onClick={() => setConfirmCancel(true)}>
                Cancel subscription
              </Btn>
            )}
            {cancel.isError ? (
              <div className="errmsg" role="alert">
                {(cancel.error as Error).message}
              </div>
            ) : null}
          </Card>
        ) : null}


      </div>
    </Row>
  );
}

/* --------------------------------------------------------- screen 55 */

const PLANS = [
  {
    name: "Individual — Free",
    price: "₦0",
    per: null,
    featured: false,
    tier: null,
    lines: ["1 account", "1 analysis a month", "90 days of history", "Full personal analysis", "No assessment sharing"],
  },
  {
    name: "Individual — Plus",
    price: "₦2,500",
    per: "/month",
    featured: true,
    tier: "basic" as PaidTier,
    lines: [
      "Up to 4 accounts consolidated",
      "12 months of history",
      "Unlimited re-runs",
      "1 verifiable share link a month",
      "PDF and CSV export",
    ],
  },
  {
    name: "Institution — Basic",
    price: "₦75,000",
    per: "/month",
    featured: false,
    tier: "basic" as PaidTier,
    lines: [
      "40 assessments included · ₦2,500 each after",
      "Multi-account consolidation",
      "Statement audit",
      "Written lender brief",
      "Share links · 2 seats",
    ],
  },
  {
    name: "Institution — Premium",
    price: "₦200,000",
    per: "/month",
    featured: false,
    tier: "premium" as PaidTier,
    lines: [
      "150 assessments included · ₦1,800 each after",
      "Everything in Basic",
      "Portfolio view",
      "API access & webhooks",
      "10 seats · priority support",
    ],
  },
];

function PlansTab() {
  const subscription = useSubscription();
  const checkout = useStartCheckout();
  const currentTier = subscription.data?.tier ?? "free";

  return (
    <>
      <Row cols={4} style={{ marginBottom: 16 }}>
        {PLANS.map((plan) => {
          const isCurrent =
            (plan.tier === null && currentTier === "free") || (plan.tier !== null && plan.tier === currentTier);
          return (
            <Card key={plan.name} style={plan.featured ? { border: "2px solid var(--g500)" } : undefined}>
              <div
                className="lab"
                style={{ color: plan.featured ? "var(--g700)" : "var(--ink3)", fontSize: 11, fontWeight: 700 }}
              >
                {plan.name}
              </div>
              <div style={{ fontSize: 27, fontWeight: 700, margin: "7px 0" }}>
                {plan.price}
                {plan.per ? <span style={{ fontSize: 13, fontWeight: 500, color: "var(--ink3)" }}>{plan.per}</span> : null}
              </div>
              <table>
                <tbody>
                  {plan.lines.map((line) => (
                    <tr key={line}>
                      <td>{line}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {isCurrent ? (
                <Btn tone="sec" sm block style={{ marginTop: 13 }} disabled>
                  Current plan
                </Btn>
              ) : plan.tier ? (
                <Btn sm block style={{ marginTop: 13 }} disabled={checkout.isPending} onClick={() => checkout.mutate(plan.tier!)}>
                  Upgrade
                </Btn>
              ) : (
                <Btn tone="sec" sm block style={{ marginTop: 13 }} disabled>
                  Included
                </Btn>
              )}
            </Card>
          );
        })}
      </Row>


    </>
  );
}

/* --------------------------------------------------------- screen 68 */

function DeleteTab() {
  const { user } = useAuth();
  const deleteAccount = useDeleteAccount();
  const cancelDelete = useCancelDeleteAccount();
  const [confirmText, setConfirmText] = useState("");

  const scheduled = user?.deletion_requested_at ?? null;

  if (scheduled) {
    const eraseOn = new Date(new Date(scheduled).getTime() + 30 * 86_400_000).toISOString();
    return (
      <Row cols={2}>
        <Card title="The 30-day window">
          <div
            style={{
              padding: 14,
              border: "1px solid var(--line)",
              borderLeft: "4px solid var(--warn)",
              borderRadius: 8,
              background: "var(--warnbg)",
            }}
          >
            <b style={{ fontSize: 12.5, color: "#5C4A16" }}>
              Your account is scheduled for deletion on {fmtDate(eraseOn)}
            </b>
            <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 7 }}>
              Nothing has been erased yet. Choose Restore before that date and everything comes back — except access you
              granted to lenders, which stays revoked and must be granted again.
            </div>
            <div style={{ marginTop: 12 }}>
              <Btn sm disabled={cancelDelete.isPending} onClick={() => cancelDelete.mutate()}>
                {cancelDelete.isPending ? "Restoring…" : "Restore my account"}
              </Btn>
            </div>
          </div>
          {cancelDelete.isError ? (
            <div className="errmsg" role="alert">
              {(cancelDelete.error as Error).message}
            </div>
          ) : null}
        </Card>

        <Card title="What is kept, and why">
          <table>
            <tbody>
              <tr>
                <td>Your analyses and transactions</td>
                <td className="num">Erased</td>
              </tr>
              <tr>
                <td>Your uploaded files</td>
                <td className="num">Erased</td>
              </tr>
              <tr>
                <td>Your consent records</td>
                <td className="num">Retained</td>
              </tr>
              <tr>
                <td>Audit log entries</td>
                <td className="num">Retained</td>
              </tr>
            </tbody>
          </table>
          <Hint style={{ marginTop: 10 }}>
            Consent and audit records are retained because they are the evidence that processing was lawful, and an
            erasure right does not extend to the record proving consent was given. We state this plainly rather than
            hiding it as an exception.
          </Hint>
        </Card>
      </Row>
    );
  }

  return (
    <Row cols={2}>
      <Card title="Before you delete" sub="This is what will happen, in order">
        <Tbl>
          <table className="stack">
            <thead>
              <tr>
                <th />
                <th>Effect</th>
                <th className="num">When</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["1", "You are signed out everywhere", "Immediately"],
                ["2", "Any share link you created is revoked", "Immediately"],
                ["3", "Any monitoring consent ends, and the recipient is told", "Immediately"],
                ["4", "Your connected accounts are disconnected", "Immediately"],
                ["5", "Account recoverable if you change your mind", "30 days"],
                ["6", "Everything permanently erased", "After 30 days"],
              ].map(([n, effect, when]) => (
                <tr key={n}>
                  <td data-l="Step">
                    <b>{n}</b>
                  </td>
                  <td data-l="Effect">{effect}</td>
                  <td className="num" data-l="When">
                    {when}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Tbl>

        <div
          style={{
            marginTop: 16,
            padding: 14,
            border: "1px solid #E9C6C6",
            background: "var(--stopbg)",
            borderRadius: 8,
          }}
        >
          <b style={{ fontSize: 12.5, color: "var(--stop)" }}>If a lender is relying on your data</b>
          <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 7 }}>
            Deleting your Scanwick account ends any monitoring a lender was granted, and they will be notified.{" "}
            <b>This may breach terms you agreed with them.</b> We cannot advise you on that — speak to them first if you
            are unsure.
          </div>
        </div>

        <Field label="Type DELETE to confirm" id="delete-confirm">
          <Inp
            id="delete-confirm"
            placeholder="DELETE"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
          />
        </Field>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn
            tone="dgr"
            disabled={confirmText !== "DELETE" || deleteAccount.isPending}
            onClick={() => deleteAccount.mutate()}
          >
            {deleteAccount.isPending ? "Scheduling…" : "Delete my account"}
          </Btn>
          <Btn tone="gho" onClick={() => setConfirmText("")}>
            Keep my account
          </Btn>
        </div>
        {deleteAccount.isError ? (
          <div className="errmsg" role="alert">
            {(deleteAccount.error as Error).message}
          </div>
        ) : null}
      </Card>


    </Row>
  );
}

/* ------------------------------------------------------------- page */

export function AccountSettingsPage() {
  const { tab, upgrade } = accountRoute.useSearch();
  const navigate = useNavigate();
  const active: AccountTab = (tab as AccountTab) ?? "profile";
  const heading = HEADINGS[active] ?? HEADINGS.profile;

  return (
    <AppShell>
      <Screen>
        <ScreenHead title={heading.title} meta={heading.meta} tag="Account" />

        <div className="stepper" role="tablist" aria-label="Account section">
          {TABS.map((item) => (
            <div
              key={item.id}
              role="tab"
              tabIndex={0}
              aria-selected={active === item.id}
              className={active === item.id ? "on" : ""}
              style={{ cursor: "pointer" }}
              onClick={() => navigate({ to: "/account", search: { tab: item.id } })}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  navigate({ to: "/account", search: { tab: item.id } });
                }
              }}
            >
              {item.label}
            </div>
          ))}
        </div>

        {active === "security" ? (
          <SecurityTab />
        ) : active === "billing" ? (
          <BillingTab upgrade={upgrade} />
        ) : active === "plans" ? (
          <PlansTab />
        ) : active === "delete" ? (
          <DeleteTab />
        ) : active === "markers" ? (
          <ContextualMarkers />
        ) : active === "settings" ? (
          <WorkspaceSettings />
        ) : (
          <ProfileTab />
        )}
      </Screen>
    </AppShell>
  );
}
