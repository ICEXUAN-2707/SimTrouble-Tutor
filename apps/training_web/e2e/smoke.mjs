import assert from "node:assert/strict";
import { chromium } from "playwright-core";
import { verifyTutorDeliveryScenarios } from "./tutor-scenarios.mjs";
import { verifyLearningFlow } from "./learning-flow.mjs";

const browser = await chromium.launch({
  channel: "msedge",
  headless: true,
});
const baseUrl = process.env.SIMTROUBLE_URL ?? "http://127.0.0.1:5174";

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.locator("#loading-state").waitFor({ state: "hidden" });
  await page.locator("#tutor-status").filter({ hasText: "READY" }).waitFor();
  assert.equal(await page.locator("#case-state").textContent(), "READY");
  assert.equal(await page.locator("#fault-callout").isHidden(), true);

  await page.locator("#play-button").click();
  await page.locator("#case-state").filter({ hasText: "FAILURE_OBSERVED" }).waitFor({ timeout: 10_000 });
  assert.equal(await page.locator("#fault-callout").isVisible(), true);
  assert.equal(await page.locator("#observations li").count(), 3);

  await page.locator("#reset-button").click();
  assert.equal(await page.locator("#case-state").textContent(), "READY");
  assert.equal(await page.locator("#fault-callout").isHidden(), true);
  await verifyLearningFlow(page);
  assert.deepEqual(errors, []);
  await verifyTutorDeliveryScenarios(browser, baseUrl);

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await mobile.locator("#loading-state").waitFor({ state: "hidden" });
  assert.equal(await mobile.locator("#play-button").isVisible(), true);
  assert.equal(await mobile.locator("#cad-viewport canvas").isVisible(), true);
  const mobileWidth = await mobile.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  assert.equal(mobileWidth.scroll, mobileWidth.client);
  await mobile.close();
  console.log("E2E OK: READY -> FAILURE_OBSERVED -> RESET");
  console.log("E2E OK: Session, Evidence, Hypothesis flow and recoverable error");
  console.log("E2E OK: Tutor LLM success and timeout/malformed/leakage fallback delivery");
  console.log("E2E OK: 390px responsive viewport");
} finally {
  await browser.close();
}
