# Demo walkthrough

Use local seeded accounts from the [README](../README.md#demo-accounts). All products, charges and shipments are synthetic.

## 1. Plan a setup

Sign in as Alex. Open Mission planner and enter: **Build a home office for Python development under ₹1,50,000 with a laptop, monitor, chair, keyboard, mouse and UPS.** Follow progress, inspect the complete bundle and expand its supporting evidence. Try an impossible budget to see an explicit infeasibility response.

## 2. Review a purchase

Add products to the cart, open checkout and enter a demo delivery address. Submission creates a workflow, not an immediate purchase. Open Approval center, review quantities and amount, and use the indicated authorized reviewer. Once approved, inspect the completed order and simulated tracking.

## 3. Return one item

Open Returns, select your eligible order and choose product quantities. Describe the reason and request refund or replacement. Review the selected lines before approval. A partial return leaves the remaining quantity eligible; replacement requires available stock. Damaged goods do not automatically return to sellable inventory.

## 4. Purchase for a business

Sign in as the business user and open Procurement. Supply organization, cost center, billing/delivery addresses, contact email, requested date and mock payment terms. Submit a team laptop request, then switch to an independent manager to review. Inspect the JSON purchase order after completion.

## 5. Observe and recover

An administrator can inspect operations, specialist records and recovery controls. Recovery actions require a reason. Restore failed dependencies before replaying work; never delete pending financial or outbox rows to clear a dashboard.

## 6. Explore failure behavior

- Reject an approval: no transaction should run.
- Choose simulated payment decline: no order or stock deduction should commit.
- Restart while awaiting approval: the saved workflow should resume after a valid decision.
- Resubmit the same request key: replay should not duplicate financial effects.

Automated equivalents and their verification limits are in [TESTING.md](TESTING.md) and [VERIFICATION.md](VERIFICATION.md).
