import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  BriefcaseBusiness,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock,
  LoaderCircle,
  RotateCcw,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Terminal,
  TriangleAlert,
} from "lucide-react";
import { motion } from "framer-motion";
import { api, money, post } from "../api";
import {
  Empty,
  ErrorState,
  EvidenceList,
  PageHeading,
  ProductArt,
  Status,
} from "../components";
import { useNotice, useSession } from "../store";
import type { Bundle, Execution, ProgressEvent } from "../types";

export const FLAGSHIP =
  "Build me a complete AI/ML home office setup under ₹150,000. I need a laptop capable of Python, Docker and local LLM development, plus a monitor, ergonomic chair, keyboard, mouse and UPS.";
export const PROCUREMENT =
  "We need 20 laptops for an AI engineering team with 32GB RAM, 1TB SSD and three-year warranty. Budget ₹25 lakh.";
export function ExecutionView({
  id,
  onComplete,
}: {
  id: string;
  onComplete?: () => void;
}) {
  const [events, setEvents] = useState<ProgressEvent[]>([]),
    token = useSession((s) => s.token),
    notice = useNotice(),
    client = useQueryClient();
  const query = useQuery({
    queryKey: ["execution", id],
    queryFn: () => api<Execution>(`/executions/${id}`),
    refetchInterval: (q) =>
      ["queued", "running"].includes(q.state.data?.status || "queued")
        ? 800
        : false,
  });
  const result = query.data;
  useEffect(() => {
    setEvents([]);
  }, [id]);
  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    (async () => {
      try {
        const response = await fetch(`/api/executions/${id}/events`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        if (!response.ok || !response.body) return;
        const reader = response.body.getReader(),
          decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";
          for (const part of parts) {
            const line = part.split("\n").find((l) => l.startsWith("data: "));
            if (line && !part.includes("event: done")) {
              const event = JSON.parse(line.slice(6));
              setEvents((old) =>
                old.some((e) => e.id === event.id) ? old : [...old, event],
              );
            }
          }
        }
      } catch {
        /* Polling provides recovery if the SSE connection drops. */
      }
    })();
    return () => controller.abort();
  }, [id, token, result?.status === "running"]);
  useEffect(() => {
    if (result?.status === "completed") {
      client.invalidateQueries({ queryKey: ["orders"] });
      client.invalidateQueries({ queryKey: ["cart"] });
      client.invalidateQueries({ queryKey: ["approvals"] });
      onComplete?.();
    }
  }, [result?.status, client, onComplete]);
  const add = useMutation({
    mutationFn: () =>
      api("/cart", {
        method: "PUT",
        body: JSON.stringify({
          items: result?.result.products?.map((p) => ({
            product_id: p.id,
            quantity: result.result.quantity || 1,
          })),
        }),
      }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["cart"] });
      notice.show(
        "Your complete bundle is in the cart. Review it before checkout.",
      );
    },
    onError: (e: Error) => notice.show(e.message),
  });
  if (query.error) return <ErrorState error={query.error} />;
  return (
    <div className="execution">
      <div className="execution-progress panel">
        <div className="panel-title">
          <span className="journey-icon green-bg">
            <Sparkles size={20} />
          </span>
          <div>
            <h3>Your copilot is on it</h3>
            <p>Live workflow activity · {id.slice(0, 8)}</p>
          </div>
          {result && <Status value={result.status} />}
        </div>
        <div className="progress-events">
          {events.map((e, i) => (
            <div key={e.id} className="progress-event">
              <span
                className={e.stage === "failed" ? "step-error" : "step-done"}
              >
                {e.stage === "failed" ? (
                  <TriangleAlert size={13} />
                ) : (
                  <Check size={13} />
                )}
              </span>
              <span>{e.message}</span>
              <small>{String(i + 1).padStart(2, "0")}</small>
            </div>
          ))}
          {(!result || ["queued", "running"].includes(result.status)) && (
            <div className="progress-event">
              <LoaderCircle className="spin" size={17} />
              <span>Working through the next step…</span>
            </div>
          )}
        </div>
      </div>
      {result?.error && (
        <>
          <ErrorState error={new Error(result.error)} />
          <button
            className="button secondary"
            onClick={async () => {
              await post(`/executions/${id}/retry`);
              client.invalidateQueries({ queryKey: ["execution", id] });
            }}
          >
            <RotateCcw size={16} />
            Retry workflow
          </button>
        </>
      )}
      {result?.result.products && (
        <BundleView
          bundle={result.result as Bundle}
          actions={
            result.kind === "shopping" ? (
              <>
                <button
                  className="button primary"
                  disabled={add.isPending}
                  onClick={() => add.mutate()}
                >
                  <ShoppingCart size={17} />
                  {add.isPending ? "Adding bundle…" : "Add complete bundle"}
                </button>
                <Link to="/cart" className="button secondary">
                  Review cart
                  <ArrowRight size={16} />
                </Link>
              </>
            ) : undefined
          }
        />
      )}{" "}
      {result?.status === "awaiting_approval" && (
        <div className="approval-banner">
          <ShieldCheck size={28} />
          <div>
            <h3>Your review is the next step.</h3>
            <p>
              {result.kind === "procurement"
                ? "An independent manager must approve this purchase order. Sign in with the manager demo account."
                : "Open the approval center to review the exact request and give the go-ahead."}
            </p>
          </div>
          <Link className="button primary" to="/approvals">
            Review request
            <ArrowRight size={16} />
          </Link>
        </div>
      )}
      {result?.result.order && (
        <div className="success-banner">
          <CheckCircle2 size={30} />
          <div>
            <h2>
              {result.result.order.status === "cancelled"
                ? "Order cancelled"
                : "You’re all set."}
            </h2>
            <p>
              {result.result.order.number} · {money(result.result.order.total)}{" "}
              · Safe mock payment
            </p>
          </div>
          <Link
            to={`/orders/${result.result.order.id}`}
            className="button primary"
          >
            View order
            <ArrowRight size={16} />
          </Link>
        </div>
      )}
      {result?.result.return && (
        <div className="success-banner">
          <CheckCircle2 />
          <div>
            <h2>
              {result.result.return.resolution === "refund"
                ? "Mock refund completed"
                : "Replacement arranged"}
            </h2>
            <p>
              {money(result.result.return.amount)} · View the updated order for
              details.
            </p>
          </div>
          <Link to="/orders" className="button primary">
            My orders
          </Link>
        </div>
      )}
      {result?.result.answer && (
        <div className="panel support-answer">
          <div className="eyebrow green">
            <BookOpen size={15} />
            SUPPORT RESPONSE
          </div>
          <h2>A little guidance for your next step.</h2>
          <p>{result.result.answer}</p>
          {result.result.ticket_id && (
            <small>
              Support request #{result.result.ticket_id.slice(0, 8)}
            </small>
          )}
          <EvidenceList evidence={result.result.evidence || []} />
          <Link to="/returns" className="button secondary">
            Request a return
            <ArrowRight size={16} />
          </Link>
        </div>
      )}
    </div>
  );
}
function BundleView({
  bundle,
  actions,
}: {
  bundle: Bundle;
  actions?: React.ReactNode;
}) {
  return (
    <motion.section
      className="bundle"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="section-heading">
        <div>
          <span className="eyebrow green">A PLAN THAT FITS</span>
          <h2>
            Your recommended {bundle.quantity > 1 ? "team purchase" : "setup"}
          </h2>
          <p>{bundle.explanation}</p>
        </div>
        <span className="outlined-badge">
          <ShieldCheck size={15} />
          Catalog verified
        </span>
      </div>
      <div className="bundle-summary">
        <div>
          <span>Total investment</span>
          <strong>{money(bundle.total)}</strong>
        </div>
        <div>
          <span>Budget remaining</span>
          <strong className="green">{money(bundle.remaining)}</strong>
        </div>
        <div>
          <span>Bundle savings</span>
          <strong>{money(bundle.discount)}</strong>
        </div>
        <div>
          <span>Items in your plan</span>
          <strong>
            {bundle.products.length * bundle.quantity}
            <small>pieces</small>
          </strong>
        </div>
      </div>
      <div className="bundle-lines">
        {bundle.products.map((p, index) => (
          <div className="bundle-line panel" key={p.id}>
            <span className="line-number">
              {String(index + 1).padStart(2, "0")}
            </span>
            <Link to={`/products/${p.id}`}>
              <ProductArt product={p} />
            </Link>
            <div className="bundle-line-copy">
              <span className="eyebrow">
                {p.category}{" "}
                {bundle.quantity > 1 && `· ${bundle.quantity} units`}
              </span>
              <Link to={`/products/${p.id}`}>
                <h3>{p.name}</h3>
              </Link>
              <p>{p.reason}</p>
              {p.review_analysis && (
                <details className="source-details">
                  <summary>
                    Review analysis · {p.review_analysis.sample_size} reviews
                  </summary>
                  <p>
                    Confidence: {p.review_analysis.confidence}.{" "}
                    {p.review_analysis.verified_count} verified records;{" "}
                    {p.review_analysis.duplicate_text_count} duplicate texts.
                  </p>
                  {Object.entries(p.review_analysis.aspects).map(
                    ([name, aspect]) => (
                      <p key={name}>
                        {name}: {aspect.mentions} mentions, average{" "}
                        {aspect.average_rating}/5
                      </p>
                    ),
                  )}
                  <p>
                    Synthetic reviews describe this demo catalog; they do not
                    establish real-world quality.
                  </p>
                </details>
              )}
              <details className="source-details">
                <summary>
                  <BookOpen size={14} />
                  {p.evidence?.length || 0} supporting sources
                  <ChevronDown size={14} />
                </summary>
                <EvidenceList evidence={p.evidence || []} />
              </details>
            </div>
            <div className="bundle-line-price">
              <strong>{money(p.price * bundle.quantity)}</strong>
              <span>
                <Check size={13} />
                {p.stock} in stock
              </span>
              <small>{p.warranty_months / 12}-year warranty</small>
            </div>
          </div>
        ))}
      </div>
      {bundle.warnings.length > 0 && (
        <div className="compatibility-notes">
          <TriangleAlert size={20} />
          <div>
            <strong>A few things to keep in mind</strong>
            {bundle.warnings.map((w) => (
              <p key={w}>{w}</p>
            ))}
          </div>
        </div>
      )}
      <details className="alternative panel">
        <summary>
          <span>Consider the lower-cost alternative</span>
          <strong>{money(bundle.alternative.subtotal)} before coupon</strong>
          <ChevronDown size={16} />
        </summary>
        <p>{bundle.alternative.products.map((p) => p.name).join(" · ")}</p>
        <p>
          Meets the same hard requirements. The recommended bundle scores higher
          on quality signals.
        </p>
      </details>
      {actions && <div className="bundle-actions">{actions}</div>}
    </motion.section>
  );
}
export default function Mission({
  mode = "shopping",
}: {
  mode?: "shopping" | "procurement" | "support";
}) {
  const location = useLocation(),
    user = useSession((s) => s.user);
  const defaultQuery =
    mode === "procurement"
      ? PROCUREMENT
      : mode === "support"
        ? "The office chair from my last order arrived damaged. What should I do?"
        : FLAGSHIP;
  const [query, setQuery] = useState(location.state?.query || defaultQuery),
    [execution, setExecution] = useState<string | null>(null);
  useEffect(() => {
    setExecution(null);
    setQuery(location.state?.query || defaultQuery);
  }, [mode, defaultQuery, location.state]);
  const [procurement, setProcurement] = useState({
    organization: "",
    cost_center: "",
    delivery_address: "",
    billing_address: "",
    contact_email: "",
    requested_delivery_date: "",
    payment_terms: "prepaid_mock",
    reference: "",
  });
  const request = useMutation({
    mutationFn: () =>
      post<Execution>(
        "/missions",
        { query, mode, ...(mode === "procurement" ? { procurement } : {}) },
        true,
      ),
    onSuccess: (e) => setExecution(e.id),
  });
  const history = useQuery({
    queryKey: ["executions"],
    queryFn: () => api<Execution[]>("/executions"),
    enabled: !!user,
  });
  const business = mode === "procurement",
    support = mode === "support";
  return (
    <>
      <PageHeading
        eyebrow={
          business
            ? "EQUIP YOUR NEXT CHAPTER"
            : support
              ? "WE’RE HERE FOR WHAT COMES NEXT"
              : "FROM AMBITION TO ACTION"
        }
        title={
          business
            ? "A smarter purchase for your team."
            : support
              ? "Let’s work through it."
              : "What are you trying to accomplish?"
        }
        description={
          business
            ? "Requirements, vendor comparison, and a purchase order — with a manager in the loop."
            : support
              ? "Grounded guidance from your purchases, manuals and warranty policies."
              : "Share the goal. We’ll build a complete, considered plan around it."
        }
      />
      {!user ? (
        <Empty
          title="Your mission starts here."
          text="Sign in with a demo account to create a persistent shopping mission."
          to="/login"
          label="Sign in to continue"
        />
      ) : (
        <>
          <section className="mission-composer panel">
            <div className="composer-top">
              <span className="journey-icon green-bg">
                {business ? (
                  <BriefcaseBusiness size={21} />
                ) : (
                  <Sparkles size={21} />
                )}
              </span>
              <div>
                <h3>
                  {business
                    ? "Procurement brief"
                    : support
                      ? "Tell us what happened"
                      : "Every good plan starts with your goal"}
                </h3>
                <p>
                  {business
                    ? "Include quantity, specifications, warranty and total budget."
                    : "Be as specific as you like. The details make a difference."}
                </p>
              </div>
              <span className="outlined-badge">
                <Terminal size={13} />
                Local demo
              </span>
            </div>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Mission description"
              rows={4}
            />
            {business && (
              <fieldset className="procurement-fields">
                <legend>Purchase order details</legend>
                {(
                  [
                    ["organization", "Organization"],
                    ["cost_center", "Cost center"],
                    ["delivery_address", "Delivery address"],
                    ["billing_address", "Billing address"],
                    ["contact_email", "Contact email"],
                    ["requested_delivery_date", "Requested delivery date"],
                    ["reference", "Internal reference (optional)"],
                  ] as const
                ).map(([key, label]) => (
                  <label key={key}>
                    {label}
                    <input
                      type={
                        key === "contact_email"
                          ? "email"
                          : key === "requested_delivery_date"
                            ? "date"
                            : "text"
                      }
                      value={procurement[key]}
                      required={key !== "reference"}
                      onChange={(e) =>
                        setProcurement({
                          ...procurement,
                          [key]: e.target.value,
                        })
                      }
                    />
                  </label>
                ))}
                <label>
                  Payment terms
                  <select
                    value={procurement.payment_terms}
                    onChange={(e) =>
                      setProcurement({
                        ...procurement,
                        payment_terms: e.target.value,
                      })
                    }
                  >
                    <option value="prepaid_mock">Prepaid (simulated)</option>
                    <option value="net_30_mock">Net 30 (simulated)</option>
                  </select>
                </label>
              </fieldset>
            )}
            <div className="composer-bottom">
              <span>
                <ShieldCheck size={16} />
                Every purchase waits for human approval.
              </span>
              <button
                className="button primary"
                onClick={() => request.mutate()}
                disabled={
                  request.isPending ||
                  query.length < 8 ||
                  (business &&
                    Object.entries(procurement).some(
                      ([key, value]) => key !== "reference" && !value,
                    ))
                }
              >
                {request.isPending ? (
                  <LoaderCircle className="spin" size={17} />
                ) : (
                  <Sparkles size={17} />
                )}{" "}
                {support
                  ? "Get support"
                  : business
                    ? "Build procurement plan"
                    : "Plan my mission"}
                <ArrowRight size={16} />
              </button>
            </div>
            {request.error && <ErrorState error={request.error} />}
          </section>
          {execution ? (
            <ExecutionView id={execution} />
          ) : (
            <>
              <div className="mission-tips">
                <div>
                  <span>01</span>
                  <h3>Clear requirements</h3>
                  <p>We turn your goal into specific purchasing needs.</p>
                </div>
                <div>
                  <span>02</span>
                  <h3>Grounded choices</h3>
                  <p>
                    Specifications, stock, reviews and policies from the
                    catalog.
                  </p>
                </div>
                <div>
                  <span>03</span>
                  <h3>A complete picture</h3>
                  <p>Budget, compatibility and alternatives, together.</p>
                </div>
              </div>
              {!!history.data?.length && (
                <section>
                  <div className="section-heading">
                    <h2>Pick up where you left off</h2>
                    <Clock size={19} />
                  </div>
                  <div className="panel history-list">
                    {history.data
                      .filter((e) => e.kind === mode)
                      .slice(0, 5)
                      .map((e) => (
                        <button key={e.id} onClick={() => setExecution(e.id)}>
                          <Sparkles size={18} />
                          <span>{e.query}</span>
                          <Status value={e.status} />
                          <ArrowRight size={17} />
                        </button>
                      ))}
                  </div>
                </section>
              )}
            </>
          )}
        </>
      )}
    </>
  );
}
