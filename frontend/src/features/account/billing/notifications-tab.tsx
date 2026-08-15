import { useState } from "react";
import { toast } from "sonner";
import { Toggle } from "../components/toggle";
import {
  useNotificationPreferences,
  useSaveNotificationPreferences,
  type NotificationPreference,
} from "./notifications-api";

type Channel = "email" | "in_app" | "slack";

export function NotificationsTab() {
  const { data, isLoading } = useNotificationPreferences();
  const savePreferences = useSaveNotificationPreferences();
  const [preferences, setPreferences] = useState<NotificationPreference[]>([]);
  // Seeds local (editable) state from the fetched defaults/overrides the
  // first time they arrive, without re-syncing on every refetch — done
  // during render (React docs' "adjusting state when a prop changes"
  // pattern) rather than in a useEffect, which would cost an extra render.
  const [seededFrom, setSeededFrom] = useState<NotificationPreference[] | undefined>(undefined);
  if (data && data !== seededFrom) {
    setSeededFrom(data);
    setPreferences(data);
  }

  const toggle = (eventKey: string, channel: Channel) => {
    setPreferences((current) =>
      current.map((preference) =>
        preference.event_key === eventKey ? { ...preference, [channel]: !preference[channel] } : preference,
      ),
    );
  };

  function handleSave() {
    savePreferences.mutate(preferences, {
      onSuccess: () => toast.success("Notification preferences saved."),
      onError: (error) => toast.error(error instanceof Error ? error.message : "Could not save your preferences."),
    });
  }

  return (
    <div className="acct-card">
      <h2>Notification preferences</h2>
      <p className="acct-card-hint">Choose how you're notified for each event type.</p>

      <div className="acct-notif-table">
        <div className="acct-notif-head">
          <span>Event</span>
          <span>Email</span>
          <span>In-app</span>
          <span>Slack</span>
        </div>
        {isLoading ? <div className="acct-notif-row">Loading…</div> : null}
        {preferences.map((preference) => (
          <div className="acct-notif-row" key={preference.event_key}>
            <span>{preference.label}</span>
            <Toggle
              checked={preference.email}
              onChange={() => toggle(preference.event_key, "email")}
              label={`${preference.label} email`}
            />
            <Toggle
              checked={preference.in_app}
              onChange={() => toggle(preference.event_key, "in_app")}
              label={`${preference.label} in-app`}
            />
            <Toggle
              checked={preference.slack}
              onChange={() => toggle(preference.event_key, "slack")}
              label={`${preference.label} slack`}
            />
          </div>
        ))}
      </div>

      <button
        type="button"
        className="dqr-action-primary acct-mt"
        onClick={handleSave}
        disabled={savePreferences.isPending || isLoading}
      >
        {savePreferences.isPending ? "Saving…" : "Save preferences"}
      </button>
    </div>
  );
}
