import { createFileRoute } from "@tanstack/react-router";
import { BlogPostPage } from "@/features/blog/post";

export const Route = createFileRoute("/blog/$slug")({
  component: BlogPostPage,
});
