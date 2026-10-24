import assert from "node:assert/strict";
import { chromium } from "playwright-core";
import { registerAndEnter, verifyAuthenticationFlow } from "./auth-flow.mjs";
import { verifyTutorDeliveryScenarios } from "./tutor-scenarios.mjs";
import { verifyLearningFlow } from "./learning-flow.mjs";
import {
  verifyAssessmentScenarios,
  verifyDiagnosisErrors,
  verifyDiagnosisReportFlow,
  verifyResponsiveDiagnosisFlows,
} from "./diagnosis-report-flow.mjs";

const browserChannel = process.env.SIMTROUBLE_BROWSER_CHANNEL ?? "bundled";
const launchOptions = { headless: true };
if (browserChannel !== "bundled") launchOptions.channel = browserChannel;

const browser = await chromium.launch(launchOptions);
const baseUrl = process.env.SIMTROUBLE_URL ?? "http://127.0.0.1:5174";

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await registerAndEnter(page, baseUrl, "main");
  await page.locator("#tutor-status").filter({ hasText: "可用" }).waitFor({ state: "attached" });
  assert.equal(await page.locator("#case-state").textContent(), "准备就绪");
  assert.equal(await page.locator("#fault-callout").isHidden(), true);

  await page.locator("#play-button").click();
  await page.waitForTimeout(150);
  await page.locator("#play-button").click();
  assert.equal(await page.locator("#play-button").textContent(), "播放");
  await page.locator("#play-button").click();
  await page.locator("#case-state").filter({ hasText: "尝试抓取" }).waitFor({ state: "attached", timeout: 10_000 });
  await page.waitForFunction(() => window.__SIMTROUBLE_INSPECT__().endEffectorDistance < 0.01);
  const grasp = await page.evaluate(() => window.__SIMTROUBLE_INSPECT__());
  assert.equal(grasp.objectAttached, false);
  assert.ok(grasp.endEffectorDistance < 0.01, `grasp distance was ${grasp.endEffectorDistance}`);
  await page.locator("#case-state").filter({ hasText: "发现异常" }).waitFor({ state: "attached", timeout: 10_000 });
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
  assert.equal(await page.locator("#case-state").textContent(), "准备就绪");
  assert.equal(await page.locator("#fault-callout").isHidden(), true);
  await page.locator("[data-tool='pan']").click();
  assert.equal(await page.locator("[data-tool='pan']").getAttribute("class"), "tool active");
  assert.equal(await page.locator("[data-tool='orbit']").getAttribute("class"), "tool");
  await page.locator("[data-tool='fit']").click();
  await page.locator("#skip-button").click();
  assert.equal(await page.locator("#case-state").textContent(), "正在执行");
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
  await verifyLearningFlow(page);
  await verifyDiagnosisReportFlow(page);
  const visibleEnglish = await page.evaluate(() => {
    const visible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    };
    return [...document.querySelectorAll('body *')]
      .filter((element) => visible(element) && element.children.length === 0 && /[A-Za-z]{2,}/.test(element.textContent ?? ''))
      .map((element) => element.textContent.trim());
  });
  assert.deepEqual(visibleEnglish, []);
  assert.deepEqual(errors, []);
  await page.close();
  await verifyAuthenticationFlow(browser, baseUrl);
  await verifyTutorDeliveryScenarios(browser, baseUrl);
  await verifyAssessmentScenarios(browser, baseUrl);
  await verifyDiagnosisErrors(browser, baseUrl);
  await verifyResponsiveDiagnosisFlows(browser, baseUrl);

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await registerAndEnter(mobile, baseUrl, "mobile");
  assert.equal(await mobile.locator("#play-button").isVisible(), true);
  assert.equal(await mobile.locator("#cad-viewport canvas").isVisible(), true);
  const mobileWidth = await mobile.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  assert.equal(mobileWidth.scroll, mobileWidth.client);
  await mobile.close();
  console.log("E2E OK: play/pause/continue/visible failure/reset/skip continuity/view tools");
  console.log("E2E OK: Session, Evidence, Hypothesis flow and recoverable error");
  console.log("E2E OK: Diagnosis submit, report retry, five dimensions, and create-once guard");
  console.log("E2E OK: correct/partially_correct/incorrect/insufficient report rendering");
  console.log("E2E OK: Diagnosis 409/422 error mapping preserves form and Session");
  console.log("E2E OK: complete Diagnosis/Report flow at 1280x720, 768x1024, and 390x844");
  console.log("E2E OK: Tutor LLM success and timeout/malformed/leakage fallback delivery");
  console.log("E2E OK: registration, logout, login, and identity restore boundary");
  console.log("E2E OK: 390px responsive viewport");
} finally {
  await browser.close();
}
