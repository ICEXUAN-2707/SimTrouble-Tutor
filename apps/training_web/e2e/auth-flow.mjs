import assert from "node:assert/strict";

function uniqueUsername(prefix = "e2e") {
  return `${prefix}${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`;
}

export async function registerAndEnter(page, baseUrl, prefix = "e2e") {
  const username = uniqueUsername(prefix);
  const password = "correct-horse";
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
