/**
 * Institution — prototype screens 53 (team & roles), 54 (credit ledger) and
 * 56 (API & webhooks).
 *
 * The row in bold on screen 53 is a correctness requirement, not a
 * convenience: a role that reads assessments does not thereby read
 * transaction-level data. The capability matrix is shown at the point a
 * role is assigned, so an admin sees what they are granting before they
 * grant it.
 *
 * On screen 54, quota is enforced at creation and never at read. An
 * assessment a lender relied on to make a decision stays readable
 * permanently, whatever happens to the subscription.
 */

import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { AppShell, Screen } from "@/features/shell/app-shell";
import {
  Btn,
  Card,
  Check,
  Empty,
  Field,
  Hint,
  Inp,
  Kpi,
  LoadFailed,
  Na,
  Pill,
  Row,
  ScreenHead,
  Select,
  SkeletonRows,
  Tbl,
} from "@/components/sw";
import { fmtDate } from "@/components/sw/format";
import {
  ROLE_OPTIONS_BY_VERTICAL,
  VERTICALS,
  VERTICAL_LABELS,
  is403,
  useInviteMember,
  useRemoveMember,
  useResendInvite,
  useRevokeInvite,
  useTeam,
  useUpdateMemberRole,
  type Vertical,
} from "@/features/account/team-api";
import { useSubscription } from "@/features/account/billing/payments-api";

export type InstitutionView = "team" | "credits" | "api";

const HEADINGS: Record<InstitutionView, { title: string; meta: string }> = {
  team: { title: "Team & roles", meta: "Who is on your team, and what each role can access" },
  credits: { title: "Credit ledger", meta: "Every grant, consumption and refund" },
  api: { title: "API & webhooks", meta: "Server-to-server, so signals reach your own system" },
};

export function InstitutionPage({ view = "team" }: { view?: InstitutionView }) {
  const heading = HEADINGS[view] ?? HEADINGS.team;
  return (
    <AppShell>
      <Screen>
        <ScreenHead title={heading.title} meta={heading.meta} tag="Institution" />
        {view === "credits" ? <CreditLedger /> : view === "api" ? <ApiWebhooks /> : <TeamRoles />}
      </Screen>
    </AppShell>
  );
}

/* ---------------------------------------------------------- screen 53 */

const CAPABILITIES: { label: string; bold?: boolean; roles: Record<string, boolean> }[] = [
  { label: "Create assessment", roles: { owner: true, admin: true, officer: true, viewer: false } },
  { label: "Read lender brief", roles: { owner: true, admin: true, officer: true, viewer: true } },
  { label: "Read transaction detail", bold: true, roles: { owner: true, admin: true, officer: true, viewer: false } },
  { label: "Monitoring portfolio", roles: { owner: true, admin: true, officer: false, viewer: true } },
  { label: "Acknowledge signals", roles: { owner: true, admin: true, officer: false, viewer: false } },
  { label: "Billing & credits", roles: { owner: true, admin: false, officer: false, viewer: false } },
  { label: "Manage team", roles: { owner: true, admin: false, officer: false, viewer: false } },
  { label: "API keys", roles: { owner: true, admin: false, officer: false, viewer: false } },
];

