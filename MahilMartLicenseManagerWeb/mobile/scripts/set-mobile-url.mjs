import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const serverConfigPath = path.resolve(__dirname, "..", "www", "server-config.json");

function printUsage() {
  console.log("Usage:");
  console.log("  node scripts/set-mobile-url.mjs --url http(s)://server:port");
  console.log("  node scripts/set-mobile-url.mjs --auto");
}

function normalizeUrl(value) {
  const candidate = (value || "").trim();
  if (!candidate) return "";

  const parsed = new URL(candidate);
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("Only http/https URLs are supported.");
  }

  parsed.hash = "";
  parsed.search = "";
  return parsed.toString().replace(/\/$/, "");
}

function parseArgs() {
  const args = process.argv.slice(2);
  if (args.includes("--auto")) {
    return { mode: "auto", url: "" };
  }

  const flagIndex = args.findIndex((item) => item === "--url" || item === "-u");
  if (flagIndex >= 0 && args[flagIndex + 1]) {
    return { mode: "fixed", url: args[flagIndex + 1] };
  }

  if (args[0] && !args[0].startsWith("-")) {
    return { mode: "fixed", url: args[0] };
  }

  return { mode: "unknown", url: "" };
}

function readConfig() {
  if (!fs.existsSync(serverConfigPath)) {
    return {
      fixedUrl: "",
      port: 8001,
      healthPath: "/healthz/",
    };
  }
  return JSON.parse(fs.readFileSync(serverConfigPath, "utf8"));
}

function main() {
  const parsed = parseArgs();
  if (parsed.mode === "unknown") {
    printUsage();
    process.exit(1);
  }

  const config = readConfig();

  if (parsed.mode === "auto") {
    config.fixedUrl = "";
    fs.writeFileSync(serverConfigPath, `${JSON.stringify(config, null, 2)}\n`, "utf8");
    console.log("Configured mobile wrapper for auto-detect mode.");
    return;
  }

  const normalizedUrl = normalizeUrl(parsed.url);
  config.fixedUrl = normalizedUrl;
  fs.writeFileSync(serverConfigPath, `${JSON.stringify(config, null, 2)}\n`, "utf8");
  console.log(`Configured fixed server URL: ${normalizedUrl}`);
}

try {
  main();
} catch (err) {
  console.error(err.message || String(err));
  process.exit(1);
}
