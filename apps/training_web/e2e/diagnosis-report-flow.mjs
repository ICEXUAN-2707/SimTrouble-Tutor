import assert from "node:assert/strict";
import { registerAndEnter } from "./auth-flow.mjs";

async function prepareDiagnosis(page, baseUrl) {
  await registerAndEnter(page, baseUrl, "diagnosis");
  await page.locator("#tutor-status").filter({ hasText: "可用" }).waitFor({ state: "attached" });
  await page.locator('[data-step="evidence"]').click();
  await page.locator("[data-evidence-id='E01']").click();
  await page.locator('[data-step="evidence"]').click();
  await page.locator("[data-evidence-id='E01']").filter({ hasText: "收起证据" }).waitFor();
  await page.locator('[data-step="hypothesis"]').click();
  await page.locator("#hypothesis-input").fill("夹爪没有保持工件。");
  await page.locator("#hypothesis-submit").click();
  await page.locator("#hypothesis-history li").filter({ hasText: "夹爪没有保持工件。" }).waitFor({ state: "attached" });
  await page.locator('[data-step="evidence"]').click();
  await page.locator("[data-evidence-id='E02']").click();
  await page.locator('[data-step="evidence"]').click();
  await page.locator("[data-evidence-id='E02']").filter({ hasText: "收起证据" }).waitFor();
  await page.locator('[data-step="hypothesis"]').click();
  await page.locator("#hypothesis-input").fill("物体 X 位姿与计划位置不一致。");
  await page.locator("#hypothesis-submit").click();
  await page.locator("#diagnosis-status").filter({ hasText: "可提交" }).waitFor({ state: "attached" });
}

async function fillDiagnosis(page, type, evidenceIds) {
  await page.locator('[data-step="diagnosis"]').click();
  await page.locator('[data-step="diagnosis"]').click();
  await page.locator("#diagnosis-type").selectOption(type);
  await page.locator("#diagnosis-reasoning").fill("已释放证据支持该诊断，且能够排除其他候选原因。");
  for (const evidenceId of evidenceIds) {
    await page.locator(`#diagnosis-citations input[value='${evidenceId}']`).check();
  }
  assert.equal(await page.locator("#diagnosis-submit").isEnabled(), true);
}

function assertNoZeroSafety(page) {
  const safety = page.locator(".dimension-card[data-dimension='safety']");
  return safety.filter({ hasText: "未评估" }).waitFor().then(async () => {
    const snapshot = await safety.evaluate((node) => ({
      status: node.getAttribute("data-status"),
      text: node.textContent,
    }));
    assert.equal(snapshot.status, "not_assessed");
    assert.equal(snapshot.text.includes("0 / 100"), false);
  });
}

export async function verifyDiagnosisReportFlow(page) {
  const sessionId = await page.locator("#session-code").getAttribute("title");
  assert.ok(sessionId);
  assert.equal(await page.locator("#diagnosis-status").textContent(), "可提交");
  assert.equal(await page.locator("#diagnosis-citations input").count(), 2);
  assert.equal(await page.locator("#diagnosis-citations input[value='E03']").count(), 0);
  assert.equal(await page.locator("#diagnosis-submit").isDisabled(), true);

  let diagnosisRequests = 0;
  const countDiagnosis = (request) => {
    if (request.method() === "POST" && request.url().endsWith("/diagnosis")) diagnosisRequests += 1;
  };
  page.on("request", countDiagnosis);

  let reportRequests = 0;
  await page.route("**/api/v0.5/sessions/*/report", async (route) => {
    reportRequests += 1;
    if (reportRequests === 1) {
      await route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({ detail: "report_not_ready" }),
      });
      return;
    }
    await route.continue();
  });

  await fillDiagnosis(page, "object_pose_mismatch", ["E01", "E02"]);
  await page.locator("#diagnosis-submit").click();
  await page.locator("#report-retry").waitFor({ state: "visible" });
  assert.equal(await page.locator("#session-stage").textContent(), "已提交");
  assert.equal(await page.locator("#hypothesis-history li").count(), 2);
  assert.equal(await page.locator("#diagnosis-submit").isDisabled(), true);

  await page.locator("#report-retry").click();
  await page.locator(".report-hero[data-assessment='correct']").waitFor();
  assert.equal(await page.locator("[data-testid='overall-score']").textContent(), "91.75");
  assert.equal(await page.locator("[data-testid='report-coverage']").textContent(), "80%");
  assert.equal(await page.locator("[data-testid='report-tutor-mode']").textContent(), "基础引导");
  await assertNoZeroSafety(page);
  await page.locator("#session-stage").filter({ hasText: "已评估" }).waitFor({ state: "attached" });
  assert.equal(await page.locator("#session-code").getAttribute("title"), sessionId);
  assert.equal(reportRequests, 2);

  await page.locator("#diagnosis-submit").evaluate((button) => button.click());
  await page.waitForTimeout(100);
  assert.equal(diagnosisRequests, 1);
  page.off("request", countDiagnosis);
  await page.unroute("**/api/v0.5/sessions/*/report");
}

