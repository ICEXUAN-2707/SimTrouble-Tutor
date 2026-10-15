import assert from "node:assert/strict";

export async function verifyTutorDeliveryScenarios(browser, baseUrl) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const scenarios = new Map([
    ["provider success", { mode: "llm", message: "请先选择一条证据，并说明它能排除什么。" }],
    ["provider timeout", { mode: "rule_fallback", message: "服务超时，已切换为规则引导。" }],
    ["malformed output", { mode: "rule_fallback", message: "输出无效，已切换为规则引导。" }],
    ["answer leakage", { mode: "rule_fallback", message: "内容未通过安全检查，已切换为规则引导。" }],
  ]);

  await page.route("**/api/v0.4/sessions/*/tutor", async (route) => {
    const body = route.request().postDataJSON();
    const scenario = scenarios.get(body.message);
    assert.ok(scenario, `unexpected Tutor scenario: ${body.message}`);
    const sessionId = route.request().url().match(/\/sessions\/([^/]+)\/tutor/)?.[1];
    assert.ok(sessionId);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        tutor: {
          contract_version: "0.4.0",
          intent: "question",
          message: scenario.message,
          hint_level: 0,
          suggested_action: "inspect_evidence",
        },
        session: {
          contract_version: "0.4.0",
          session_id: sessionId,
          case_public_state: {
            evidence_options: [
              { id: "E01", type: "gripper_state" },
              { id: "E02", type: "object_pose" },
              { id: "E03", type: "target_pose" },
            ],
          },
          public_stage: "READY",
          released_evidence: [],
          current_hypothesis: null,
          hypotheses: [],
          allowed_actions: ["observe_scene", "inspect_evidence"],
        },
        tutor_mode: scenario.mode,
      }),
    });
  });

  try {
    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#tutor-status").filter({ hasText: "READY" }).waitFor();
    for (const [prompt, scenario] of scenarios) {
      await page.locator("#tutor-input").fill(prompt);
      await page.locator("#tutor-submit").click();
      const response = page.locator(`.tutor-message.tutor[data-mode="${scenario.mode}"]`, {
        hasText: scenario.message,
      });
      await response.waitFor();
    }
    assert.equal(await page.getByText("object_pose_mismatch").count(), 0);
  } finally {
    await page.close();
  }
}
