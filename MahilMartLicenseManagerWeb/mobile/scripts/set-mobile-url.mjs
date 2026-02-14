import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const configPath = path.resolve(__dirname, "..", "capacitor.config.json");

function printUsage() {
  console.log("Usage: node scripts/set-mobile-url.mjs --url http(s)://server:port");
}

function getUrlArg() {
  const args = process.argv.slice(2);
  const flagIndex = args.findIndex((item) => item === "--url" || item === "-u");
  if (flagIndex >= 0 && args[flagIndex + 1]) {
    return args[flagIndex + 1];
  }
  if (args[0] && !args[0].startsWith("-")) {
    return args[0];
  }
  return "";
}

function normalizeUrl(value) {
  const candidate = (value || "").trim();
  if (!candidate) {
    throw new Error("Missing URL value.");
  }

  const parsed = new URL(candidate);
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("Only http/https URLs are supported.");
  }

  parsed.hash = "";
  parsed.search = "";
  const normalized = parsed.toString().replace(/\/$/, "");
  return normalized;
}

function main() {
  const rawUrl = getUrlArg();
  if (!rawUrl) {
    printUsage();
    process.exit(1);
  }

  if (!fs.existsSync(configPath)) {
    throw new Error(`Config file not found: ${configPath}`);
  }

  const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
  const normalizedUrl = normalizeUrl(rawUrl);
  const cleartext = normalizedUrl.startsWith("http://");

  config.server = {
    url: normalizedUrl,
    cleartext
  };

  fs.writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`, "utf8");
  console.log(`Updated server URL: ${normalizedUrl}`);
  console.log(`cleartext: ${cleartext ? "true" : "false"}`);
}

try {
  main();
} catch (err) {
  console.error(err.message || String(err));
  process.exit(1);
}
