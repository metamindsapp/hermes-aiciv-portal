import { defineConfig } from "vite";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  build: {
    emptyOutDir: false,
    lib: {
      entry: resolve(here, "src/index.js"),
      formats: ["iife"],
      name: "AiCIVWorkspacePlugin",
      fileName: () => "index.js",
    },
    outDir: resolve(here, "dist"),
    target: "es2022",
    minify: false,
    sourcemap: false,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
});
