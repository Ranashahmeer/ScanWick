import { createFileRoute } from "@tanstack/react-router";
import { ContactPage } from "@/features/contact";

export const Route = createFileRoute("/contact/")({
  component: ContactPage,
});
