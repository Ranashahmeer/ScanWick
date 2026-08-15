import path from "path";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite"; // Add this
import { defineConfig } from "vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";

export default defineConfig({
  plugins: [
    tanstackRouter({
      target: "react",
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(), // Add this
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // Lets a cloudflared quick tunnel (random *.trycloudflare.com host per
    // run) reach the dev server — Vite blocks unrecognized Host headers by
    // default. Remove/tighten once client testing is done.
    allowedHosts: [".trycloudflare.com"],
  },
});
