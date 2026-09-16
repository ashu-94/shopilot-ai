import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  CreditCard,
  Minus,
  Package,
  Plus,
  ShieldCheck,
  Trash2,
  Truck,
  Undo2,
} from "lucide-react";
import { api, money, post } from "../api";
import {
  Empty,
  ErrorState,
  Loading,
  PageHeading,
  ProductArt,
  Status,
} from "../components";
import { useNotice, useSession } from "../store";
import { ExecutionView } from "./Mission";
import type { Cart as CartType, Execution, Order } from "../types";

export function CartPage({ checkout = false }: { checkout?: boolean }) {
  const user = useSession((s) => s.user),
    client = useQueryClient(),
    notice = useNotice();
  const {
    data: cart,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["cart"],
    queryFn: () => api<CartType>("/cart"),
    enabled: !!user,
  });
  const [address, setAddress] = useState(
      "42 Demo Avenue, Bengaluru, Karnataka 560001",
    ),
    [failure, setFailure] = useState(false),
    [execution, setExecution] = useState<string | null>(null);
  const edit = useMutation({
    mutationFn: ({ id, quantity }: { id: string; quantity: number }) =>
      api("/cart", {
        method: "PUT",
        body: JSON.stringify({
          items: cart?.items
            .map((i) => ({
              product_id: i.product_id,
              quantity: i.product_id === id ? quantity : i.quantity,
            }))
            .filter((i) => i.quantity > 0),
        }),
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["cart"] }),
    onError: (e: Error) => notice.show(e.message),
  });
  const buy = useMutation({
    mutationFn: () =>
      post<Execution>(
        "/checkout",
        { address, simulate_failure: failure },
        true,
      ),
    onSuccess: (r) => setExecution(r.id),
  });
  if (!user)
    return (
      <Empty
        title="Your cart is waiting."
        text="Sign in to save products and review a purchase."
        to="/login"
        label="Sign in"
      />
    );
  return (
    <>
      <PageHeading
        eyebrow="A FEW GOOD CHOICES"
        title={
          checkout
            ? "A final look before the go-ahead."
            : "Your next chapter, in a cart."
        }
        description="Prices and inventory are rechecked before every transaction."
      />
      {execution ? (
        <ExecutionView id={execution} />
      ) : isLoading ? (
        <Loading />
      ) : error ? (
        <ErrorState error={error} />
      ) : !cart?.items.length ? (
        <Empty
          title="Room for something great."
          text="Start a mission or explore the collection to fill your cart."
          to="/shop"
          label="Explore products"
        />
      ) : (
        <div className="cart-layout">
          <div>
            <div className="cart-lines panel">
              {cart.items.map((i) => (
                <div className="cart-line" key={i.product_id}>
                  <ProductArt product={i.product} />
                  <div>
                    <span className="eyebrow">{i.product.category}</span>
                    <Link to={`/products/${i.product_id}`}>
                      <h3>{i.product.name}</h3>
                    </Link>
                    <p>{money(i.unit_price)} per unit</p>
                    <div className="quantity">
                      <button
                        disabled={edit.isPending}
                        aria-label={`Decrease ${i.product.name} quantity`}
                        onClick={() =>
                          edit.mutate({
                            id: i.product_id,
                            quantity: i.quantity - 1,
                          })
                        }
                      >
                        <Minus size={14} />
                      </button>
                      <span>{i.quantity}</span>
                      <button
                        disabled={edit.isPending}
                        aria-label={`Increase ${i.product.name} quantity`}
                        onClick={() =>
                          edit.mutate({
                            id: i.product_id,
                            quantity: i.quantity + 1,
                          })
                        }
                      >
                        <Plus size={14} />
                      </button>
                    </div>
                  </div>
                  <div className="cart-line-total">
                    <strong>{money(i.unit_price * i.quantity)}</strong>
                    <button
                      className="icon-button"
                      aria-label={`Remove ${i.product.name}`}
                      onClick={() =>
                        edit.mutate({ id: i.product_id, quantity: 0 })
                      }
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            {checkout && (
              <section className="panel checkout-details">
                <h2>Where should it go?</h2>
                <label>
                  Delivery address
                  <textarea
                    rows={3}
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    minLength={12}
                  />
                </label>
                <div className="payment-method">
                  <CreditCard />
                  <div>
                    <strong>ShopPilot safe mock payment</strong>
                    <p>No card details. No real money. Fully simulated.</p>
                  </div>
                  <CheckCircle2 size={20} />
                </div>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={failure}
                    onChange={(e) => setFailure(e.target.checked)}
                  />
                  Simulate a declined payment to test rollback
                </label>
              </section>
            )}
          </div>
          <aside className="order-summary panel">
            <h2>Your plan, in numbers.</h2>
            <dl>
              <div>
                <dt>Subtotal</dt>
                <dd>{money(cart.subtotal)}</dd>
              </div>
              <div className="green">
                <dt>Savings {cart.coupon && <small>{cart.coupon}</small>}</dt>
                <dd>−{money(cart.discount)}</dd>
              </div>
              <div>
                <dt>Delivery</dt>
                <dd>Complimentary</dd>
              </div>
              <div className="summary-total">
                <dt>Total</dt>
                <dd>{money(cart.total)}</dd>
              </div>
            </dl>
            {checkout ? (
              <button
                className="button primary wide"
                disabled={buy.isPending || address.length < 12}
                onClick={() => buy.mutate()}
              >
                {buy.isPending ? "Preparing review…" : "Continue to approval"}
                <ArrowRight size={17} />
              </button>
            ) : (
              <Link to="/checkout" className="button primary wide">
                Review checkout
                <ArrowRight size={17} />
              </Link>
            )}
            {buy.error && <ErrorState error={buy.error} />}
            <p className="summary-note">
              <ShieldCheck size={16} />
              The next step creates a review request. Payment happens only after
              approval.
            </p>
            <Link to="/shop" className="continue-link">
              Keep exploring
              <ChevronRight size={15} />
            </Link>
          </aside>
        </div>
      )}
    </>
  );
}
export function Orders() {
  const user = useSession((s) => s.user);
  const {
    data = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ["orders"],
    queryFn: () => api<Order[]>("/orders"),
    enabled: !!user,
    refetchInterval: 5000,
  });
  return (
    <>
      <PageHeading
        eyebrow="ON TO WHAT’S NEXT"
        title="Good things, on their way."
        description="Your purchases, shipment details and next steps in one place."
      />
      {!user ? (
        <Empty
          title="Your orders live here."
          text="Sign in to see your purchase history."
          to="/login"
          label="Sign in"
        />
      ) : isLoading ? (
        <Loading />
      ) : error ? (
        <ErrorState error={error} />
      ) : !data.length ? (
        <Empty
          title="The start of something good."
          text="Complete a mission and approve checkout to place your first demo order."
          to="/missions"
        />
      ) : (
        <div className="orders-list">
          {data.map((order) => (
            <article key={order.id} className="panel order-card">
              <div className="order-card-top">
                <span>
                  <strong>{order.number}</strong>
                  <small>
                    {new Date(order.created_at * 1000).toLocaleDateString(
                      "en-IN",
                      { day: "numeric", month: "long", year: "numeric" },
                    )}
                  </small>
                </span>
                <Status value={order.status} />
              </div>
              <div className="order-card-products">
                {order.items.slice(0, 4).map((i) => (
                  <ProductArt key={i.product_id} product={i.product} />
                ))}
                <div>
                  <h3>
                    {order.items.length === 1
                      ? order.items[0].product.name
                      : `Your ${order.items.length}-product setup`}
                  </h3>
                  <p>
                    {order.items.reduce((n, i) => n + i.quantity, 0)} items ·
                    Safe mock payment
                  </p>
                  <strong>{money(order.total)}</strong>
                </div>
              </div>
              <div className="order-card-bottom">
                <span>
                  <Truck size={16} />
                  {order.shipments[0]?.tracking_code || "Shipment preparing"}
                </span>
                <Link
                  className="button secondary small"
                  to={`/orders/${order.id}`}
                >
                  View order
                  <ArrowRight size={16} />
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
export function OrderDetail() {
  const { id } = useParams(),
    [execution, setExecution] = useState<string | null>(null);
  const notice = useNotice();
  async function downloadPurchaseOrder() {
    try {
      const document = await api<Record<string, unknown>>(
        `/orders/${id}/purchase-order`,
      );
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(document, null, 2)], {
          type: "application/json",
        }),
      );
      const link = window.document.createElement("a");
      link.href = url;
      link.download = `PO-${id?.slice(0, 12)}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      notice.show((e as Error).message);
    }
  }
  const {
    data: order,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["order", id],
    queryFn: () => api<Order>(`/orders/${id}`),
    refetchInterval: 3000,
  });
  const cancel = useMutation({
    mutationFn: () => post<Execution>(`/orders/${id}/cancel`, {}, true),
    onSuccess: (e) => setExecution(e.id),
  });
  if (isLoading) return <Loading />;
  if (error) return <ErrorState error={error} />;
  if (!order) return null;
  return (
    <>
      <Link className="back-link" to="/orders">
        ← All orders
      </Link>
      <PageHeading
        eyebrow="YOUR PURCHASE"
        title={order.number}
        description={`Placed ${new Date(order.created_at * 1000).toLocaleString()}`}
        action={<Status value={order.status} />}
      />
      {execution && <ExecutionView id={execution} />}
      <div className="detail-lower">
        <section className="panel tracking-panel">
          <h2>Follow the next steps.</h2>
          <p>
            Local shipping simulation. Status does not imply a real delivery.
          </p>
          {!["cancelled", "refunded", "replacement_sent"].includes(
            order.status,
          ) ? (
            <div className="tracking-steps">
              {[
                [ClipboardList, "Order confirmed"],
                [CreditCard, "Mock payment settled"],
                [Package, "Preparing your order"],
                [Truck, "In transit"],
                [CheckCircle2, "Delivered"],
              ].map(([Icon, label], i) => {
                const Component = Icon as typeof Package;
                return (
                  <div key={String(label)} className={i < 3 ? "active" : ""}>
                    <span>
                      {i < 2 ? <Check size={18} /> : <Component size={18} />}
                    </span>
                    <div>
                      <strong>{String(label)}</strong>
                      <small>
                        {i < 2
                          ? "Completed"
                          : i === 2
                            ? "Current simulated status"
                            : "Awaiting carrier update"}
                      </small>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="policy-reason" style={{ marginTop: 20 }}>
              This order is {order.status.replaceAll("_", " ")}. Refer to the
              shipment and payment status below.
            </div>
          )}
          {order.shipments.map((s) => (
            <div className="tracking-code" key={s.tracking_code}>
              <span>{s.kind} shipment</span>
              <strong>{s.tracking_code}</strong>
              <Status value={s.status} />
            </div>
          ))}
        </section>
        <section className="panel">
          <h2>Order details</h2>
          {order.kind === "procurement" && (
            <button
              className="button secondary"
              style={{ marginTop: 16 }}
              onClick={downloadPurchaseOrder}
            >
              Download purchase order
              <ClipboardList size={16} />
            </button>
          )}
          <dl className="spec-list">
            <div>
              <dt>Total</dt>
              <dd>{money(order.total)}</dd>
            </div>
            <div>
              <dt>Payment</dt>
              <dd>{order.payment.status}</dd>
            </div>
            <div>
              <dt>Delivery address</dt>
              <dd>{order.address}</dd>
            </div>
            <div>
              <dt>Order type</dt>
              <dd>{order.kind}</dd>
            </div>
          </dl>
          <div className="order-item-list">
            {order.items.map((i) => (
              <div key={i.product_id}>
                <span>
                  {i.product.name} × {i.quantity}
                </span>
                <strong>{money(i.unit_price * i.quantity)}</strong>
              </div>
            ))}
          </div>
          <div className="bundle-actions">
            <Link
              to="/returns"
              state={{ order_id: order.id }}
              className="button secondary"
            >
              <Undo2 size={16} />
              Return or replace
            </Link>
            {order.status === "confirmed" && (
              <button
                className="button secondary"
                disabled={cancel.isPending}
                onClick={() => cancel.mutate()}
              >
                Request cancellation
              </button>
            )}
          </div>
          {cancel.error && <ErrorState error={cancel.error} />}
        </section>
      </div>
    </>
  );
}
export function Returns() {
  const user = useSession((s) => s.user),
    [orderId, setOrderId] = useState(""),
    [quantities, setQuantities] = useState<Record<string, number>>({}),
    [reason, setReason] = useState(
      "The product arrived damaged. I would like help resolving this.",
    ),
    [resolution, setResolution] = useState("replacement"),
    [execution, setExecution] = useState<string | null>(null);
  const { data: orders = [] } = useQuery({
    queryKey: ["orders"],
    queryFn: () => api<Order[]>("/orders"),
    enabled: !!user,
  });
  const submit = useMutation({
    mutationFn: () =>
      post<Execution>(
        "/returns",
        {
          order_id: orderId,
          reason,
          resolution,
          items: Object.entries(quantities)
            .filter(([, quantity]) => quantity > 0)
            .map(([product_id, quantity]) => ({ product_id, quantity })),
        },
        true,
      ),
    onSuccess: (r) => setExecution(r.id),
  });
  return (
    <>
      <PageHeading
        eyebrow="LET’S MAKE IT RIGHT"
        title="A little help getting back on track."
        description="Request a reviewed return or replacement within the demo’s 30-day policy."
      />
      {!user ? (
        <Empty
          title="We can help with your order."
          text="Sign in to request a return."
          to="/login"
          label="Sign in"
        />
      ) : execution ? (
        <ExecutionView id={execution} />
      ) : (
        <div className="return-layout">
          <form
            className="panel form-panel"
            onSubmit={(e) => {
              e.preventDefault();
              submit.mutate();
            }}
          >
            <h2>Tell us about your purchase</h2>
            <label>
              Order
              <select
                value={orderId}
                onChange={(e) => {
                  setOrderId(e.target.value);
                  setQuantities({});
                }}
                required
              >
                <option value="">Choose an order</option>
                {orders
                  .filter((o) =>
                    ["confirmed", "delivered", "partially_returned"].includes(
                      o.status,
                    ),
                  )
                  .map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.number} — {money(o.total)}
                    </option>
                  ))}
              </select>
            </label>
            {orderId && (
              <fieldset>
                <legend>Select items and quantities</legend>
                {orders
                  .find((o) => o.id === orderId)
                  ?.items.map((item) => (
                    <label key={item.product_id}>
                      {item.product.name} (
                      {item.returnable_quantity ?? item.quantity} available to
                      return)
                      <input
                        type="number"
                        min={0}
                        max={item.returnable_quantity ?? item.quantity}
                        value={quantities[item.product_id] || 0}
                        onChange={(e) =>
                          setQuantities({
                            ...quantities,
                            [item.product_id]: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                  ))}
              </fieldset>
            )}
            <label>
              What happened?
              <textarea
                rows={4}
                minLength={10}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
            <label>
              Preferred resolution
              <select
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
              >
                <option value="replacement">Replacement</option>
                <option value="refund">Refund to mock payment</option>
              </select>
            </label>
            {submit.error && <ErrorState error={submit.error} />}
            <button
              className="button primary"
              disabled={
                submit.isPending ||
                !orderId ||
                !Object.values(quantities).some((q) => q > 0)
              }
            >
              Submit for review
              <ArrowRight size={16} />
            </button>
          </form>
          <aside className="panel return-policy">
            <ShieldCheck size={29} />
            <h2>A clear path forward.</h2>
            <p>
              We check ownership, purchase date, policy, previous returns and
              risk before taking action.
            </p>
            <ul>
              <li>30-day eligibility window</li>
              <li>Choose individual products and quantities</li>
              <li>Independent manager review above ₹10,000</li>
              <li>Damaged stock is kept out of sellable inventory</li>
              <li>Refunds use the safe mock payment provider</li>
            </ul>
            <Link to="/support">
              Need help first?
              <ArrowRight size={16} />
            </Link>
          </aside>
        </div>
      )}
    </>
  );
}
