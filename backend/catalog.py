import time

from sqlalchemy import select

from backend.cache import cache
from backend.db import Session
from backend.errors import DomainError
from backend.models import Coupon, Inventory, Product, Review
from backend.repositories import required


def serialize_product(product, stock: int) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "price": product.price,
        "rating": product.rating,
        "stock": stock,
        "warranty_months": product.warranty_months,
        "delivery_days": product.delivery_days,
        "description": product.description,
        "specs": product.specs,
        "color": product.color,
        "seller": "ShopPilot Demo Studio",
        "source": f"catalog://{product.id}",
        "synthetic": True,
    }


def get_product(product_id: str) -> dict:
    cached = cache.get(f"product:{product_id}")
    if cached:
        return cached
    with Session() as db:
        product = required(db, Product, product_id)
        if not product:
            raise DomainError("Product not found.", 404)
        result = serialize_product(product, required(db, Inventory, product_id).available)
    cache.set(f"product:{product_id}", result, 60)
    return result


def search_products(query: str = "", category: str = "", max_price: int = 10000000) -> list[dict]:
    # Cache product identifiers; stock is separately refreshed on every transactional use.
    key = f"search:{query.lower()}:{category}:{max_price}"
    ids = cache.get(key)
    if ids is None:
        with Session() as db:
            statement = select(Product).where(Product.price <= max_price)
            if category:
                statement = statement.where(Product.category == category)
            if query:
                statement = statement.where(
                    (Product.name.ilike(f"%{query}%"))
                    | (Product.description.ilike(f"%{query}%"))
                    | (Product.category.ilike(f"%{query}%"))
                )
            ids = [p.id for p in db.scalars(statement.order_by(Product.rating.desc(), Product.price)).all()]
        cache.set(key, ids, 120)
    return [get_product(pid) for pid in ids]


def reviews(product_id: str) -> list[dict]:
    with Session() as db:
        return [
            {
                "id": r.id,
                "rating": r.rating,
                "text": r.text,
                "verified": r.verified,
                "source": f"catalog://{product_id}/review",
            }
            for r in db.scalars(select(Review).where(Review.product_id == product_id)).all()
        ]


def coupon_for(db, subtotal: int, code: str | None = None) -> dict:
    coupons = db.scalars(
        select(Coupon).where(Coupon.minimum <= subtotal, Coupon.expires_at > time.time())
    ).all()
    if code:
        coupons = [c for c in coupons if c.code == code.upper()]
        if not coupons:
            raise DomainError("Coupon is invalid, expired, or below its minimum spend.")
    best = max(coupons, key=lambda c: min(subtotal * c.percent // 100, c.max_discount), default=None)
    return {
        "code": best.code if best else None,
        "discount": min(subtotal * best.percent // 100, best.max_discount) if best else 0,
    }
