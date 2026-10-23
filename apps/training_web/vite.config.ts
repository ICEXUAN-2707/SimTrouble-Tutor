import { defineConfig } from "vite";

export default defineConfig({
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: "three-runtime",
              test: /node_modules[\\/]three[\\/]/,
            },
          ],
        },
      },
    },
  },
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8001",
      "/healthz": "http://127.0.0.1:8001",
    },
  },
  preview: {
    port: 4173,
    strictPort: true,
  },
});
