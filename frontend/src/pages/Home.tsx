import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  BriefcaseBusiness,
  Check,
  ChevronRight,
  Headphones,
  Monitor,
  Send,
  Sparkles,
  Target,
  Wallet,
} from "lucide-react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { PageHeading, ProductCard, TrustStrip } from "../components";
import { useSession } from "../store";
import type { Product } from "../types";

const suggestions = [
  "Build my home office",
  "Find my next laptop",
  "Upgrade movie night",
];
export default function Home() {
  const user = useSession((s) => s.user),
    navigate = useNavigate(),
    [query, setQuery] = useState("");
  const { data: products = [] } = useQuery({
    queryKey: ["products", "featured"],
    queryFn: () => api<Product[]>("/products"),
  });
  const featured = ["product-001", "product-004", "product-006", "product-008"]
    .map((id) => products.find((p) => p.id === id))
    .filter((p): p is Product => !!p);
  function start(value: string) {
    navigate("/missions", { state: { query: value } });
  }
  return (
    <>
      <PageHeading
        eyebrow="A LITTLE AMBITION GOES A LONG WAY"
        title={`Good to see you${user ? ", " + user.name.split(" ")[0] : ""}.`}
        description="What would you like to make possible today?"
        action={
          <span className="outlined-badge">
            <Sparkles size={14} />
            Your personal shopping copilot
          </span>
        }
      />
      <motion.section
        className="mission-hero"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="hero-main">
          <div className="hero-kicker">
            <span className="sparkle-tile">
              <Sparkles size={17} />
            </span>{" "}
            A smarter starting point
          </div>
          <h2>
            Start with a goal.
            <br />
            We’ll find your <em>way there.</em>
          </h2>
          <p>
            A home office. A creative studio. Your team's next chapter.
            <br className="desktop-only" />
            Tell us what you have in mind — we’ll connect the details.
          </p>
          <form
            className="hero-input"
            onSubmit={(e) => {
              e.preventDefault();
              start(
                query ||
                  "Build an AI/ML home office under ₹150000 with laptop, monitor, chair, keyboard, mouse and UPS",
              );
            }}
          >
            <Sparkles size={20} />
            <input
              aria-label="Describe your shopping goal"
              placeholder="I want to build a home office under ₹1,50,000…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button aria-label="Plan this mission" type="submit">
              <ArrowRight size={21} />
            </button>
          </form>
          <div className="hero-suggestions">
            Try a goal
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() =>
                  start(
                    s === "Upgrade movie night"
                      ? "TV and soundbar under ₹100000"
                      : s === "Find my next laptop"
                        ? "Laptop for Python and Docker under ₹100000"
                        : "Build an AI/ML home office under ₹150000 with laptop, monitor, chair, keyboard, mouse and UPS",
                  )
                }
              >
                {s}
                <ArrowUpRight size={12} />
              </button>
            ))}
          </div>
        </div>
        <div className="hero-aside">
          <div className="mission-preview">
            <div className="preview-top">
              <span className="preview-icon">
                <Monitor size={20} />
              </span>
              <span>
                Your next workspace<small>ONE GOAL. ALL THE DETAILS.</small>
              </span>
              <span className="tiny-pill">Example</span>
            </div>
            <div className="preview-budget">
              <span>A complete setup</span>
              <strong>
                ₹1,50,000 <small>budget</small>
              </strong>
            </div>
            <div className="preview-grid">
              {["Laptop", "Monitor", "Ergonomic chair", "Desk essentials"].map(
                (s, i) => (
                  <div key={s}>
                    <span className="preview-check">
                      <Check size={12} />
                    </span>
                    {s}
                    <span>0{i + 1}</span>
                  </div>
                ),
              )}
            </div>
            <div className="preview-foot">
              <ShieldSymbol />
              Thoughtfully matched. Ready for your review.
            </div>
          </div>
          <div className="hero-note">
            <span className="note-line" />
            Your ambition, with a plan.
          </div>
        </div>
      </motion.section>
      <TrustStrip />
      <section className="journey-grid">
        <Link to="/missions" className="journey-card">
          <span className="journey-icon green-bg">
            <Target size={23} />
          </span>
          <div>
            <h3>One mission. A complete setup.</h3>
            <p>A bundle that works together and fits your budget.</p>
          </div>
          <ArrowUpRight size={19} />
        </Link>
        <Link to="/procurement" className="journey-card">
          <span className="journey-icon purple-bg">
            <BriefcaseBusiness size={23} />
          </span>
          <div>
            <h3>Better equipped, together.</h3>
            <p>Plan team purchases with clear approvals.</p>
          </div>
          <ArrowUpRight size={19} />
        </Link>
        <Link to="/support" className="journey-card">
          <span className="journey-icon orange-bg">
            <Headphones size={23} />
          </span>
          <div>
            <h3>Support beyond the checkout.</h3>
            <p>Get help with your purchase, returns and more.</p>
          </div>
          <ArrowUpRight size={19} />
        </Link>
      </section>
      <div className="section-heading">
        <div>
          <span className="eyebrow">GOOD TOGETHER</span>
          <h2>Meet your next workspace</h2>
          <p>A few considered picks from our demo collection.</p>
        </div>
        <Link to="/shop">
          Explore the catalog <ArrowRight size={16} />
        </Link>
      </div>
      <div className="product-grid">
        {featured.map((p) => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
      <section className="how-section">
        <div>
          <div className="eyebrow">LESS SEARCHING. MORE DOING.</div>
          <h2>From “what if” to all set.</h2>
          <Link to="/missions">
            Create your first mission
            <ChevronRight size={16} />
          </Link>
        </div>
        <div className="how-step">
          <span>01</span>
          <Target size={22} />
          <h3>Tell us your goal</h3>
          <p>Your needs, your preferences, your budget.</p>
        </div>
        <div className="how-step">
          <span>02</span>
          <Wallet size={22} />
          <h3>Review a thoughtful plan</h3>
          <p>Compare the choices and see the evidence.</p>
        </div>
        <div className="how-step">
          <span>03</span>
          <Send size={22} />
          <h3>You give the go-ahead</h3>
          <p>Approve your purchase. We handle the next steps.</p>
        </div>
      </section>
    </>
  );
}
function ShieldSymbol() {
  return <Check size={14} />;
}
