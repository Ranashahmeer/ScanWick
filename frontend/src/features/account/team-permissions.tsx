import { useState } from "react";
import { toast } from "sonner";
import {
  is403,
  ROLE_OPTIONS_BY_VERTICAL,
  useInviteMember,
  useRemoveMember,
  useResendInvite,
  useRevokeInvite,
  useTeam,
  useUpdateMemberRole,
  VERTICAL_LABELS,
  VERTICALS,
  type Invite,
  type Member,
  type Vertical,
} from "./team-api";
import { LoadingLabel } from "@/components/ui/spinner";
import { Skeleton } from "@/components/ui/skeleton";

interface GroupedMember {
  user_id: number;
  email: string;
  first_name: string | null;
  last_name: string | null;
  roles: Member[];
}

function groupByUser(members: Member[]): GroupedMember[] {
  const byUserId = new Map<number, GroupedMember>();
  for (const member of members) {
    const existing = byUserId.get(member.user_id);
    if (existing) {
      existing.roles.push(member);
    } else {
      byUserId.set(member.user_id, {
        user_id: member.user_id,
        email: member.email,
        first_name: member.first_name,
        last_name: member.last_name,
        roles: [member],
      });
    }
  }
  return [...byUserId.values()];
}

const LOWEST_PRIVILEGE_ROLE: Record<Vertical, string> = {
  bank: "bank_viewer",
  ecommerce: "viewer",
};

