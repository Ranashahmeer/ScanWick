import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { isAxiosError } from "axios"
import { apiClient } from "@/lib/api-client"

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.error?.message === "string") {
    return error.response.data.error.message
  }
  return fallback
}

export function is403(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 403
}

export class TeamApiError extends Error {}

interface Envelope<T> {
  success: boolean
  data: T
}

// ---- Roles vocabulary — mirrors backend/app/models/user_merchant_roles.py exactly ----
export type Vertical = "bank" | "ecommerce"

export const VERTICALS: Vertical[] = ["bank", "ecommerce"]

export const VERTICAL_LABELS: Record<Vertical, string> = {
  bank: "Bank",
  ecommerce: "E-commerce",
}

export const ROLE_OPTIONS_BY_VERTICAL: Record<Vertical, string[]> = {
  bank: ["bank_owner", "bank_admin", "loan_officer", "bank_viewer"],
  ecommerce: ["owner", "admin", "manager", "viewer"],
}

// ---- Members & invites ----
export interface Member {
  user_id: number
  email: string
  first_name: string | null
  last_name: string | null
  vertical: Vertical
  role: string
  rep_id: string | null
}

export interface Invite {
  id: string
  email: string
  vertical: Vertical
  role: string
  rep_id: string | null
  status: "pending" | "accepted" | "revoked" | "expired"
  expires_at: string | null
}

interface TeamData {
  members: Member[]
  pending_invites: Invite[]
}

export function useTeam() {
  return useQuery({
    queryKey: ["team", "members"],
    queryFn: async () => {
      const { data } = await apiClient.get<Envelope<TeamData>>("/team/members")
      return data.data
    },
    retry: false, // a 403 here means "not the primary owner" — retrying won't change that
  })
}

export function useInviteMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: { email: string; vertical: Vertical; role: string; rep_id?: string }) => {
      try {
        const { data } = await apiClient.post<Envelope<Invite>>("/team/invite", body)
        return data.data
      } catch (error) {
        throw new TeamApiError(errorMessage(error, "Could not send this invite. Please try again."))
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team", "members"] })
    },
  })
}

export function useResendInvite() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (inviteId: string) => {
      await apiClient.post(`/team/invite/${inviteId}/resend`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team", "members"] })
    },
  })
}

export function useRevokeInvite() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (inviteId: string) => {
      await apiClient.delete(`/team/invite/${inviteId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team", "members"] })
    },
  })
}

export function useUpdateMemberRole() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (params: { userId: number; vertical: Vertical; role: string; rep_id?: string }) => {
      try {
        await apiClient.patch(`/team/members/${params.userId}`, {
          vertical: params.vertical,
          role: params.role,
          rep_id: params.rep_id,
        })
      } catch (error) {
        throw new TeamApiError(errorMessage(error, "Could not update this member's role."))
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team", "members"] })
    },
  })
}

export function useRemoveMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (userId: number) => {
      try {
        await apiClient.delete(`/team/members/${userId}`)
      } catch (error) {
        throw new TeamApiError(errorMessage(error, "Could not remove this member."))
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team", "members"] })
    },
  })
}
