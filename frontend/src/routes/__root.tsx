import { useEffect } from "react";
import { type QueryClient } from "@tanstack/react-query";
import { createRootRouteWithContext, Outlet, useNavigate } from "@tanstack/react-router";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";
import { NavigationProgress } from "@/components/navigation-progress";
import { GeneralError } from "@/features/errors/general-error";
import { NotFoundError } from "@/features/errors/not-found-error";
import { Toaster } from "@/components/ui/sonner";
import { authClient } from "@/lib/api-client";
import { clearTokens, setTokens } from "@/lib/auth-tokens";
import { authStore, type AuthUser } from "@/lib/auth-store";
import { ensureAuthBootstrapped } from "@/lib/auth-bootstrap";

// The Google OAuth callback (backend's /api/auth/google/callback) redirects
// to `${frontend_url}/#access_token=...&refresh_token=...` — a URL fragment
// on whatever page the browser lands on, not a dedicated route. Parsing it
// here, once, at the app root covers that regardless of which path it's on.
function useGoogleOAuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    const hash = window.location.hash.startsWith("#")
      ? window.location.hash.slice(1)
      : window.location.hash;
    if (!hash) return;

    const params = new URLSearchParams(hash);
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    if (!accessToken || !refreshToken) return;

    // Strip the fragment immediately so tokens never linger in browser
    // history/the visible URL.
    window.history.replaceState(null, "", window.location.pathname + window.location.search);

    setTokens({ accessToken, refreshToken });
    authClient
      .get<AuthUser>("/me")
      .then(({ data }) => {
        authStore.setAuthenticated(data);
        // Land on Upload, not the dashboard — see login/index.tsx for why.
        navigate({ to: "/upload" });
      })
      .catch(() => {
        // Tokens were already set above but `/me` failed — don't leave a
        // live refresh cookie in place while the app reports unauthenticated
        // (matches the equivalent failure path in auth-bootstrap.ts).
        clearTokens();
        authStore.setUnauthenticated();
      });
  }, [navigate]);
}

function RootComponent() {
  useGoogleOAuthCallback();

  return (
    <div className="flex flex-col h-screen">

      <NavigationProgress />
      <Outlet />

      <Toaster duration={5000} />
      {import.meta.env.MODE === "development" && (
        <>
          <ReactQueryDevtools buttonPosition="bottom-left" />
          <TanStackRouterDevtools position="bottom-right" />
        </>
      )}
    </div>
  );
}

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient;
}>()({
  // Public pages (landing, blog, etc.) have no auth beforeLoad of their own,
  // so without this the auth store would just sit at its initial "loading"
  // state on them forever — anything reading useAuth() there (e.g. the
  // landing header's Sign in / Go to app link) would never see a real
  // session even when one exists. ensureAuthBootstrapped() is memoized, so
  // _app/_auth routes calling it again on top of this is a no-op.
  beforeLoad: () => ensureAuthBootstrapped(),
  component: RootComponent,
  notFoundComponent: NotFoundError,
  errorComponent: GeneralError,
});
