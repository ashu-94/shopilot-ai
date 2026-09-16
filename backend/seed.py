import time

from pwdlib import PasswordHash
from sqlalchemy import select

from backend.config import settings
from backend.db import Session
from backend.models import (
    Cart,
    Category,
    Coupon,
    Inventory,
    KnowledgeDocument,
    Product,
    ProductSpecification,
    Review,
    Role,
    Seller,
    User,
)

CATALOG: list[tuple[str, str, int, float, int, int, dict, str]] = [
    (
        "laptop",
        "NovaBook Pro 14",
        74900,
        4.8,
        45,
        36,
        {
            "ram_gb": 32,
            "ssd_gb": 1024,
            "cpu": "8-core performance",
            "gpu_vram_gb": 8,
            "ports": ["HDMI", "USB-C", "USB-A"],
            "power_w": 120,
        },
        "A portable development workstation for Python, Docker and smaller quantized local models.",
    ),
    (
        "laptop",
        "NovaBook Studio 16",
        99900,
        4.9,
        24,
        36,
        {
            "ram_gb": 64,
            "ssd_gb": 1024,
            "cpu": "12-core performance",
            "gpu_vram_gb": 12,
            "ports": ["HDMI", "USB-C", "USB-A"],
            "power_w": 180,
        },
        "More memory and GPU headroom for demanding creative and AI workloads.",
    ),
    (
        "laptop",
        "Orbit Air 13",
        48900,
        4.4,
        32,
        12,
        {
            "ram_gb": 16,
            "ssd_gb": 512,
            "cpu": "6-core efficient",
            "gpu_vram_gb": 0,
            "ports": ["USB-C"],
            "power_w": 65,
        },
        "Everyday productivity and light development in a compact package.",
    ),
    (
        "monitor",
        "VistaView 27 QHD",
        18900,
        4.7,
        62,
        36,
        {"resolution": "2560 × 1440", "size_inches": 27, "ports": ["HDMI", "USB-C"], "power_w": 45},
        "A sharp IPS display with USB-C and an adjustable stand.",
    ),
    (
        "monitor",
        "VistaView 24 FHD",
        10900,
        4.5,
        70,
        24,
        {"resolution": "1920 × 1080", "size_inches": 24, "ports": ["HDMI"], "power_w": 30},
        "A practical, color-balanced everyday workspace display.",
    ),
    (
        "chair",
        "Forma Ergo Pro",
        16900,
        4.8,
        28,
        36,
        {"lumbar": "adjustable", "material": "breathable mesh", "max_weight_kg": 130, "width_cm": 66},
        "Adjustable lumbar support, a breathable back and all-day comfort.",
    ),
    (
        "chair",
        "Forma Essential",
        8900,
        4.3,
        48,
        12,
        {"lumbar": "fixed", "material": "mesh", "max_weight_kg": 110, "width_cm": 62},
        "Comfortable support for a smaller workspace and budget.",
    ),
    (
        "keyboard",
        "Keyform K75",
        5490,
        4.8,
        80,
        24,
        {"connection": "USB-C / Bluetooth", "layout": "75%", "switches": "tactile", "ports": ["USB-A"]},
        "A quiet mechanical keyboard with a compact, considered layout.",
    ),
    (
        "keyboard",
        "Keyform Lite",
        1890,
        4.2,
        90,
        12,
        {"connection": "USB", "layout": "full-size", "ports": ["USB-A"]},
        "A dependable low-profile keyboard for everyday work.",
    ),
    (
        "mouse",
        "Arc Precision",
        2490,
        4.7,
        100,
        24,
        {"connection": "Bluetooth", "dpi": 4000, "ports": ["USB-A"]},
        "An ergonomic wireless mouse with precise tracking.",
    ),
    (
        "mouse",
        "Arc Go",
        990,
        4.3,
        120,
        12,
        {"connection": "USB", "dpi": 1600, "ports": ["USB-A"]},
        "A simple, comfortable mouse for a focused setup.",
    ),
    (
        "ups",
        "PowerNest 1100",
        7490,
        4.6,
        50,
        24,
        {"capacity_va": 1100, "output_w": 660, "outlets": 4},
        "Power protection and short backup for your desk essentials.",
    ),
    (
        "ups",
        "PowerNest 650",
        4490,
        4.3,
        45,
        24,
        {"capacity_va": 650, "output_w": 390, "outlets": 3},
        "Compact backup power for laptops and monitors.",
    ),
    (
        "desk",
        "Oakline Work 140",
        12900,
        4.7,
        25,
        36,
        {"width_cm": 140, "depth_cm": 70, "height_cm": 74},
        "A generous, clean-lined desk with integrated cable routing.",
    ),
    (
        "desk",
        "Oakline Sit Stand",
        25900,
        4.8,
        16,
        36,
        {"width_cm": 150, "depth_cm": 75, "height_cm": "72–118"},
        "A motorized standing desk that moves with your workday.",
    ),
    (
        "headphones",
        "Hush Audio One",
        4990,
        4.6,
        66,
        12,
        {"connection": "Bluetooth", "noise_canceling": True},
        "Soft over-ear headphones for focused listening and clear calls.",
    ),
    (
        "headphones",
        "Hush Studio",
        8990,
        4.8,
        44,
        24,
        {"connection": "USB-C / Bluetooth", "noise_canceling": True},
        "A comfortable headset with a dedicated meeting microphone.",
    ),
    (
        "tv",
        "Prism 55 OLED",
        74900,
        4.8,
        18,
        24,
        {"size_inches": 55, "resolution": "4K", "ports": ["HDMI", "eARC"]},
        "A cinematic OLED screen for rich contrast and movie nights.",
    ),
    (
        "tv",
        "Prism 43 LED",
        28900,
        4.4,
        24,
        24,
        {"size_inches": 43, "resolution": "4K", "ports": ["HDMI", "eARC"]},
        "A versatile smart display for everyday entertainment.",
    ),
    (
        "soundbar",
        "Resonance Beam",
        14900,
        4.6,
        35,
        12,
        {"channels": "2.1", "ports": ["HDMI", "eARC"], "power_w": 100},
        "Fuller dialogue and balanced sound in a compact soundbar.",
    ),
    (
        "appliance",
        "Frostwell 320 Refrigerator",
        38900,
        4.5,
        20,
        24,
        {"capacity_l": 320, "energy_rating": 4, "compressor": "inverter"},
        "A quiet inverter refrigerator with flexible storage.",
    ),
    (
        "appliance",
        "PureCycle 8 Washer",
        32900,
        4.6,
        22,
        24,
        {"capacity_kg": 8, "energy_rating": 5},
        "Efficient washing with simple controls and a gentle cycle.",
    ),
    (
        "webcam",
        "Frame HD",
        3490,
        4.5,
        60,
        12,
        {"resolution": "1080p", "ports": ["USB-A"]},
        "Clear video calls with a privacy shutter.",
    ),
]


