import { chromium } from "playwright-core";
import { verifyAuthenticationExpiryClearsState } from "./auth-flow.mjs";

const browser = await chromium.launch({ headless: true });
try {
  await verifyAuthenticationExpiryClearsState(
    browser,
    process.env.SIMTROUBLE_URL ?? "http://127.0.0.1:5174",
  );
  console.log("Targeted auth-expiry E2E passed.");
} finally {
  await browser.close();
}
