import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { restoreSession } from "./api";
import { Layout } from "./layout";
import { Empty, Loading } from "./components";
import Home from "./pages/Home";
import Auth from "./pages/Auth";
import Mission from "./pages/Mission";
import Shop, { Compare, ProductDetail } from "./pages/Shop";
import { CartPage, OrderDetail, Orders, Returns } from "./pages/Commerce";
import { Admin, Approvals, Operations } from "./pages/Operations";
import "./styles.css";

const client = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 15000, refetchOnWindowFocus: false },
  },
});
function App() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    restoreSession().finally(() => setReady(true));
  }, []);
  if (!ready) return <Loading />;
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Auth />} />
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="/shop" element={<Shop />} />
          <Route path="/products/:id" element={<ProductDetail />} />
          <Route path="/missions" element={<Mission />} />
          <Route path="/assistant" element={<Mission />} />
          <Route path="/procurement" element={<Mission mode="procurement" />} />
          <Route path="/support" element={<Mission mode="support" />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CartPage checkout />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/orders/:id" element={<OrderDetail />} />
          <Route path="/tracking/:id" element={<OrderDetail />} />
          <Route path="/returns" element={<Returns />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/operations" element={<Operations />} />
          <Route path="/admin" element={<Admin />} />
          <Route
            path="*"
            element={
              <Empty
                title="This page took a different path."
                text="Head back to your workspace to keep going."
                to="/"
                label="Back to overview"
              />
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