function roleLabel(role: string): string {
  return role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function TeamRoles() {
  const team = useTeam();
  const invite = useInviteMember();
  const resend = useResendInvite();
  const revoke = useRevokeInvite();
  const updateRole = useUpdateMemberRole();
  const removeMember = useRemoveMember();

  const [email, setEmail] = useState("");
  const [vertical, setVertical] = useState<Vertical>("bank");
  const [role, setRole] = useState(ROLE_OPTIONS_BY_VERTICAL.bank[1]);

  if (team.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={5} />
      </Card>
    );
  }

  if (team.isError) {
    if (is403(team.error)) {
      return (
        <Card title="Team management is owner-only">
          <Hint>
            Only the workspace owner can see and change who has access. That separation is deliberate — an admin who can
            read assessments should not thereby be able to grant someone else that access.
          </Hint>
        </Card>
      );
    }
    return <LoadFailed onRetry={() => team.refetch()} />;
  }

  const members = team.data?.members ?? [];
  const invites = (team.data?.pending_invites ?? []).filter((i) => i.status === "pending");

  return (
    <>
      <Card
        title="Members"
        sub={`${members.length} member${members.length === 1 ? "" : "s"} · ${invites.length} pending invite${invites.length === 1 ? "" : "s"}`}
        style={{ marginBottom: 16 }}
      >
        {members.length === 0 ? (
          <Empty title="No member yet">Invite a colleague below and choose exactly what their role can see.</Empty>
        ) : (
          <Tbl>
            <table className="stack">
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Module</th>
                  <th>Role</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={`${member.user_id}-${member.vertical}`}>
                    <td data-l="Member">
                      <b>
                        {[member.first_name, member.last_name].filter(Boolean).join(" ") || member.email}
                      </b>
                      <Hint>{member.email}</Hint>
                    </td>
                    <td data-l="Module">{VERTICAL_LABELS[member.vertical]}</td>
                    <td data-l="Role">
                      <Select
                        value={member.role}
                        aria-label={`Role for ${member.email}`}
                        onChange={(e) =>
                          updateRole.mutate({
                            userId: member.user_id,
                            vertical: member.vertical,
                            role: e.target.value,
                          })
                        }
                        style={{ padding: "5px 28px 5px 8px", fontSize: 11.5 }}
                      >
                        {ROLE_OPTIONS_BY_VERTICAL[member.vertical].map((option) => (
                          <option key={option} value={option}>
                            {roleLabel(option)}
                          </option>
                        ))}
                      </Select>
                    </td>
                    <td>
                      <Btn tone="dgr" sm onClick={() => removeMember.mutate(member.user_id)}>
                        Remove
                      </Btn>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Tbl>
        )}

        {invites.length > 0 ? (
          <>
            <h3 style={{ marginTop: 20 }}>Pending invites</h3>
            <table>
              <tbody>
                {invites.map((pending) => (
                  <tr key={pending.id}>
                    <td>
                      {pending.email}
                      <Hint>
                        {roleLabel(pending.role)} · expires {fmtDate(pending.expires_at) ?? "—"}
                      </Hint>
                    </td>
                    <td className="num">
                      <Pill tone="c">Pending</Pill>
                    </td>
                    <td>
                      <Btn tone="gho" sm onClick={() => resend.mutate(pending.id)}>
                        Resend
                      </Btn>{" "}
                      <Btn tone="dgr" sm onClick={() => revoke.mutate(pending.id)}>
                        Revoke
                      </Btn>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
      </Card>

      <Row cols="21">
        <Card
          title="What each role can see"
          sub="What each role can access"
        >
          <Tbl>
            <table className="stack">
              <thead>
                <tr>
                  <th>Capability</th>
                  <th>Owner</th>
                  <th>Admin</th>
                  <th>Officer</th>
                  <th>Viewer</th>
                </tr>
              </thead>
              <tbody>
                {CAPABILITIES.map((capability) => (
                  <tr key={capability.label}>
                    <td data-l="Capability">
                      {capability.bold ? <b>{capability.label}</b> : capability.label}
                    </td>
                    {["owner", "admin", "officer", "viewer"].map((key) => (
                      <td key={key} data-l={key}>
                        {capability.roles[key] ? "✓" : capability.bold ? <b>—</b> : "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </Tbl>

        </Card>

        <Card title="Invite a colleague">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              invite.mutate(
                { email, vertical, role },
                {
                  onSuccess: () => setEmail(""),
                },
              );
            }}
          >
            <Field label="Email" id="invite-email">
              <Inp
                id="invite-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="colleague@example-mfb.ng"
              />
            </Field>
            <Field label="Module" id="invite-vertical">
              <Select
                id="invite-vertical"
                value={vertical}
                onChange={(e) => {
                  const next = e.target.value as Vertical;
                  setVertical(next);
                  setRole(ROLE_OPTIONS_BY_VERTICAL[next][1]);
                }}
              >
                {VERTICALS.map((option) => (
                  <option key={option} value={option}>
                    {VERTICAL_LABELS[option]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Role" id="invite-role" hint="Check the matrix beside this before you send.">
              <Select id="invite-role" value={role} onChange={(e) => setRole(e.target.value)}>
                {ROLE_OPTIONS_BY_VERTICAL[vertical].map((option) => (
                  <option key={option} value={option}>
                    {roleLabel(option)}
                  </option>
                ))}
              </Select>
            </Field>
            <Btn sm block type="submit" disabled={invite.isPending || !email}>
              {invite.isPending ? "Sending…" : "Send invite"}
            </Btn>
            {invite.isError ? (
              <div className="errmsg" role="alert">
                {(invite.error as Error).message}
              </div>
            ) : null}
          </form>
        </Card>
      </Row>
    </>
  );
}

/* ---------------------------------------------------------- screen 54 */

function CreditLedger() {
  const subscription = useSubscription();
  const navigate = useNavigate();
  const tier = subscription.data?.tier ?? "free";

  return (
    <>
      <Row cols={4} style={{ marginBottom: 16 }}>
        <Kpi
          label="Balance"
          value={<Na reason="Assessment credits are not issued by the billing service yet." />}
          valueStyle={{ fontSize: 16 }}
          detail="assessments remaining"
        />
        <Kpi label="Used this cycle" value={0} detail={tier === "free" ? "free plan" : `on ${tier}`} />
        <Kpi
          label="Resets"
          value={fmtDate(subscription.data?.current_period_end) ?? "—"}
          valueStyle={{ fontSize: 17 }}
          detail="at the start of the next period"
        />
        <Kpi label="Plan" value={tier} valueStyle={{ fontSize: 19, textTransform: "capitalize" }} detail="assessments, not seats" />
      </Row>

      <Row cols="21">
        <Card
          title="Ledger"
          sub="Every entry has a source and an expiry"
        >
          <Empty title="No ledger entry yet">
            A subscription grant, each assessment consumed, every refund and any promotional grant appears here as its own
            append-only row.
          </Empty>
        </Card>

        <div>
          <Card title="Two rules the design honours" style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.75 }}>
              <b>Re-running is free within validity.</b> An assessment is valid 30 days and re-running inside that window
              consumes nothing.
              <br />
              <br />
              <b>Reading never consumes and never blocks.</b> An assessment a lender relied on to make a decision stays
              readable permanently, whatever happens to the subscription.
            </div>
          </Card>

          <Card title="Change plan">
            <Btn sm block onClick={() => navigate({ to: "/account", search: { tab: "plans" } })}>
              See plans
            </Btn>
            <Btn tone="sec" sm block style={{ marginTop: 8 }} onClick={() => navigate({ to: "/account", search: { tab: "billing" } })}>
              Billing & payments
            </Btn>
          </Card>
        </div>
      </Row>
    </>
  );
}

/* ---------------------------------------------------------- screen 56 */

const WEBHOOK_EVENTS = [
  { key: "assessment.completed", on: true },
  { key: "signal.raised", on: true },
  { key: "consent.revoked", on: true },
  { key: "statement.failed", on: false },
];

function ApiWebhooks() {
  const [endpoint, setEndpoint] = useState("");
  const [events, setEvents] = useState(() => Object.fromEntries(WEBHOOK_EVENTS.map((e) => [e.key, e.on])));

  return (
    <>
      <Row cols={2}>
        <Card title="API keys" sub="Shown once at creation and never again">
          <Empty title="No API key issued">
            A key is issued per environment and shown exactly once. Nothing is stored that could show it to you again.
          </Empty>
          <Btn sm style={{ marginTop: 13 }} disabled>
            Create key
          </Btn>
        </Card>

        <Card title="Webhooks" sub="Where Scanwick posts events">
          <Field label="Endpoint" id="webhook-endpoint">
            <Inp
              id="webhook-endpoint"
              className="mono"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              placeholder="https://api.example-mfb.ng/hooks/scanwick"
            />
          </Field>
          <div className="field">
            <label>Events</label>
            {WEBHOOK_EVENTS.map((event) => (
              <Check
                key={event.key}
                label={<span className="mono">{event.key}</span>}
                checked={events[event.key]}
                onChange={(e) => setEvents((current) => ({ ...current, [event.key]: e.target.checked }))}
              />
            ))}
          </div>
          <Btn sm disabled>
            Save
          </Btn>{" "}
          <Btn tone="gho" sm disabled>
            Send test event
          </Btn>
        </Card>
      </Row>

      <Card title="Recent deliveries" style={{ marginTop: 16 }}>
        <Empty title="No delivery attempted">
          Failed deliveries retry with backoff and are replayable, so an endpoint that was down can see and replay what it
          missed.
        </Empty>
      </Card>


    </>
  );
}

export default InstitutionPage;