export function TeamPermissions() {
  const { data, isLoading, error } = useTeam();
  const inviteMember = useInviteMember();
  const resendInvite = useResendInvite();
  const revokeInvite = useRevokeInvite();
  const removeMember = useRemoveMember();
  const updateMemberRole = useUpdateMemberRole();

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteVertical, setInviteVertical] = useState<Vertical>("bank");
  const [inviteRole, setInviteRole] = useState(LOWEST_PRIVILEGE_ROLE.bank);

  const [editingRole, setEditingRole] = useState<{ userId: number; vertical: Vertical } | null>(null);
  const [editRoleValue, setEditRoleValue] = useState("");

  if (isLoading) {
    return (
      <div className="acct-card">
        <div className="acct-table acct-table-members">
          <div className="acct-table-head">
            <span>Member</span>
            <span>Roles</span>
            <span />
          </div>
          {[0, 1, 2].map((row) => (
            <div className="acct-table-row" key={row}>
              <div className="acct-member-cell">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-40 acct-mt" />
              </div>
              <Skeleton className="h-6 w-24" />
              <span />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    if (is403(error)) {
      return (
        <div className="acct-card">
          <h2>Team</h2>
          <p className="acct-card-hint">
            Only your account's primary owner — whoever originally signed up — can view and manage the team.
          </p>
        </div>
      );
    }
    return (
      <div className="acct-card">
        <p className="acct-card-hint">Could not load your team. Please try again.</p>
      </div>
    );
  }

  const members = groupByUser(data?.members ?? []);
  const pendingInvites: Invite[] = data?.pending_invites ?? [];

  function handleVerticalChange(vertical: Vertical) {
    setInviteVertical(vertical);
    setInviteRole(LOWEST_PRIVILEGE_ROLE[vertical]);
  }

  function handleSendInvite() {
    const email = inviteEmail.trim();
    if (!email) return;

    inviteMember.mutate(
      {
        email,
        vertical: inviteVertical,
        role: inviteRole,
      },
      {
        onSuccess: () => {
          toast.success(`Invite sent to ${email}.`);
          setInviteEmail("");
        },
        onError: (err) => toast.error(err instanceof Error ? err.message : "Could not send this invite."),
      }
    );
  }

  function startEditingRole(userId: number, role: Member) {
    setEditingRole({ userId, vertical: role.vertical });
    setEditRoleValue(role.role);
  }

  function saveEditedRole(userId: number) {
    if (!editingRole) return;
    updateMemberRole.mutate(
      { userId, vertical: editingRole.vertical, role: editRoleValue },
      {
        onSuccess: () => {
          toast.success("Role updated.");
          setEditingRole(null);
        },
        onError: (err) => toast.error(err instanceof Error ? err.message : "Could not update this member's role."),
      }
    );
  }

  return (
    <div className="acct-stack">
      <div className="acct-card">
        <h2>Members</h2>
        <div className="acct-table acct-table-members">
          <div className="acct-table-head">
            <span>Member</span>
            <span>Roles</span>
            <span />
          </div>
          {members.map((member) => (
            <div className="acct-table-row" key={member.user_id}>
              <div className="acct-member-cell">
                <strong>{[member.first_name, member.last_name].filter(Boolean).join(" ") || member.email}</strong>
                <span>{member.email}</span>
              </div>
              <div className="acct-role-tags">
                {member.roles.map((role) =>
                  editingRole?.userId === member.user_id && editingRole.vertical === role.vertical ? (
                    <span className="acct-role-tag" key={`${member.user_id}-${role.vertical}-editing`}>
                      {VERTICAL_LABELS[role.vertical]}:{" "}
                      <select value={editRoleValue} onChange={(event) => setEditRoleValue(event.target.value)}>
                        {ROLE_OPTIONS_BY_VERTICAL[role.vertical].map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                      <button type="button" className="acct-link" onClick={() => saveEditedRole(member.user_id)}>
                        Save
                      </button>
                      <button type="button" className="acct-link" onClick={() => setEditingRole(null)}>
                        Cancel
                      </button>
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="acct-role-tag"
                      key={`${member.user_id}-${role.vertical}`}
                      onClick={() => startEditingRole(member.user_id, role)}
                      title="Click to change this member's role for this module"
                    >
                      {VERTICAL_LABELS[role.vertical]}: {role.role}
                    </button>
                  )
                )}
              </div>
              <button
                type="button"
                className="acct-btn-outline"
                onClick={() =>
                  removeMember.mutate(member.user_id, {
                    onSuccess: () => toast.success("Removed from your team."),
                    onError: (err) =>
                      toast.error(err instanceof Error ? err.message : "Could not remove this member."),
                  })
                }
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="acct-card">
        <h2>Invite a member</h2>
        <p className="acct-card-hint">
          They'll get an email link. Each invite grants one module at the role you pick — send another invite to
          grant a second module to the same person.
        </p>

        <div className="acct-form-grid">
          <label className="acct-field">
            <span>Email</span>
            <input
              type="email"
              placeholder="name@company.com"
              value={inviteEmail}
              onChange={(event) => setInviteEmail(event.target.value)}
            />
          </label>
          <label className="acct-field">
            <span>Module</span>
            <select value={inviteVertical} onChange={(event) => handleVerticalChange(event.target.value as Vertical)}>
              {VERTICALS.map((vertical) => (
                <option key={vertical} value={vertical}>
                  {VERTICAL_LABELS[vertical]}
                </option>
              ))}
            </select>
          </label>
          <label className="acct-field">
            <span>Role</span>
            <select value={inviteRole} onChange={(event) => setInviteRole(event.target.value)}>
              {ROLE_OPTIONS_BY_VERTICAL[inviteVertical].map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </label>
        </div>

        <button
          type="button"
          className="dqr-action-primary acct-mt"
          disabled={inviteMember.isPending}
          onClick={handleSendInvite}
        >
          {inviteMember.isPending ? <LoadingLabel label="Sending…" /> : "Send Invite"}
        </button>
      </div>

      <div className="acct-card">
        <h2>Pending invites</h2>
        {pendingInvites.length ? (
          <div className="acct-invite-list">
            {pendingInvites.map((invite) => (
              <div className="acct-invite-row" key={invite.id}>
                <div>
                  <strong>{invite.email}</strong>
                  <span>
                    {VERTICAL_LABELS[invite.vertical]}: {invite.role}
                    {invite.expires_at ? ` · expires ${new Date(invite.expires_at).toLocaleDateString()}` : ""}
                  </span>
                </div>
                <div className="acct-invite-actions">
                  <button
                    type="button"
                    className="acct-btn-outline"
                    onClick={() =>
                      resendInvite.mutate(invite.id, { onSuccess: () => toast.success("Invite resent.") })
                    }
                  >
                    Resend
                  </button>
                  <button
                    type="button"
                    className="acct-btn-outline"
                    onClick={() =>
                      revokeInvite.mutate(invite.id, { onSuccess: () => toast.success("Invite cancelled.") })
                    }
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="acct-muted">No pending invites.</p>
        )}
      </div>
    </div>
  );
}
