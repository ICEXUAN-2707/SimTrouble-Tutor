import assert from "node:assert/strict";
import { chromium } from "playwright-core";

const browserChannel = process.env.SIMTROUBLE_BROWSER_CHANNEL ?? "msedge";
const launchOptions = { headless: true };
if (browserChannel !== "bundled") launchOptions.channel = browserChannel;

const browser = await chromium.launch(launchOptions);
const baseUrl = process.env.SIMTROUBLE_URL ?? "http://127.0.0.1:5174";

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.locator("#loading-state").waitFor({ state: "hidden" });
  assert.equal(await page.locator("#case-state").textContent(), "READY");
  assert.equal(await page.locator("#fault-callout").isHidden(), true);

  await page.locator("#play-button").click();
  await page.waitForTimeout(150);
  await page.locator("#play-button").click();
  assert.equal(await page.locator("#play-button").textContent(), "PLAY");
  await page.locator("#play-button").click();
  await page.locator("#case-state").filter({ hasText: "FAILURE_OBSERVED" }).waitFor({ timeout: 10_000 });
  assert.equal(await page.locator("#fault-callout").isVisible(), true);
  assert.equal(await page.locator("#observations li").count(), 3);

  await page.locator("#reset-button").click();
  assert.equal(await page.locator("#case-state").textContent(), "READY");
  assert.equal(await page.locator("#fault-callout").isHidden(), true);
  await page.locator("[data-tool='pan']").click();
  assert.equal(await page.locator("[data-tool='pan']").getAttribute("class"), "tool active");
  assert.equal(await page.locator("[data-tool='orbit']").getAttribute("class"), "tool");
  await page.locator("[data-tool='fit']").click();
  await page.locator("#skip-button").click();
  assert.equal(await page.locator("#case-state").textContent(), "EXECUTING");
  assert.deepEqual(errors, []);

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto(baseUrl, { waitUntil: "networkidle" });
  await mobile.locator("#loading-state").waitFor({ state: "hidden" });
  assert.equal(await mobile.locator("#play-button").isVisible(), true);
  assert.equal(await mobile.locator("#cad-viewport canvas").isVisible(), true);
  const mobileWidth = await mobile.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  assert.equal(mobileWidth.scroll, mobileWidth.client);
  await mobile.close();
  console.log("E2E OK: play/pause/continue/failure/reset/skip/view tools");
  console.log("E2E OK: 390px responsive viewport");
} finally {
  await browser.close();
}
