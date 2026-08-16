/**
 * Notifications — prototype screen 50.
 *
 * Immediate for Act and Urgent; digest for Watch and Informational. A
 * portfolio officer who gets forty emails a day stops reading all of them,
 * including the urgent ones — so the delivery rules are visible on the same
 * screen as the list, and preferences are per user rather than per
 * institution.
 */

import { AppShell, Screen } from "@/features/shell/app-shell";
import {
  Btn,
  Card,
  Empty,
  Hint,
  LoadFailed,
  Row,
  ScreenHead,
  Sev,
  SkeletonRows,
  Tbl,
} from "@/components/sw";
import {
  useNotificationPreferences,
  useSaveNotificationPreferences,
} from "@/features/account/billing/notifications-api";

const DELIVERY_RULES = [
  { level: "u" as const, label: "Urgent", email: "Immediate", inApp: "Immediate" },
  { level: "a" as const, label: "Act", email: "Immediate", inApp: "Immediate" },
  { level: "w" as const, label: "Watch", email: "Daily digest", inApp: "Immediate" },
  { level: "i" as const, label: "Informational", email: "Weekly digest", inApp: "Immediate" },
];

export function NotificationCenterPage() {
  const preferences = useNotificationPreferences();
  const savePreferences = useSaveNotificationPreferences();

  const list = preferences.data ?? [];

  return (
    <AppShell>
      <Screen>
        <ScreenHead
          title="Notifications"
          meta="Immediate for Act and Urgent · digest for Watch and Informational"
          tag="Surface 3"
          tagTone="s3"
        />

        <Row cols="21">
          <Card title="Recent" sub="Everything raised on your account">
            <Empty title="Nothing to tell you">
              No signal has been raised and no analysis has finished since you last looked.
            </Empty>
          </Card>

          <div>
            <Card title="How each severity is delivered" style={{ marginBottom: 14 }}>
              <Tbl>
                <table>
                  <thead>
                    <tr>
                      <th>Severity</th>
                      <th>Email</th>
                      <th>In-app</th>
                    </tr>
                  </thead>
                  <tbody>
                    {DELIVERY_RULES.map((rule) => (
                      <tr key={rule.label}>
                        <td>
                          <Sev level={rule.level} />
                          {rule.label}
                        </td>
                        <td>{rule.email}</td>
                        <td>{rule.inApp}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Tbl>
              <Hint style={{ marginTop: 12 }}>Urgent never waits for a digest.</Hint>
            </Card>

            <Card title="Your preferences" sub="Per user, not per workspace">
              {preferences.isLoading ? (
                <SkeletonRows rows={5} />
              ) : preferences.isError ? (
                <LoadFailed onRetry={() => preferences.refetch()} />
              ) : list.length === 0 ? (
                <Hint>No preference rows were returned for your account.</Hint>
              ) : (
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
                      {list.map((preference) => (
                        <tr key={preference.event_key}>
                          <td data-l="Event">{preference.label}</td>
                          <td data-l="Email">
                            <input
                              type="checkbox"
                              checked={preference.email}
                              aria-label={`${preference.label} by email`}
                              onChange={(event) =>
                                savePreferences.mutate(
                                  list.map((row) =>
                                    row.event_key === preference.event_key
                                      ? { ...row, email: event.target.checked }
                                      : row,
                                  ),
                                )
                              }
                            />
                          </td>
                          <td data-l="In-app">
                            <input
                              type="checkbox"
                              checked={preference.in_app}
                              aria-label={`${preference.label} in app`}
                              onChange={(event) =>
                                savePreferences.mutate(
                                  list.map((row) =>
                                    row.event_key === preference.event_key
                                      ? { ...row, in_app: event.target.checked }
                                      : row,
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
              )}
              {savePreferences.isError ? (
                <div className="errmsg" role="alert">
                  {(savePreferences.error as Error).message}
                </div>
              ) : null}
              {savePreferences.isPending ? <Hint>Saving…</Hint> : null}
            </Card>
          </div>
        </Row>



        <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn tone="sec" sm onClick={() => (window.location.href = "/consent")}>
            Consent centre
          </Btn>
          <Btn tone="gho" sm onClick={() => (window.location.href = "/account?tab=profile")}>
            All account settings
          </Btn>
        </div>
      </Screen>
    </AppShell>
  );
}

export default NotificationCenterPage;
