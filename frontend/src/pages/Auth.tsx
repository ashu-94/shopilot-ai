import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, LoaderCircle, ShieldCheck, Sparkles } from "lucide-react";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { Brand, ErrorState } from "../components";
import { post, api } from "../api";
import { useSession } from "../store";
import type { User } from "../types";

export default function Auth() {
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<Error | null>(null),
    navigate = useNavigate(),
    session = useSession(),
    client = useQueryClient();
  const {data:config} = useQuery({queryKey:["config"],queryFn:()=>api<{demo:boolean}>("/config")});
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await post<{ access_token: string; user: User }>(
        "/auth/login",
        { email, password },
      );
      session.setSession(data.access_token, data.user);
      client.clear();
      navigate("/");
    } catch (e) {
      setError(e as Error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-layout">
      <section className="login-story">
        <Brand />
        <div>
          <span className="outlined-badge">
            <Sparkles size={15} />A more thoughtful way to shop
          </span>
          <h1>
            Your next big thing
            <br />
            starts with a<br />
            <em>little direction.</em>
          </h1>
          <p>
            Tell ShopPilot what you’re trying to accomplish,
            <br />
            not what product you want.
          </p>
        </div>
        <small>ShopPilot AI · Goal-oriented commerce</small>
      </section>
      <section className="login-form">
        <Link className="back-link" to="/">
          ← Back to workspace
        </Link>
        <div>
          <span className="eyebrow green">YOUR GOALS ARE WAITING</span>
          <h2>Welcome back.</h2>
          <p>Sign in to plan, compare, and make it happen.</p>
          <form onSubmit={submit}>
            <label>
              Email address
              <input
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {error && <ErrorState error={error} />}
            <button className="button primary wide" disabled={busy}>
              {busy ? (
                <LoaderCircle className="spin" size={18} />
              ) : (
                <>
                  Sign in
                  <ArrowRight size={17} />
                </>
              )}
            </button>
          </form>
          {config?.demo && <div className="demo-accounts">
            <span className="eyebrow">EXPLORE A DEMO ROLE</span>
            <div>
              {[
                ["alex", "Shopper"],
                ["business", "Business"],
                ["manager", "Manager"],
                ["admin", "Admin"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  className={email.startsWith(value + "@") ? "active" : ""}
                  onClick={() => {
                    setEmail(`${value}@shopilot.demo`);
                    setPassword("ShopPilot-demo-2026!");
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <p>
              <ShieldCheck size={15} />
              Synthetic products. Simulated payments. No real charges.
            </p>
          </div>}
        </div>
      </section>
    </div>
  );
}
