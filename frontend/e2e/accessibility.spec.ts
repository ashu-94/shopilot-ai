import { writeFileSync } from "node:fs";
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("WCAG AA scan of public, customer and admin screens", async ({
  page,
  request,
}, testInfo) => {
  const findings: any[] = [];
  async function scan(path: string) {
    console.log("Scanning", path);
    await page.goto(path);
    await expect(page.locator("h1, main h2").first()).toBeVisible();
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    findings.push(
      ...result.violations.map((v) => ({
        path,
        id: v.id,
        impact: v.impact,
        nodes: v.nodes.map((n) => ({
          target: n.target,
          summary: n.failureSummary,
        })),
      })),
    );
  }
  for (const path of ["/", "/shop", "/products/product-001", "/login"])
    await scan(path);
  await page.goto("/login");
  await expect(
    page.getByRole("button", { name: "Shopper", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Email address").fill("alex@shopilot.demo");
  await page
    .getByLabel("Password", { exact: true })
    .fill("ShopPilot-demo-2026!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  for (const path of [
    "/missions",
    "/cart",
    "/checkout",
    "/orders",
    "/returns",
    "/support",
    "/approvals",
    "/compare",
  ])
    await scan(path);
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.goto("/login");
  await expect(
    page.getByRole("button", { name: "Shopper", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Email address").fill("admin@shopilot.demo");
  await page
    .getByLabel("Password", { exact: true })
    .fill("ShopPilot-demo-2026!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  for (const path of ["/procurement", "/operations", "/admin"])
    await scan(path);
  await testInfo.attach("axe-findings", {
    body: JSON.stringify(findings, null, 2),
    contentType: "application/json",
  });
  writeFileSync(
    "../verification/axe-findings.json",
    JSON.stringify(findings, null, 2),
  );
  console.log("Axe issue groups", findings.length);
  expect(findings).toEqual([]);
});

test("mobile keyboard navigation returns focus and has no horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/shop");
  await expect(page.locator("h1, main h2").first()).toBeVisible();
  const open = page.getByRole("button", { name: "Open navigation" });
  await open.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: "Close navigation" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(open).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("layout reflows at 200 percent equivalent viewport", async ({ page }) => {
  await page.setViewportSize({ width: 640, height: 450 });
  await page.goto("/shop");
  await expect(page.locator("h1, main h2").first()).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toBeVisible();
});
