export type User = { id: string; name: string; email: string; role: string };
export type Evidence = {
  id: string;
  kind: string;
  title: string;
  text: string;
  source: string;
  score: number;
};
export type Product = {
  review_analysis?: {sample_size:number; verified_count:number; confidence:string; duplicate_text_count:number; aspects:Record<string,{mentions:number; average_rating:number}>};
  id: string;
  name: string;
  category: string;
  price: number;
  rating: number;
  stock: number;
  warranty_months: number;
  delivery_days: number;
  description: string;
  specs: Record<string, string | number | boolean | string[]>;
  color: string;
  source: string;
  reason?: string;
  evidence?: Evidence[];
  reviews?: { text: string; rating: number }[];
};
export type Line = {
  amount?: number;
  product_id: string;
  quantity: number;
  returnable_quantity?: number;
  unit_price: number;
  product: Product;
};
export type Cart = {
  items: Line[];
  subtotal: number;
  discount: number;
  total: number;
  coupon?: string;
  shipping: number;
};
export type Order = {
  id: string;
  number: string;
  status: string;
  total: number;
  discount: number;
  kind: string;
  created_at: number;
  address: string;
  items: Line[];
  payment: { status: string; provider: string; reference: string };
  shipments: {
    tracking_code: string;
    status: string;
    estimated_days: number;
    kind: string;
  }[];
};
export type Bundle = {
  products: Product[];
  subtotal: number;
  total: number;
  discount: number;
  coupon: string;
  budget: number;
  remaining: number;
  quantity: number;
  returnable_quantity?: number;
  warnings: string[];
  explanation: string;
  provider: string;
  alternative: { products: Product[]; subtotal: number };
};
export type Execution = {
  id: string;
  kind: string;
  query: string;
  status: string;
  result: Partial<Bundle> & {
    order?: Order;
    return?: { id: string; status: string; resolution: string; amount: number };
    answer?: string;
    evidence?: Evidence[];
    ticket_id?: string;
  };
  error?: string;
  created_at: number;
  duration_ms: number;
  tokens: number;
};
export type Approval = {
  procurement?: Record<string,string>;
  id: string;
  execution_id: string;
  amount: number;
  reason: string;
  risk_score: number;
  required_role: string;
  status: string;
  feedback: string;
  customer: string;
  kind: string;
  can_decide: boolean;
  quote: Cart;
};
export type ProgressEvent = { id: number; stage: string; message: string };
