# Retrieval and recommendation

Every synthetic product has description, specification, review, warranty, return policy, manual and FAQ documents. Source IDs use `catalog://product-id/document-kind` and are retained through retrieval, recommendation and UI evidence expansion.

Retrieval creates a query rewrite and document-kind plan, fetches document kinds concurrently with product filters, calculates lexical and learned BGE vector similarity in learned mode, optionally obtains Qdrant cosine scores, cross-encoder reranks and diversifies by product/kind, validates source ownership and compresses text into bounded excerpts. No successful evidence means no recommendation. The support path only retrieves documents associated with a matching owned order.

The deterministic recommendation engine filters stock, quantity, budget, laptop RAM/storage/warranty, and delivery limits. It combines rating, warranty, RAM, stock and category preferences. An exact Pareto frontier optimizes the sum of quality scores across required categories under the pre-coupon budget. Coupons then reduce the total. This conservative optimization may miss a higher-quality bundle that fits only after a coupon; that is an explicit limitation.

Compatibility checks cover shared display connections and UPS wattage headroom. Room fit and local-model performance remain caveated rather than inferred. Learned mode uses BAAI/bge-small-en-v1.5 (384 dimensions) and Xenova/ms-marco-MiniLM-L-12-v2 through FastEmbed ONNX on CPU. Collections include model identity; local embeddings are cached and SQL evidence can be ranked when Qdrant is unavailable. Development lexical mode remains available. The 24 authored English paraphrase cases achieve MRR@8 0.8903 and recall@3 0.9583; the set informed model selection and is not held-out validation. Broader independent, multilingual and adversarial relevance data remain necessary.

Review analysis presents verified/sample counts, rating distribution, aspect excerpts and duplicate-text signals with small-sample uncertainty. It makes no fraud or physical-damage diagnosis.
