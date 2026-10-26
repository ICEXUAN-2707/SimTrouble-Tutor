import { chromium } from "playwright-core";
import { verifyAuthenticationExpiryClearsState } from "./auth-flow.mjs";

const browserChannel = process.env.SIMTROUBLE_BROWSER_CHANNEL ?? "bundled";
const launchOptions = { headless: true };
if (browserChannel !== "bundled") launchOptions.channel = browserChannel;
const browser = await chromium.launch(launchOptions);
try {
  await verifyAuthenticationExpiryClearsState(
    browser,
    process.env.SIMTROUBLE_URL ?? "http://127.0.0.1:5174",
  );
  console.log("Targeted auth-expiry E2E passed.");
} finally {
  await browser.close();
}