def seed() -> None:
    with Session.begin() as db:
        if db.scalar(select(User.id).limit(1)):
            return
        roles = ["CUSTOMER", "BUSINESS_USER", "SUPPORT_AGENT", "MANAGER", "ADMIN"]
        db.add_all([Role(name=r) for r in roles])
        db.add_all([Category(name=c) for c in sorted({row[0] for row in CATALOG})])
        db.add(Seller(id="seller-studio", name="ShopPilot Demo Studio"))
        db.flush()
        for email, name, role in [
            ("alex@shopilot.demo", "Alex Morgan", "CUSTOMER"),
            ("business@shopilot.demo", "Jordan Ellis", "BUSINESS_USER"),
            ("manager@shopilot.demo", "Morgan Chen", "MANAGER"),
            ("admin@shopilot.demo", "Sam Rivera", "ADMIN"),
            ("support@shopilot.demo", "Casey Quinn", "SUPPORT_AGENT"),
        ]:
            user = User(
                email=email,
                name=name,
                role=role,
                password_hash=PasswordHash.recommended().hash(settings().demo_password),
            )
            db.add(user)
            db.flush()
            db.add(Cart(user_id=user.id))
        for i, (category, name, price, rating, stock, warranty, specs, description) in enumerate(CATALOG):
            pid = f"product-{i + 1:03}"
            product = Product(
                id=pid,
                name=name,
                category=category,
                price=price,
                rating=rating,
                warranty_months=warranty,
                delivery_days=4 + i % 4,
                specs=specs,
                description=description,
                seller_id="seller-studio",
                color=["#edf0f6", "#eee9e2", "#e4ede9", "#ece8f3"][i % 4],
            )
            db.add(product)
            db.flush()
            db.add(Inventory(product_id=pid, available=stock))
            db.add_all([ProductSpecification(product_id=pid, name=k, value=str(v)) for k, v in specs.items()])
            review = f"Synthetic verified review: {name} feels well built. {description} Packaging could be better."
            db.add(Review(product_id=pid, rating=round(rating), text=review))
            documents = {
                "description": description,
                "specifications": "; ".join(f"{k}: {v}" for k, v in specs.items()),
                "review": review,
                "warranty": f"{name}: {warranty} month limited warranty for manufacturing defects. Accidental damage is excluded.",
                "return_policy": "Returns or replacements may be requested within 30 days of purchase for damaged or defective items. Inspection may be required. Whole-order returns only in this demo.",
                "manual": f"{name}: disconnect power before inspecting cables. Do not open electrical housings. For unusual noise, check stable placement and contact support if it persists.",
                "faq": "All catalog entries, ratings and policies are synthetic demonstration data. Shipping estimates are simulated, not delivery promises.",
            }
            for kind, content in documents.items():
                db.add(
                    KnowledgeDocument(
                        product_id=pid,
                        kind=kind,
                        title=f"{name} · {kind.replace('_', ' ')}",
                        text=content,
                        source=f"catalog://{pid}/{kind}",
                    )
                )
        db.add(
            Coupon(
                code="WORKSPACE5",
                percent=5,
                minimum=50000,
                max_discount=5000,
                expires_at=time.time() + 365 * 86400,
            )
        )
