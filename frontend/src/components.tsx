import productPhotos from "./product-photos.json";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Armchair,
  ArrowRight,
  Check,
  CheckCheck,
  ChevronRight,
  Headphones,
  Laptop,
  LoaderCircle,
  Monitor,
  Mouse,
  Package,
  Plus,
  ShieldCheck,
  ShoppingBag,
  Star,
  Table2,
  Tv,
  Keyboard,
  Webcam,
  Zap,
  X,
  GitCompareArrows,
} from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, money } from "./api";
import { useCompare, useNotice, useSession } from "./store";
import type { Cart, Evidence, Product } from "./types";

export function Brand() {
  return (
    <Link to="/" className="brand">
      <span className="brand-icon">
        <ShoppingBag size={22} />
      </span>
      <span>
        shopilot<span className="brand-dot">.</span>
      </span>
    </Link>
  );
}
export const categoryName = (s: string) =>
  ({
    ups: "UPS",
    tv: "Televisions",
    appliance: "Appliances",
    mouse: "Mice",
    chair: "Chairs",
    desk: "Desks",
  })[s] || s.charAt(0).toUpperCase() + s.slice(1) + "s";
export function ProductArt({
  product,
  large = false,
}: {
  product: Product;
  large?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const photo = (productPhotos as Record<string, {src:string}>)[product.id];
  const Icon =
    (
      {
        laptop: Laptop,
        monitor: Monitor,
        chair: Armchair,
        keyboard: Keyboard,
        mouse: Mouse,
        ups: Zap,
        desk: Table2,
        headphones: Headphones,
        tv: Tv,
        soundbar: Headphones,
        webcam: Webcam,
      } as Record<string, typeof Laptop>
    )[product.category] || Package;
  return (
    <div
      className={`product-art ${large ? "large" : ""} ${photo && !failed ? "photographic" : ""}`}
      style={{ background: product.color }}
    >
      {photo && !failed ? <img src={photo.src} alt={`${product.category === "appliance" ? product.name.includes("Washer") ? "Washing machine" : "Refrigerator" : categoryName(product.category)} — representative photo for ${product.name}`} loading={large ? "eager" : "lazy"} decoding="async" onError={() => setFailed(true)} /> : <Icon size={large ? 140 : 78} strokeWidth={1.1} />}
      <span className="art-caption">
        {photo && !failed ? "Representative photo" : "Photo unavailable"}
      </span>
    </div>
  );
}
export function ProductCard({
  product,
  compact = false,
}: {
  product: Product;
  compact?: boolean;
}) {
  const compare = useCompare(),
    notice = useNotice(),
    client = useQueryClient(),
    user = useSession((s) => s.user);
  const add = useMutation({
    mutationFn: async () => {
      const cart = await api<Cart>("/cart");
      const exists = cart.items.find((i) => i.product_id === product.id);
      return api("/cart", {
        method: "PUT",
        body: JSON.stringify({
          items: [
            ...cart.items
              .filter((i) => i.product_id !== product.id)
              .map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
            { product_id: product.id, quantity: (exists?.quantity || 0) + 1 },
          ],
        }),
      });
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["cart"] });
      notice.show(`${product.name} added to your cart`);
    },
    onError: (e: Error) => notice.show(e.message),
  });
  return (
    <article className={`product-card ${compact ? "compact" : ""}`}>
      <Link to={`/products/${product.id}`} className="art-link">
        <ProductArt product={product} />
      </Link>
      <button
        className={`compare-toggle ${compare.ids.includes(product.id) ? "selected" : ""}`}
        onClick={() => compare.toggle(product.id)}
        aria-label={`Compare ${product.name}`}
        aria-pressed={compare.ids.includes(product.id)}
      >
        <GitCompareArrows size={16} />
      </button>
      <div className="product-copy">
        <div className="eyebrow">
          {categoryName(product.category)}
          <span className="rating">
            <Star size={12} fill="currentColor" />
            {product.rating}
          </span>
        </div>
        <Link to={`/products/${product.id}`} className="product-name">
          {product.name}
        </Link>
        <p>
          {product.category === "laptop"
            ? `${product.specs.ram_gb} GB RAM · ${product.specs.ssd_gb} GB SSD`
            : product.description}
        </p>
        <div className="product-bottom">
          <strong>{money(product.price)}</strong>
          <button
            className="add-button"
            onClick={() =>
              user
                ? add.mutate()
                : notice.show("Sign in to add products to your cart")
            }
            disabled={add.isPending || product.stock === 0}
            aria-label={`Add ${product.name} to cart`}
          >
            {add.isPending ? (
              <LoaderCircle className="spin" size={17} />
            ) : (
              <Plus size={18} />
            )}
          </button>
        </div>
      </div>
    </article>
  );
}
export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow green">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}
export function Empty({
  title,
  text,
  to,
  label,
}: {
  title: string;
  text: string;
  to?: string;
  label?: string;
}) {
  return (
    <div className="empty panel">
      <ShoppingBag size={34} />
      <h2>{title}</h2>
      <p>{text}</p>
      {to && (
        <Link className="button primary" to={to}>
          {label || "Start a mission"}
          <ArrowRight size={16} />
        </Link>
      )}
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading">
      <LoaderCircle className="spin" />
      Loading your workspace…
    </div>
  );
}
export function ErrorState({ error }: { error: Error }) {
  return (
    <div role="alert" className="error-box">
      {error.message}
    </div>
  );
}
export function Status({ value }: { value: string }) {
  return (
    <span
      className={`status ${["failed", "rejected", "cancelled"].includes(value) ? "bad" : ["pending", "needs_info", "awaiting_approval", "running", "queued"].includes(value) ? "pending" : ""}`}
    >
      {value.replaceAll("_", " ")}
    </span>
  );
}
export function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  return (
    <div className="evidence-list">
      {evidence.map((e) => (
        <details key={e.id}>
          <summary>
            <ShieldCheck size={16} />
            {e.title}
            <ChevronRight size={15} />
          </summary>
          <p>{e.text}</p>
          <code>{e.source}</code>
        </details>
      ))}
    </div>
  );
}
export function Notice() {
  const notice = useNotice();
  useEffect(() => {
    if (!notice.text) return;
    const timer = setTimeout(notice.clear, 6000);
    return () => clearTimeout(timer);
  }, [notice.text, notice.clear]);
  return notice.text ? (
    <div className="toast" role="status">
      <CheckCheck size={18} />
      {notice.text}
      <button aria-label="Dismiss notification" onClick={notice.clear}>
        <X size={16} />
      </button>
    </div>
  ) : null;
}
export function TrustStrip() {
  return (
    <div className="trust-strip">
      <span>
        <ShieldCheck size={15} />
        Evidence-backed picks
      </span>
      <span>
        <Check size={15} />
        You approve every purchase
      </span>
      <span>
        <Zap size={15} />
        Safe simulated payments
      </span>
    </div>
  );
}