export async function verifyAssessmentScenarios(browser, baseUrl) {
  const scenarios = [
    { type: "object_pose_mismatch", evidence: ["E02"], assessment: "insufficient" },
    { type: "grasp_failure", evidence: ["E01"], assessment: "partially_correct" },
    { type: "obstacle_collision_risk", evidence: ["E01"], assessment: "incorrect" },
  ];
  for (const scenario of scenarios) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    try {
      await prepareDiagnosis(page, baseUrl);
      await fillDiagnosis(page, scenario.type, scenario.evidence);
      await page.locator("#diagnosis-submit").click();
      await page.locator(`.report-hero[data-assessment='${scenario.assessment}']`).waitFor();
      await assertNoZeroSafety(page);
      assert.equal(await page.locator("#diagnosis-submit").isDisabled(), true);
    } finally {
      await page.close();
    }
  }
}

export async function verifyDiagnosisErrors(browser, baseUrl) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const failures = [
    { status: 422, detail: "invalid_evidence_reference", text: "诊断引用包含未释放的证据" },
    { status: 409, detail: "invalid_session_stage", text: "当前学习阶段不允许提交诊断" },
    { status: 409, detail: "diagnosis_already_submitted", text: "本会话已提交过诊断" },
  ];
  let attempt = 0;
  try {
    await prepareDiagnosis(page, baseUrl);
    const sessionId = await page.locator("#session-code").getAttribute("title");
    await page.route("**/api/v0.5/sessions/*/diagnosis", async (route) => {
      const body = route.request().postDataJSON();
      assert.deepEqual(body.cited_evidence_ids, ["E01"]);
      const failure = failures[attempt];
      attempt += 1;
      await route.fulfill({
        status: failure.status,
        contentType: "application/json",
        body: JSON.stringify({ detail: failure.detail }),
      });
    });

    assert.equal(await page.locator("#diagnosis-submit").isDisabled(), true);
    await page.locator('[data-step="diagnosis"]').click();
    await page.locator("#diagnosis-type").selectOption("object_pose_mismatch");
    assert.equal(await page.locator("#diagnosis-submit").isDisabled(), true);
    await page.locator("#diagnosis-reasoning").fill("保留此理由以验证错误恢复。");
    assert.equal(await page.locator("#diagnosis-submit").isDisabled(), true);
    await page.locator("#diagnosis-citations input[value='E01']").check();
    await page.locator("#diagnosis-citations").evaluate((container) => {
      const injected = document.createElement("input");
      injected.type = "checkbox";
      injected.value = "E03";
      injected.checked = true;
      container.append(injected);
    });

    for (const failure of failures) {
      await page.locator("#diagnosis-submit").click();
      await page.locator("#diagnosis-error").filter({ hasText: failure.text }).waitFor();
      assert.equal(await page.locator("#diagnosis-reasoning").inputValue(), "保留此理由以验证错误恢复。");
      assert.equal(await page.locator("#diagnosis-citations input[value='E01']").isChecked(), true);
      assert.equal(await page.locator("#hypothesis-history li").count(), 2);
      assert.equal(await page.locator("#session-code").getAttribute("title"), sessionId);
      assert.equal(await page.locator("#diagnosis-submit").isEnabled(), true);
    }
    assert.equal(attempt, failures.length);
  } finally {
    await page.close();
  }
}

export async function verifyResponsiveDiagnosisFlows(browser, baseUrl) {
  const viewports = [
    { width: 1280, height: 720 },
    { width: 768, height: 1024 },
    { width: 390, height: 844 },
  ];
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport });
    try {
      await prepareDiagnosis(page, baseUrl);
      await fillDiagnosis(page, "object_pose_mismatch", ["E01", "E02"]);
      await page.locator("#diagnosis-submit").click();
      await page.locator(".report-hero[data-assessment='correct']").waitFor();
      await assertNoZeroSafety(page);
      const layout = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        reportWidth: document.getElementById("report-panel")?.getBoundingClientRect().width ?? 0,
      }));
      assert.equal(layout.scrollWidth, layout.clientWidth);
      assert.ok(layout.reportWidth > 0 && layout.reportWidth <= viewport.width);
    } finally {
      await page.close();
    }
  }
}
