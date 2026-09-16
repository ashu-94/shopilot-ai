import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  GitCompareArrows,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Star,
  Truck,
} from "lucide-react";
import { api, money } from "../api";
import {
  Empty,
  ErrorState,
  Loading,
  PageHeading,
  ProductArt,
  ProductCard,
  categoryName,
} from "../components";
import { useCompare, useNotice, useSession } from "../store";
import type { Cart, Product } from "../types";

export default function Shop() {
  const [query, setQuery] = useState(""),
    [category, setCategory] = useState(""),
    [sort, setSort] = useState("recommended");
  const {
    data = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ["products"],
    queryFn: () => api<Product[]>("/products"),
  });
  const products = data
    .filter(
      (p) =>
        (!category || p.category === category) &&
        `${p.name} ${p.description} ${p.category}`
          .toLowerCase()
          .includes(query.toLowerCase()),
    )
    .sort((a, b) =>
      sort === "price"
        ? a.price - b.price
        : sort === "rating"
          ? b.rating - a.rating
          : 0,
    );
  return (
    <>
      <section className="collection-hero" aria-labelledby="collection-title">
        <div className="collection-hero-copy">
          <span className="collection-kicker">THE EVERYDAY, UPGRADED</span>
          <h1 id="collection-title">Good things.<br/><em>Great possibilities.</em></h1>
          <p>Find your focus. Make room for comfort. Discover a setup that feels like you.</p>
          <Link to="/missions" className="collection-cta">Build my perfect setup <ArrowRight size={18}/></Link>
          <div className="collection-pills"><span>Work smarter</span><span>Live comfortably</span><span>Find your flow</span></div>
        </div>
        <div className="collection-visual" aria-hidden="true">
          <img src="/images/products/product-016.jpg" alt="" className="hero-headphones"/>
          <div className="hero-photo-note"><span>THE FOCUS EDIT</span><strong>A little less noise.<br/>A lot more you.</strong></div>
          <span className="hero-orbit">Made for<br/><b>your everyday.</b></span>
        </div>
      </section>
      <div className="collection-intro"><div><span className="eyebrow">EXPLORE THE COLLECTION</span><h2>Your next favorite starts here.</h2></div><a href="/photo-credits.html" className="photo-credit-link">Real photography · Photo credits ↗</a></div>
      <div className="shop-toolbar">
        <div className="search-field">
          <Search size={18} />
          <input
            placeholder="Search the collection…"
            aria-label="Search products"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="sort-field">
          <SlidersHorizontal size={16} />
          <select
            aria-label="Sort products"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="recommended">Recommended</option>
            <option value="price">Price: low to high</option>
            <option value="rating">Highest rated</option>
          </select>
        </div>
      </div>
      <div className="category-tabs">
        <button
          className={!category ? "active" : ""}
          onClick={() => setCategory("")}
        >
          All products <span>{data.length}</span>
        </button>
        {[...new Set(data.map((p) => p.category))].map((c) => (
          <button
            key={c}
            className={category === c ? "active" : ""}
            onClick={() => setCategory(c)}
          >
            {categoryName(c)}
          </button>
        ))}
      </div>
      <div className="catalog-meta">
        <span>{products.length} thoughtful choices</span>
        <span>Demo products · Representative photos · Prices in INR</span>
      </div>
      {isLoading ? (
        <Loading />
      ) : error ? (
        <ErrorState error={error} />
      ) : products.length ? (
        <div className="product-grid">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      ) : (
        <Empty
          title="No matching products"
          text="Try a different search or category."
        />
      )}
    </>
  );
}
export function ProductDetail() {
  const { id } = useParams();
  const client = useQueryClient(),
    notice = useNotice(),
    user = useSession((s) => s.user);
  const add = useMutation({
    mutationFn: async () => {
      const cart = await api<Cart>("/cart");
      const current = cart.items.find((i) => i.product_id === id);
      return api("/cart", {
        method: "PUT",
        body: JSON.stringify({
          items: [
            ...cart.items
              .filter((i) => i.product_id !== id)
              .map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
            { product_id: id, quantity: (current?.quantity || 0) + 1 },
          ],
        }),
      });
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["cart"] });
      notice.show("Product added to your cart");
    },
    onError: (e: Error) => notice.show(e.message),
  });
  const {
      data: p,
      isLoading,
      error,
    } = useQuery({
      queryKey: ["product", id],
      queryFn: () => api<Product>(`/products/${id}`),
    }),
    compare = useCompare();
  if (isLoading) return <Loading />;
  if (error) return <ErrorState error={error} />;
  if (!p) return null;
  return (
    <>
      <Link className="back-link" to="/shop">
        ← Back to collection
      </Link>
      <div className="product-detail">
        <ProductArt product={p} large />
        <div>
          <span className="eyebrow green">
            {categoryName(p.category)} / DEMO COLLECTION
          </span>
          <h1>{p.name}</h1>
          <div className="detail-rating">
            <Star size={16} fill="currentColor" />
            {p.rating}
            <span>Synthetic verified ratings</span>
          </div>
          <p className="detail-description">{p.description}</p>
          <div className="detail-price">
            {money(p.price)}
            <small>Including demo taxes</small>
          </div>
          <div className="detail-perks">
            <span>
              <Check size={17} />
              {p.stock} available
            </span>
            <span>
              <ShieldCheck size={17} />
              {p.warranty_months}-month warranty
            </span>
            <span>
              <Truck size={17} />
              Estimated {p.delivery_days} days · simulated
            </span>
          </div>
          <div className="bundle-actions">
            <button
              className="button secondary"
              onClick={() => compare.toggle(p.id)}
            >
              <GitCompareArrows size={16} />
              {compare.ids.includes(p.id)
                ? "Remove from comparison"
                : "Add to comparison"}
            </button>
            <button
              className="button primary"
              disabled={add.isPending || p.stock === 0}
              onClick={() =>
                user
                  ? add.mutate()
                  : notice.show("Sign in to add products to your cart")
              }
            >
              {add.isPending ? "Adding…" : "Add to cart"}
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
      <div className="detail-lower">
        <section className="panel">
          <h2>The details that matter</h2>
          <dl className="spec-list">
            {Object.entries(p.specs).map(([k, v]) => (
              <div key={k}>
                <dt>{k.replaceAll("_", " ")}</dt>
                <dd>{Array.isArray(v) ? v.join(", ") : String(v)}</dd>
              </div>
            ))}
          </dl>
          <code>{p.source}</code>
        </section>
        <section className="panel">
          <h2>From the demo community</h2>
          {p.reviews?.map((r, i) => (
            <blockquote key={i}>
              <div className="rating">
                <Star size={14} fill="currentColor" />
                {r.rating}/5
              </div>
              <p>{r.text}</p>
            </blockquote>
          ))}
          <div className="policy-note">
            <ShieldCheck size={19} />
            <p>
              30-day return requests for damaged or defective products.
              Eligibility and approvals are checked when you submit a request.
            </p>
          </div>
        </section>
      </div>
    </>
  );
}
export function Compare() {
  const compare = useCompare();
  const { data = [] } = useQuery({
    queryKey: ["products"],
    queryFn: () => api<Product[]>("/products"),
  });
  const products = data.filter((p) => compare.ids.includes(p.id));
  return (
    <>
      <PageHeading
        eyebrow="A CLEARER PICTURE"
        title="Good choices, side by side."
        description="Compare up to four products using current catalog information."
        action={
          products.length > 0 && (
            <button className="button secondary" onClick={compare.clear}>
              Clear comparison
            </button>
          )
        }
      />
      {!products.length ? (
        <Empty
          title="A little perspective helps."
          text="Select the comparison icon on any product to add it here."
          to="/shop"
          label="Explore products"
        />
      ) : (
        <div className="comparison-scroll panel">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>What matters</th>
                {products.map((p) => (
                  <th key={p.id}>
                    <ProductArt product={p} />
                    <Link to={`/products/${p.id}`}>{p.name}</Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                "Price",
                "Category",
                "Rating",
                "Warranty",
                "Stock",
                "Delivery estimate",
                ...new Set(products.flatMap((p) => Object.keys(p.specs))),
              ].map((k) => (
                <tr key={k}>
                  <th>{k.replaceAll("_", " ")}</th>
                  {products.map((p) => (
                    <td key={p.id}>
                      {k === "Price"
                        ? money(p.price)
                        : k === "Category"
                          ? p.category
                          : k === "Rating"
                            ? p.rating
                            : k === "Warranty"
                              ? `${p.warranty_months} months`
                              : k === "Stock"
                                ? p.stock
                                : k === "Delivery estimate"
                                  ? `${p.delivery_days} days (simulated)`
                                  : p.specs[k] !== undefined
                                    ? String(p.specs[k])
                                    : "Not specified"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
