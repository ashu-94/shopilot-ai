import { useState, useRef, useLayoutEffect } from "react";
import { NavLink, Outlet, Link, useLocation } from "react-router-dom";
import {
  Activity,
  ArrowUpRight,
  BriefcaseBusiness,
  ChevronDown,
  Compass,
  GitCompareArrows,
  HelpCircle,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Search,
  ShieldCheck,
  ShoppingBag,
  ShoppingCart,
  Sparkles,
  Undo2,
  X,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, post } from "./api";
import { Brand, Notice } from "./components";
import { useSession } from "./store";
import type { Cart } from "./types";

const primary = [
  ["/", "Overview", LayoutDashboard],
  ["/missions", "Mission planner", Sparkles],
  ["/shop", "Explore products", ShoppingBag],
  ["/compare", "Compare", GitCompareArrows],
  ["/orders", "My orders", Package],
  ["/procurement", "Business procurement", BriefcaseBusiness],
] as const;
export function Layout() {
  const [open, setOpen] = useState(false),
    location = useLocation(),
    session = useSession(),
    client = useQueryClient();
  const { data: cart } = useQuery({
    queryKey: ["cart"],
    queryFn: () => api<Cart>("/cart"),
    enabled: !!session.user,
  });
  const menuButton = useRef<HTMLButtonElement>(null);
  const sidebar = useRef<HTMLElement>(null);
  const mainShell = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    if (!open) return;
    const openedPath = location.pathname;
    // Move focus after the 200 ms drawer transition; restore it after inert styling clears.
    const focusTimer = window.setTimeout(
      () =>
        sidebar.current
          ?.querySelector<HTMLButtonElement>("button")
          ?.focus({ preventScroll: true }),
      220,
    );
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        menuButton.current?.focus();
      }
      if (event.key === "Tab") {
        const items = Array.from(
          sidebar.current?.querySelectorAll<HTMLElement>(
            "a[href], button:not([disabled])",
          ) || [],
        ).filter((el) => el.getClientRects().length);
        const first = items[0],
          last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    if (mainShell.current) mainShell.current.inert = true;
    document.addEventListener("keydown", handler);
    return () => {
      window.clearTimeout(focusTimer);
      document.removeEventListener("keydown", handler);
      if (mainShell.current) mainShell.current.inert = false;
      window.setTimeout(() => {
        if (window.location.pathname === openedPath)
          menuButton.current?.focus();
      }, 220);
    };
  }, [open]);
  useLayoutEffect(() => {
    document.querySelector<HTMLElement>("#main-content")?.focus();
  }, [location.pathname]);
  const notices = useQuery({
    queryKey: ["notifications"],
    queryFn: () =>
      api<{ id: string; message: string; order_id: string; read: boolean }[]>(
        "/notifications",
      ),
    enabled: !!session.user,
    refetchInterval: 30000,
  });
  const elevated = ["ADMIN", "MANAGER"].includes(session.user?.role || "");
  const active = primary.find(([to]) =>
    to === "/" ? location.pathname === "/" : location.pathname.startsWith(to),
  );
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <aside
        ref={sidebar}
        id="navigation-panel"
        aria-label="Workspace navigation"
        className={`sidebar ${open ? "open" : ""}`}
      >
        <div className="sidebar-top">
          <Brand />
          <button
            className="mobile-only icon-button"
            onClick={() => setOpen(false)}
            aria-label="Close navigation"
          >
            <X />
          </button>
        </div>
        <Link to="/missions" className="workspace-label">
          <span className="workspace-icon">
            <Compass size={18} />
          </span>
          <span>
            Your workspace
            <small>
              {session.user?.role === "BUSINESS_USER"
                ? "Business account"
                : "Personal shopping"}
            </small>
          </span>
          <ChevronDown size={15} />
        </Link>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Workspace">
          {primary.map(([to, label, Icon]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setOpen(false)}
            >
              <Icon size={19} />
              {label}
              {to === "/missions" && <span className="nav-new">AI</span>}
            </NavLink>
          ))}
        </nav>
        <div className="nav-label spaced">MANAGE</div>
        <nav aria-label="Account management">
          <NavLink to="/approvals" onClick={() => setOpen(false)}>
            <ShieldCheck size={19} />
            Approval center
          </NavLink>
          <NavLink to="/returns" onClick={() => setOpen(false)}>
            <Undo2 size={19} />
            Returns & refunds
          </NavLink>
          <NavLink to="/support" onClick={() => setOpen(false)}>
            <HelpCircle size={19} />
            Help & support
          </NavLink>
          {elevated && (
            <NavLink to="/operations">
              <Activity size={19} />
              AI operations
            </NavLink>
          )}
          {session.user?.role === "ADMIN" && (
            <NavLink to="/admin">
              <LayoutDashboard size={19} />
              Admin dashboard
            </NavLink>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-callout">
            <div className="callout-icon">
              <Sparkles size={18} />
            </div>
            <strong>Big goals. Smart choices.</strong>
            <p>Build a whole setup around what matters to you.</p>
            <Link to="/missions">
              Plan your next mission <ArrowUpRight size={16} />
            </Link>
          </div>
          <div className="environment">
            <span />
            Demo workspace <span className="demo-tag">LOCAL</span>
          </div>
        </div>
      </aside>
      {open && (
        <div className="sidebar-backdrop" onClick={() => setOpen(false)} />
      )}
      <div className="main-shell" ref={mainShell}>
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="mobile-only icon-button"
              onClick={() => setOpen(true)}
              aria-label="Open navigation"
              ref={menuButton}
              aria-expanded={open}
              aria-controls="navigation-panel"
            >
              <Menu />
            </button>
            <span>Workspace</span>
            <span className="slash">/</span>
            <strong>
              {active?.[1] ||
                location.pathname.split("/")[1].replaceAll("-", " ")}
            </strong>
          </div>
          <div className="topbar-actions">
            {session.user && (
              <details className="notification-menu">
                <summary aria-label="Order notifications">
                  Updates {notices.data?.filter((n) => !n.read).length || 0}
                </summary>
                <div className="notification-list">
                  <strong>Order updates</strong>
                  {notices.error && <p>Updates are temporarily unavailable.</p>}
                  {notices.data?.slice(0, 10).map((n) => (
                    <Link
                      key={n.id}
                      to={`/orders/${n.order_id}`}
                      onClick={async () => {
                        await post(`/notifications/${n.id}/read`);
                        client.invalidateQueries({
                          queryKey: ["notifications"],
                        });
                      }}
                    >
                      {n.message}
                    </Link>
                  ))}
                  {!notices.data?.length && <p>No updates yet.</p>}
                </div>
              </details>
            )}

            <Link to="/shop" className="header-search">
              <Search size={16} />
              <span>Find something</span>
              <kbd>⌕</kbd>
            </Link>
            <Link to="/cart" className="cart-icon" aria-label="Shopping cart">
              <ShoppingCart size={20} />
              {!!cart?.items.length && <span>{cart.items.length}</span>}
            </Link>
            <div className="topbar-divider" />
            {session.user ? (
              <>
                <div className="avatar">
                  {session.user.name
                    .split(" ")
                    .map((n) => n[0])
                    .join("")}
                </div>
                <span className="profile-name">
                  {session.user.name.split(" ")[0]}
                  <small>
                    {session.user.role.toLowerCase().replace("_", " ")}
                  </small>
                </span>
                <button
                  className="icon-button signout"
                  aria-label="Sign out"
                  title="Sign out"
                  onClick={async () => {
                    await post("/auth/logout");
                    session.clear();
                    client.clear();
                  }}
                >
                  <LogOut size={17} />
                </button>
              </>
            ) : (
              <Link className="button small primary" to="/login">
                Sign in
                <ArrowUpRight size={15} />
              </Link>
            )}
          </div>
        </header>
        <main className="page-content" id="main-content" tabIndex={-1}>
          <Outlet />
        </main>
        <footer className="app-footer">
          <span>
            ShopPilot AI <span>·</span> Thoughtful commerce, one goal at a time.
          </span>
          <span>Synthetic catalog. No real charges.</span>
        </footer>
      </div>
      <Notice />
    </div>
  );
}
