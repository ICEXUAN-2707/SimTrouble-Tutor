import assert from "node:assert/strict";
import { chromium } from "playwright-core";
import { verifyTutorDeliveryScenarios } from "./tutor-scenarios.mjs";

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
  await page.locator("#tutor-status").filter({ hasText: "READY" }).waitFor();
  assert.equal(await page.locator("#case-state").textContent(), "READY");
  assert.equal(await page.locator("#fault-callout").isHidden(), true);

  await page.locator("#play-button").click();
  await page.waitForTimeout(150);
  await page.locator("#play-button").click();
  assert.equal(await page.locator("#play-button").textContent(), "PLAY");
  await page.locator("#play-button").click();
  await page.locator("#case-state").filter({ hasText: "GRASP_ATTEMPT" }).waitFor({ timeout: 10_000 });
  await page.waitForFunction(() => window.__SIMTROUBLE_INSPECT__().endEffectorDistance < 0.01);
  const grasp = await page.evaluate(() => window.__SIMTROUBLE_INSPECT__());
  assert.equal(grasp.objectAttached, false);
  assert.ok(grasp.endEffectorDistance < 0.01, `grasp distance was ${grasp.endEffectorDistance}`);
  await page.locator("#case-state").filter({ hasText: "FAILURE_OBSERVED" }).waitFor({ timeout: 10_000 });
  await page.waitForFunction(() => window.__SIMTROUBLE_INSPECT__().endEffectorDistance > 0.9);
  const failure = await page.evaluate(() => window.__SIMTROUBLE_INSPECT__());
  assert.equal(failure.objectAttached, false);
  assert.ok(failure.endEffectorDistance > 0.9, `failure distance was ${failure.endEffectorDistance}`);
  assert.deepEqual(
    failure.workpiecePosition.map((value) => Number(value.toFixed(3))),
    [1.3, 0.34, 0.55],
  );
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
  const skipped = await page.evaluate(() => window.__SIMTROUBLE_INSPECT__());
  await page.locator("#play-button").click();
  await page.waitForTimeout(50);
  const resumed = await page.evaluate(() => window.__SIMTROUBLE_INSPECT__());
  const resumeDisplacement = Math.hypot(...resumed.endEffectorPosition.map(
    (value, index) => value - skipped.endEffectorPosition[index],
  ));
  assert.equal(resumed.stepId, "descend");
  assert.ok(resumed.endEffectorPosition[1] <= skipped.endEffectorPosition[1] + 0.02);
  assert.ok(resumeDisplacement < 0.25, `skip/play pose rolled back by ${resumeDisplacement}`);
  assert.deepEqual(errors, []);
  await page.close();
  await verifyTutorDeliveryScenarios(browser, baseUrl);

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
  console.log("E2E OK: play/pause/continue/visible failure/reset/skip continuity/view tools");
  console.log("E2E OK: Tutor LLM success and timeout/malformed/leakage fallback delivery");
  console.log("E2E OK: 390px responsive viewport");
} finally {
  await browser.close();
}
