import assert from "node:assert/strict";

export async function verifyLearningFlow(page) {
  const originalSessionId = await page.locator("#session-code").getAttribute("title");
  assert.ok(originalSessionId);
  assert.equal(await page.locator(".evidence-card").count(), 3);
  assert.equal(await page.locator(".evidence-card .evidence-locked").count(), 3);
  assert.equal(await page.locator("#hypothesis-input").isDisabled(), true);

  await page.locator('[data-step="evidence"]').click();
  await page.locator("[data-evidence-id='E01']").click();
  await page.locator('[data-step="evidence"]').click();
  await page.locator("[data-evidence-id='E01']").filter({ hasText: "收起证据" }).waitFor();
  assert.equal(await page.locator("#learning-progress").textContent(), "1 / 3 条证据");
  await page.locator('[data-step="evidence"]').click();
  assert.equal(await page.locator("[data-evidence-id='E02']").locator("xpath=..").getByText("测量值未释放").count(), 1);
  assert.equal(await page.locator("#hypothesis-input").isEnabled(), true);

  await page.locator('[data-step="hypothesis"]').click();
  await page.locator("#hypothesis-input").fill("夹爪未能保持工件。");
  await page.locator("#hypothesis-submit").click();
  await page.locator("#hypothesis-history li").filter({ hasText: "夹爪未能保持工件。" }).waitFor({ state: "attached" });
  assert.equal(await page.locator("#hypothesis-history li").count(), 1);
  assert.equal(await page.locator("#hypothesis-submit").textContent(), "修正假设");

  await page.locator('[data-step="evidence"]').click();
  await page.locator("[data-evidence-id='E02']").click();
  await page.locator('[data-step="evidence"]').click();
  await page.locator("[data-evidence-id='E02']").filter({ hasText: "收起证据" }).waitFor();
  const e02 = page.locator("[data-evidence-id='E02']").locator("xpath=..");
  assert.equal(await e02.getByText("70", { exact: true }).count(), 2);
  assert.equal(await page.locator("#learning-progress").textContent(), "2 / 3 条证据");

  await page.locator('[data-step="hypothesis"]').click();
  await page.locator("#hypothesis-input").fill("E02 显示物体 X 位姿相对计划偏移。");
  await page.locator("#hypothesis-submit").click();
  await page.locator("#hypothesis-history li").filter({ hasText: "E02 显示物体 X 位姿相对计划偏移。" }).waitFor({ state: "attached" });
  assert.equal(await page.locator("#hypothesis-history li").count(), 2);
  assert.equal(await page.locator("#session-stage").textContent(), "调查中");

  await page.route("**/api/v0.4/sessions/*/evidence", async (route) => {
    const body = route.request().postDataJSON();
    if (body.evidence_id !== "E03") return route.continue();
    await route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({ detail: "invalid_session_stage" }),
    });
  });
  await page.locator('[data-step="evidence"]').click();
  await page.locator("[data-evidence-id='E03']").click();
  await page.locator("#learning-error").filter({ hasText: "当前学习阶段不允许此操作" }).waitFor();
  assert.equal(await page.locator("#learning-progress").textContent(), "2 / 3 条证据");
  assert.equal(await page.locator("#hypothesis-history li").count(), 2);
  assert.equal(await page.locator("#session-code").getAttribute("title"), originalSessionId);
  await page.locator('[data-step="evidence"]').click();
  assert.equal(await page.locator("[data-evidence-id='E03']").isEnabled(), true);
  await page.unroute("**/api/v0.4/sessions/*/evidence");
}
