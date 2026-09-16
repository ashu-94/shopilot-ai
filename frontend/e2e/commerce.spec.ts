import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("item return can be reviewed and approved through the UI", async ({
  page,
}) => {
  test.setTimeout(60000);
  page.setDefaultTimeout(10000);
  const response = await page.request.post("/api/auth/login", {
    data: { email: "alex@shopilot.demo", password: "ShopPilot-demo-2026!" },
  });
  expect(response.ok()).toBeTruthy();
  const token = (await response.json()).access_token;
  const headers = {
    Authorization: `Bearer ${token}`,
    "Idempotency-Key": crypto.randomUUID(),
  };
  await page.request.put("/api/cart", {
    headers,
    data: { items: [{ product_id: "product-010", quantity: 2 }] },
  });
  const checkout = await page.request.post("/api/checkout", {
    headers,
    data: { address: "42 Test Avenue, Bengaluru 560001" },
  });
  const id = (await checkout.json()).id;
  await expect
    .poll(
      async () =>
        (
          await (
            await page.request.get(`/api/executions/${id}`, { headers })
          ).json()
        ).status,
    )
    .toBe("awaiting_approval");
  const approvals = await (
    await page.request.get("/api/approvals", { headers })
  ).json();
  const approval = approvals.find((a: any) => a.execution_id === id);
  await page.request.post(`/api/approvals/${approval.id}/decision`, {
    headers,
    data: { decision: "approve" },
  });
  await expect
    .poll(
      async () =>
        (
          await (
            await page.request.get(`/api/executions/${id}`, { headers })
          ).json()
        ).status,
    )
    .toBe("completed");
  const order = (
    await (await page.request.get(`/api/executions/${id}`, { headers })).json()
  ).result.order;
  await page.goto("/returns");
  await page
    .getByRole("combobox", { name: "Order", exact: true })
    .selectOption(order.id);
  await page.getByRole("spinbutton").fill("1");
  await page
    .getByRole("combobox", { name: "Preferred resolution" })
    .selectOption("refund");
  const returnResponse = page.waitForResponse(
    (r) => r.url().endsWith("/api/returns") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Submit for review" }).click();
  const returnId = (await (await returnResponse).json()).id;
  await expect(
    page.getByText("Waiting for human review", { exact: true }),
  ).toBeVisible({ timeout: 15000 });
  await page.goto("/approvals");
  const card = page.getByTestId(`approval-${returnId}`);
  await card.getByText("Review exact items and quantities").click();
  await expect(
    card.getByText(`${order.items[0].product.name} × 1`, { exact: true }),
  ).toBeVisible();
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    scan.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.failureSummary),
    })),
  ).toEqual([]);
  await card.getByRole("button", { name: "Approve", exact: true }).click();
  await expect
    .poll(
      async () =>
        (
          await (
            await page.request.get(`/api/orders/${order.id}`, { headers })
          ).json()
        ).status,
    )
    .toBe("partially_returned");
  const updated = await (
    await page.request.get(`/api/orders/${order.id}`, { headers })
  ).json();
  expect(updated.items[0].returnable_quantity).toBe(1);
});
