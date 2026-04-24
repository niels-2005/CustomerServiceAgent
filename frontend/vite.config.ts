import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const rootEnv = loadEnv(mode, "..", "");

  return {
    envDir: "..",
    define: {
      __LANGFUSE_PUBLIC_KEY__: JSON.stringify(rootEnv.LANGFUSE_PUBLIC_KEY ?? ""),
      __LANGFUSE_HOST__: JSON.stringify(rootEnv.VITE_LANGFUSE_HOST || rootEnv.LANGFUSE_HOST || ""),
    },
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 5173,
    },
  };
});
