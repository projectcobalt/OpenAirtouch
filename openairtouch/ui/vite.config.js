import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  plugins: [svelte()],
  build: {
    outDir: "../src/openairtouch/service/web",
    emptyOutDir: true,
    assetsDir: "ui-assets"
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8099",
      "/ws": {
        target: "ws://127.0.0.1:8099",
        ws: true
      },
      "/assets": "http://127.0.0.1:8099"
    }
  }
});
