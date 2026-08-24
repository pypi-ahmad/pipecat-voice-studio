import react from "@vitejs/plugin-react";
import process from "node:process";
import { defineConfig, type UserConfig } from "vite";

export default defineConfig(() => {
  const isDev = process.env.NODE_ENV !== "production";
  return {
    base: "./",
    plugins: [react()],
    define: {
      "process.env.NODE_ENV": JSON.stringify(process.env.NODE_ENV),
    },
    build: {
      minify: isDev ? false : "oxc",
      outDir: "build",
      sourcemap: isDev,
      lib: {
        entry: "./src/index.tsx",
        name: "PipecatVoiceStudio",
        formats: ["es"],
        fileName: "index-[hash]",
      },
    },
  } satisfies UserConfig;
});
