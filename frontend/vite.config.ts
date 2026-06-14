import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Tailwind v4 is wired as a Vite plugin (no tailwind.config.js / postcss).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Dev: forward API calls to the FastAPI backend.
      "/api": "http://localhost:8000",
    },
  },
});
