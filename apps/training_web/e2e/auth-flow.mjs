import assert from "node:assert/strict";

function uniqueUsername(prefix = "e2e") {
  return `${prefix}${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`;
}

export async function registerAndEnter(page, baseUrl, prefix = "e2e") {
  const username = uniqueUsername(prefix);
  const password = "correct-horse-battery";
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.locator("#register-tab").click();
  await page.locator("#auth-display-name").fill("测试学员");
  await page.locator("#auth-username").fill(username);
  await page.locator("#auth-password").fill(password);
  await page.locator("#auth-submit").click();
  await page.locator("#app").waitFor({ state: "visible" });
  await page.locator("#loading-state").waitFor({ state: "hidden" });
  return { username, password };
}

export async function verifyAuthenticationFlow(browser, baseUrl) {
  const page = await browser.newPage({ viewport: { width: 1024, height: 800 } });
  try {
    const credentials = await registerAndEnter(page, baseUrl, "auth");
    assert.equal(await page.locator("#signed-user").textContent(), "测试学员");
    await page.locator("#logout-button").click();
    await page.locator("#auth-shell").waitFor({ state: "visible" });
    await page.locator("#auth-username").fill(credentials.username);
    await page.locator("#auth-password").fill(credentials.password);
    await page.locator("#auth-submit").click();
    await page.locator("#app").waitFor({ state: "visible" });
    assert.equal(await page.locator("#signed-user").textContent(), "测试学员");
  } finally {
    await page.close();
  }
}

export async function verifyAuthenticationExpiryClearsState(browser, baseUrl) {
  const context = await browser.newContext({ viewport: { width: 1024, height: 800 } });
  const page = await context.newPage();
  try {
    await registerAndEnter(page, baseUrl, "expired");
    await page.locator(".evidence-card").first().waitFor();
    await page.locator('[data-step="evidence"]').click();
    await page.locator("[data-evidence-id='E01']").click();
    await page.locator("#learning-progress").filter({ hasText: "1 / 3" }).waitFor();
    await page.locator('[data-step="hypothesis"]').click();
    await page.locator("#hypothesis-input").fill("仅属于已撤销身份的假设");
    const sessionId = await page.locator("#session-code").getAttribute("title");
    assert.ok(sessionId);

    const cookies = await context.cookies(baseUrl);
    const auth = cookies.find((cookie) => cookie.name === "simtrouble_auth");
    const csrf = cookies.find((cookie) => cookie.name === "simtrouble_csrf");
    assert.ok(auth);
    assert.ok(csrf);
    const revoked = await fetch(`${baseUrl}/api/v0.5/auth/logout`, {
      method: "POST",
      headers: {
        Cookie: `simtrouble_auth=${auth.value}; simtrouble_csrf=${csrf.value}`,
        "X-CSRF-Token": csrf.value,
      },
    });
    assert.equal(revoked.status, 204);

    const navigation = page.waitForEvent("framenavigated");
    await page.locator("#hypothesis-submit").click();
    await navigation;
    await page.locator("#auth-shell").waitFor({ state: "visible" });
    assert.equal(await page.locator("#app").isHidden(), true);
    assert.equal(await page.locator("#signed-user").textContent(), "");
    assert.equal(await page.locator("#session-code").textContent(), "尚未创建");
    assert.equal(await page.locator("#session-code").getAttribute("title"), null);
    assert.equal(await page.locator("#evidence-options").children().count(), 0);
    assert.equal(await page.locator("#hypothesis-input").inputValue(), "");
    assert.equal(await page.locator("#report-content").children().count(), 0);
    assert.equal(
      await page.evaluate(() => document.cookie.includes("simtrouble_csrf=")),
      false,
    );
  } finally {
    await context.close();
  }
}
