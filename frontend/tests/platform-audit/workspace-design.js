// Local isolated environment only. Does not use production credentials or external writes.
// prettier-ignore
async (page) => {
  const base = "http://127.0.0.1:3104",
    results = [],
    errors = [];
  page.setDefaultTimeout(8000);
  page.on("pageerror", (error) => errors.push(error.message));
  const test = async (name, fn) => {
    try {
      await fn();
      results.push({ name, status: "passed" });
    } catch (error) {
      results.push({
        name,
        status: "failed",
        reason: error.message.slice(0, 700),
      });
    }
  };
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(base + "/?module=home");
  await page.locator(".atelier-welcome").waitFor();
  await test("快捷键搜索与键盘进入功能", async () => {
    await page.keyboard.press("Control+k");
    const input = page.getByRole("combobox", { name: "搜索功能", exact: true });
    await input.fill("周报");
    await page.getByRole("option", { name: /工作手记/ }).waitFor();
    if ((await page.getByRole("option").count()) !== 1)
      throw new Error("search results mismatch");
    await input.press("Enter");
    await page.locator(".work-journal").waitFor();
    if (!page.url().includes("module=work_journal"))
      throw new Error("search did not navigate");
  });
  await test("最近访问按真实导航更新并刷新恢复", async () => {
    await page.getByRole("menuitem", { name: "工作台", exact: true }).click();
    await page
      .locator(".atelier-recent-grid")
      .getByRole("button", { name: /工作手记/ })
      .waitFor();
    await page.reload();
    await page
      .locator(".atelier-recent-grid")
      .getByRole("button", { name: /工作手记/ })
      .waitFor();
  });
  await test("搜索列表键盘滚动到最后一项仍可见", async () => {
    await page.keyboard.press("Control+k");
    const input = page.getByRole("combobox", { name: "搜索功能", exact: true });
    await input.fill("");
    for (let i = 0; i < 25; i++) await input.press("ArrowDown");
    const visible = await page.locator('.atelier-command-results').evaluate(list => {
      const row = list.querySelector('[aria-selected="true"]');
      return row && row.getBoundingClientRect().bottom <= list.getBoundingClientRect().bottom + 1 && row.getBoundingClientRect().top >= list.getBoundingClientRect().top;
    });
    if (!visible) throw new Error("keyboard-selected result outside the scroll viewport");
    await input.press("Escape");
  });
  await test("页面标题、导航定位与浏览器前进后退", async () => {
    await page.setViewportSize({ width: 1440, height: 800 });
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.getByRole("menuitem", { name: "工作手记", exact: true }).click();
    await page.waitForFunction(() => document.title === "工作手记 · Cling");
    if (await page.evaluate(() => scrollY) > 2) throw new Error("new module did not start at the top");
    await page.goBack();
    await page.locator(".atelier-welcome").waitFor();
    await page.goForward();
    await page.waitForFunction(() => document.title === "工作手记 · Cling");
    await page.getByRole("menuitem", { name: "工作台", exact: true }).click();
    await page.setViewportSize({ width: 1440, height: 1000 });
  });
  await test("分组搜索、上下选择、关闭恢复", async () => {
    await page
      .locator(".atelier-space").filter({has:page.getByRole("heading",{name:"测试中心",exact:true})}).getByRole("button", { name: "查看全部 4 项", exact: true })
      .click();
    const input = page.getByRole("combobox", { name: "搜索功能", exact: true });
    await input.waitFor();
    if ((await input.inputValue()) !== "测试中心")
      throw new Error("section filter missing");
    if ((await page.getByRole("option").count()) !== 4)
      throw new Error("section item count");
    await input.press("ArrowDown");
    const active = await input.getAttribute("aria-activedescendant");
    if (!active?.includes("circle_stats"))
      throw new Error("keyboard down not selected");
    await input.press("ArrowUp");
    await input.fill("没有这个功能");
    await page.getByText("还没找到这个功能", { exact: true }).waitFor();
    await input.press("Escape");
    await input.waitFor({ state: "hidden" });
    if (!page.url().includes("module=home"))
      throw new Error("escape changed route");
  });
  await test("损坏的最近访问记录不影响工作台", async () => {
    const old = await page.evaluate(() =>
      localStorage.getItem("cling:workspace:audit-admin:recent:v1"),
    );
    await page.evaluate(() =>
      localStorage.setItem("cling:workspace:audit-admin:recent:v1", "broken"),
    );
    await page.reload();
    await page.locator(".atelier-recent-empty").waitFor();
    if (old)
      await page.evaluate(
        (old) =>
          localStorage.setItem("cling:workspace:audit-admin:recent:v1", old),
        old,
      );
  });
  await test("手机导航自动关闭且页面不横向溢出", async () => {
    await page.setViewportSize({ width: 320, height: 844 });
    await page
      .getByRole("button", { name: "展开或收起导航", exact: true })
      .click();
    await page
      .locator(".platform-nav")
      .getByRole("menuitem", { name: "数据生成", exact: true })
      .click();
    await page.locator(".platform-nav").waitFor({ state: "hidden" });
    await page
      .getByRole("button", { name: /立即生成$/ })
      .waitFor();
    const sizing = await page.evaluate(() => ({
      width: innerWidth,
      document: document.documentElement.scrollWidth,
    }));
    if (sizing.document > sizing.width + 2)
      throw new Error(JSON.stringify(sizing));
  });
  await test("减少动态效果偏好与桌面折叠导航", async () => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(base + "/?module=home");
    await page.locator('.atelier-welcome').waitFor();
    if(await page.locator('.atelier-home .atelier-orbit').count())throw new Error('decorative hero returned');
    await page
      .getByRole("button", { name: "展开或收起导航", exact: true })
      .click();
    await page.locator(".ant-layout-sider-collapsed").waitFor();
    await page
      .getByRole("button", { name: "展开或收起导航", exact: true })
      .click();
    await page.emulateMedia({ reducedMotion: "no-preference" });
  });
  await test("受限账号搜索不泄露管理功能", async () => {
    const admin = await page.evaluate(
      () => sessionStorage.getItem("token") || localStorage.getItem("token"),
    );
    const name = "design_limited_" + Date.now();
    const response = await page.request.post(base + "/api/users", {
      headers: { Authorization: "Bearer " + admin },
      data: {
        username: name,
        password: "isolated-only",
        menu_permissions: ["data_generator"],
      },
    });
    const created = await response.json();
    if (!created.id) throw new Error("could not create isolated limited user");
    const login = await page.request.post(base + "/api/auth/login", {
      data: { username: name, password: "isolated-only" },
    });
    const token = (await login.json()).access_token;
    const context = await page.context().browser().newContext();
    try {
      const limited = await context.newPage();
      await limited.goto(base);
      await limited.evaluate((token) => {
        sessionStorage.setItem("token", token);
        localStorage.setItem("token", token);
      }, token);
      await limited.goto(base + "/?module=home");
      await limited.locator(".atelier-welcome").waitFor();
      await limited.keyboard.press("Control+k");
      await limited
        .getByRole("combobox", { name: "搜索功能", exact: true })
        .fill("用户管理");
      await limited.getByText("还没找到这个功能", { exact: true }).waitFor();
      if (
        await limited
          .getByRole("menuitem", { name: "用户管理", exact: true })
          .count()
      )
        throw new Error("admin menu leaked");
    } finally {
      await context.close();
      await page.request.delete(base + "/api/users/" + created.id, {
        headers: { Authorization: "Bearer " + admin },
      });
    }
  });
  return { results, errors };
}
