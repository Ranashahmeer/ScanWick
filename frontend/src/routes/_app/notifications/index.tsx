import { createFileRoute } from "@tanstack/react-router";
import { NotificationCenterPage } from "@/features/notifications";

export const Route = createFileRoute("/_app/notifications/")({
  component: NotificationCenterPage,
});
