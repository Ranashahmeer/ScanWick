import { redirect } from "@tanstack/react-router"

import { ensureAuthBootstrapped } from "@/lib/auth-bootstrap"
import { authStore } from "@/lib/auth-store"

// For /_auth/* routes (login, register, reset, etc.) — bounce an already
// signed-in user straight to the app instead of showing them a login form.
export async function requireGuest(): Promise<void> {
  await ensureAuthBootstrapped()
  if (authStore.getState().status === "authenticated") {
    // Land on Upload, not the dashboard — the dashboard only makes sense
    // once there's real analysis to show.
    throw redirect({ to: "/upload" })
  }
}

// For /_app/* routes — send a signed-out visitor to login, remembering
// where they were headed so we can return them there afterwards.
export async function requireAuth(redirectTo: string): Promise<void> {
  await ensureAuthBootstrapped()
  if (authStore.getState().status !== "authenticated") {
    throw redirect({ to: "/login", search: { redirect: redirectTo } })
  }
}
