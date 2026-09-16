import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowDownRight,
  Check,
  CheckCircle2,
  Clock,
  MessageSquare,
  ShieldCheck,
  Terminal,
  X,
} from "lucide-react";
import { api, money, post } from "../api";
import { Empty, ErrorState, Loading, PageHeading, Status } from "../components";
import { useNotice, useSession } from "../store";
import type { Approval } from "../types";

export function Approvals() {
  const user = useSession((s) => s.user),
    client = useQueryClient(),
    notice = useNotice();
  const {
    data = [],
    error,
    isLoading,
  } = useQuery({
    queryKey: ["approvals"],
    queryFn: () => api<Approval[]>("/approvals"),
    enabled: !!user,
    refetchInterval: 1500,
  });
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const decision = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: string }) =>
      post(`/approvals/${id}/decision`, {
        decision,
        feedback: feedback[id] || "",
      }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["approvals"] });
      notice.show(
        "Decision recorded. The saved workflow will continue when approved or rejected.",
      );
    },
    onError: (e: Error) => notice.show(e.message),
  });
  const pending = data.filter((a) =>
    ["pending", "needs_info"].includes(a.status),
  );
  return (
    <>
      <PageHeading
        eyebrow="YOU’RE ALWAYS IN CONTROL"
        title="A thoughtful pause before the next step."
        description="Review the amount, items, policy and risk before approving a sensitive action."
        action={
          <span className="outlined-badge">
            <Clock size={15} />
            {pending.length} awaiting review
          </span>
        }
      />
      {!user ? (
        <Empty
          title="Your review matters."
          text="Sign in to view approval requests."
          to="/login"
          label="Sign in"
        />
      ) : isLoading ? (
        <Loading />
      ) : error ? (
        <ErrorState error={error} />
      ) : !data.length ? (
        <Empty
          title="All clear for now."
          text="Checkout, procurement and return requests will appear here when they need review."
          to="/missions"
        />
      ) : (
        <div className="approval-list">
          {data.map((a) => (
            <article
              key={a.id}
              data-testid={`approval-${a.execution_id}`}
              className="panel approval-card"
            >
              <div className="approval-card-heading">
                <span className="journey-icon green-bg">
                  <ShieldCheck size={22} />
                </span>
                <div>
                  <span className="eyebrow">
                    {a.kind} REQUEST · {a.execution_id.slice(0, 8)}
                  </span>
                  <h2>
                    {a.customer}'s{" "}
                    {a.kind === "return"
                      ? "return request"
                      : a.kind === "cancel"
                        ? "cancellation request"
                        : "purchase review"}
                  </h2>
                </div>
                <Status value={a.status} />
              </div>
              <div className="approval-facts">
                <div>
                  <span>Requested amount</span>
                  <strong>{money(a.amount)}</strong>
                </div>
                <div>
                  <span>Risk score</span>
                  <strong>
                    {a.risk_score}
                    <small>/ 100</small>
                  </strong>
                </div>
                <div>
                  <span>Required reviewer</span>
                  <strong>
                    {a.required_role === "OWNER"
                      ? "Account owner"
                      : "Independent manager"}
                  </strong>
                </div>
              </div>
              <div className="policy-reason">
                <ShieldCheck size={17} />
                {a.reason}
              </div>
              {a.procurement && Object.keys(a.procurement).length > 0 && (
                <details className="approval-items">
                  <summary>Review business and delivery details</summary>
                  <dl className="spec-list">
                    {Object.entries(a.procurement).map(([key, value]) => (
                      <div key={key}>
                        <dt>{key.replaceAll("_", " ")}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                </details>
              )}
              {a.quote?.items && (
                <details className="approval-items">
                  <summary>
                    Review exact items and quantities{" "}
                    <ArrowDownRight size={15} />
                  </summary>
                  {a.quote.items.map((i) => (
                    <div key={i.product_id}>
                      <span>
                        {i.product.name} × {i.quantity}
                      </span>
                      <strong>
                        {money(i.amount ?? i.unit_price * i.quantity)}
                      </strong>
                    </div>
                  ))}
                </details>
              )}
              {a.feedback && (
                <p className="feedback">
                  <MessageSquare size={15} />
                  Review note: {a.feedback}
                </p>
              )}
              {["pending", "needs_info"].includes(a.status) &&
                (a.can_decide ? (
                  <div className="approval-controls">
                    <label className="sr-only" htmlFor={`feedback-${a.id}`}>
                      Reviewer feedback
                    </label>
                    <input
                      id={`feedback-${a.id}`}
                      placeholder="Add a review note or request more information…"
                      value={feedback[a.id] || ""}
                      onChange={(e) =>
                        setFeedback({ ...feedback, [a.id]: e.target.value })
                      }
                    />
                    <div>
                      <button
                        className="button primary"
                        disabled={decision.isPending}
                        onClick={() =>
                          decision.mutate({ id: a.id, decision: "approve" })
                        }
                      >
                        <Check size={16} />
                        Approve
                      </button>
                      <button
                        className="button secondary danger-text"
                        disabled={decision.isPending}
                        onClick={() =>
                          decision.mutate({ id: a.id, decision: "reject" })
                        }
                      >
                        <X size={16} />
                        Reject
                      </button>
                      <button
                        className="button secondary"
                        disabled={decision.isPending || !feedback[a.id]?.trim()}
                        onClick={() =>
                          decision.mutate({
                            id: a.id,
                            decision: "request_info",
                          })
                        }
                      >
                        <MessageSquare size={16} />
                        Request information
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="reviewer-note">
                    {a.required_role === "MANAGER"
                      ? "Sign in as an independent manager or administrator to review this request."
                      : "This request must be confirmed by the account owner."}
                  </div>
                ))}
            </article>
          ))}
        </div>
      )}
    </>
  );
}
type Ops = {
  total_requests: number;
  successful: number;
  failed: number;
  average_latency_ms: number;
  tokens: number;
  estimated_cost: number;
  mcp_calls: number;
  tool_failure_rate: number;
  human_intervention_rate: number;
  outbox_pending: number;
  dead_letters: number;
  agents: {
    name: string;
    calls: number;
    success_rate: number | null;
    latency_ms: number | null;
  }[];
  executions: {
    id: string;
    kind: string;
    status: string;
    duration_ms: number;
    created_at: number;
  }[];
};
export function Operations() {
  const user = useSession((s) => s.user),
    allowed = ["MANAGER", "ADMIN"].includes(user?.role || "");
  const { data, isLoading, error } = useQuery({
    queryKey: ["operations"],
    queryFn: () => api<Ops>("/operations"),
    enabled: allowed,
    refetchInterval: 5000,
  });
  if (!allowed)
    return (
      <Empty
        title="Operations are role-protected."
        text="Sign in as a manager or administrator to inspect platform activity."
        to="/login"
        label="Switch account"
      />
    );
  return (
    <>
      <PageHeading
        eyebrow="THE SYSTEM BEHIND THE EXPERIENCE"
        title="Every action, accounted for."
        description="Real execution data from your local workspace. Unused metrics show no data."
        action={
          <span className="outlined-badge">
            <Activity size={15} />
            Refreshes every 5 seconds
          </span>
        }
      />
      {isLoading ? (
        <Loading />
      ) : error ? (
        <ErrorState error={error} />
      ) : (
        data && (
          <>
            <div className="metrics-grid">
              {[
                ["AI workflows", data.total_requests, "Persisted executions"],
                [
                  "Successful",
                  data.successful,
                  `${data.failed} failed workflows`,
                ],
                [
                  "Average duration",
                  `${(data.average_latency_ms / 1000).toFixed(2)}s`,
                  "Includes each execution segment",
                ],
                [
                  "MCP calls",
                  data.mcp_calls,
                  `${data.tool_failure_rate}% tool failure rate`,
                ],
                [
                  "Model tokens",
                  data.tokens,
                  data.tokens
                    ? "Reported provider usage"
                    : "Offline deterministic mode",
                ],
                [
                  "Estimated model cost",
                  `$${data.estimated_cost.toFixed(4)}`,
                  "From configured per-token prices",
                ],
                [
                  "Human review",
                  `${data.human_intervention_rate}%`,
                  "Requests with an approval step",
                ],
                [
                  "Pending events",
                  data.outbox_pending,
                  `${data.dead_letters} exhausted retries`,
                ],
              ].map(([label, value, detail]) => (
                <div className="metric-card panel" key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                  <small>{detail}</small>
                </div>
              ))}
            </div>
            <div className="ops-grid">
              <section className="panel">
                <div className="section-heading">
                  <h2>Specialist execution performance</h2>
                  <Terminal size={19} />
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Agent</th>
                        <th>Calls</th>
                        <th>Success</th>
                        <th>Avg. latency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.agents.map((a) => (
                        <tr key={a.name}>
                          <td>
                            <span className="agent-name">
                              <Activity size={14} />
                              {a.name}
                            </span>
                          </td>
                          <td>{a.calls}</td>
                          <td>
                            {a.success_rate === null
                              ? "—"
                              : `${a.success_rate}%`}
                          </td>
                          <td>
                            {a.latency_ms === null ? "—" : `${a.latency_ms} ms`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <section className="panel">
                <div className="section-heading">
                  <h2>Recent executions</h2>
                  <Clock size={19} />
                </div>
                <div className="execution-feed">
                  {data.executions.map((e) => (
                    <div key={e.id}>
                      <span className="feed-icon">
                        {e.status === "completed" ? (
                          <CheckCircle2 size={19} />
                        ) : (
                          <Activity size={19} />
                        )}
                      </span>
                      <div>
                        <strong>{e.kind}</strong>
                        <small>
                          {e.id.slice(0, 12)} ·{" "}
                          {(e.duration_ms / 1000).toFixed(2)}s
                        </small>
                      </div>
                      <Status value={e.status} />
                    </div>
                  ))}
                  {!data.executions.length && (
                    <p>Run a shopping mission to populate this view.</p>
                  )}
                </div>
              </section>
            </div>
            <div className="observability-note">
              <ShieldCheck size={21} />
              <p>
                Prometheus exposes HTTP, database, cache, MCP, workflow and
                event metrics. Optional OpenTelemetry and LangSmith exporters
                are configured through environment variables.
              </p>
            </div>
          </>
        )
      )}
    </>
  );
}
type AdminData = {
  orders: number;
  revenue: number;
  products: number;
  low_stock: { product_id: string; name: string; stock: number }[];
  audit: {
    id: string;
    action: string;
    resource_id: string;
    created_at: number;
  }[];
};
export function Admin() {
  const allowed = useSession((s) => s.user?.role === "ADMIN");
  const { data, error, isLoading } = useQuery({
    queryKey: ["admin"],
    queryFn: () => api<AdminData>("/admin"),
    enabled: allowed,
    refetchInterval: 5000,
  });
  if (!allowed)
    return (
      <Empty
        title="Administrator access required."
        text="Sign in with the administrator demo account."
        to="/login"
        label="Switch account"
      />
    );
  return (
    <>
      <PageHeading
        eyebrow="COMMERCE AT A GLANCE"
        title="Your workspace, in perspective."
        description="Order activity, inventory and a durable audit trail."
      />
      <RecoveryPanel />
      {isLoading ? (
        <Loading />
      ) : error ? (
        <ErrorState error={error} />
      ) : (
        data && (
          <>
            <div className="metrics-grid three">
              {[
                ["Orders", data.orders],
                ["Confirmed order value", money(data.revenue)],
                ["Catalog products", data.products],
              ].map(([k, v]) => (
                <div key={k} className="metric-card panel">
                  <span>{k}</span>
                  <strong>{v}</strong>
                  <small>Synthetic local activity</small>
                </div>
              ))}
            </div>
            <div className="ops-grid">
              <section className="panel">
                <h2>Inventory to keep an eye on</h2>
                <table>
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Available</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.low_stock.map((i) => (
                      <tr key={i.product_id}>
                        <td>{i.name}</td>
                        <td>{i.stock}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
              <section className="panel">
                <h2>Recent audit activity</h2>
                <div
                  className="audit-feed"
                  tabIndex={0}
                  role="region"
                  aria-label="Audit history"
                >
                  {data.audit.map((a) => (
                    <div key={a.id}>
                      <strong>{a.action}</strong>
                      <span>{a.resource_id.slice(0, 24)}</span>
                      <small>
                        {new Date(a.created_at * 1000).toLocaleTimeString()}
                      </small>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </>
        )
      )}
    </>
  );
}

type RecoveryData = {
  outbox: {
    id: string;
    type: string;
    attempts: number;
    error: string | null;
  }[];
  workflows: { id: string; kind: string; status: string }[];
  dead_letters: {
    id: string;
    reason: string;
    source: string;
    status: string;
  }[];
};
function RecoveryPanel() {
  const [reason, setReason] = useState("");
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["recovery"],
    queryFn: () => api<RecoveryData>("/admin/recovery"),
  });
  const replay = useMutation({
    mutationFn: (path: string) => post(path, { reason }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["recovery"] }),
  });
  return (
    <details className="panel recovery-panel">
      <summary>Recovery center</summary>
      <p>
        Review the cause before retrying. Each action records your reason in the
        audit trail.
      </p>
      <label>
        Reason for recovery
        <input
          value={reason}
          minLength={10}
          onChange={(e) => setReason(e.target.value)}
        />
      </label>
      {query.error && <ErrorState error={query.error} />}
      {replay.error && <ErrorState error={replay.error} />}
      {query.data && (
        <>
          {query.data.outbox.map((e) => (
            <div className="recovery-row" key={e.id}>
              <span>
                {e.type} · {e.attempts} attempts · {e.error || "Pending"}
              </span>
              <button
                className="button secondary"
                disabled={reason.length < 10 || replay.isPending}
                onClick={() => replay.mutate(`/admin/outbox/${e.id}/replay`)}
              >
                Retry event
              </button>
            </div>
          ))}
          {query.data.workflows.map((e) => (
            <div className="recovery-row" key={e.id}>
              <span>
                {e.kind} · {e.status} · {e.id.slice(0, 8)}
              </span>
              <button
                className="button secondary"
                disabled={reason.length < 10 || replay.isPending}
                onClick={() =>
                  replay.mutate(`/admin/workflows/${e.id}/recover`)
                }
              >
                Recover workflow
              </button>
            </div>
          ))}
          {query.data.dead_letters.map((e) => (
            <div className="recovery-row" key={e.id}>
              <span>
                {e.reason} · {e.source}
              </span>
              <button
                className="button secondary"
                disabled={reason.length < 10 || replay.isPending}
                onClick={() =>
                  replay.mutate(`/admin/dead-letters/${e.id}/replay`)
                }
              >
                Validate and replay
              </button>
            </div>
          ))}
          {!query.data.outbox.length &&
            !query.data.workflows.length &&
            !query.data.dead_letters.length && (
              <p>No pending recovery actions.</p>
            )}
        </>
      )}
    </details>
  );
}
