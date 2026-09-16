import json

import boto3
from botocore.config import Config

from backend.commerce import get_order
from backend.config import settings
from backend.errors import DomainError


def purchase_order(user_id: str, order_id: str) -> dict:
    order = get_order(user_id, order_id)
    if order["kind"] != "procurement":
        raise DomainError("This order is not a procurement purchase.", 409)
    return {
        "document_type": "purchase_order",
        "number": f"PO-{order_id[:12].upper()}",
        "order_number": order["number"],
        "issued_at": order["created_at"],
        "buyer_id": user_id,
        "procurement": order["procurement"],
        "delivery_address": order["address"],
        "currency": "INR",
        "supplier": "ShopPilot Demo Studio",
        "status": order["status"],
        "lines": [
            {
                "sku": i["product_id"],
                "description": i["product"]["name"],
                "quantity": i["quantity"],
                "unit_price": i["unit_price"],
                "warranty_months": i["product"]["warranty_months"],
            }
            for i in order["items"]
        ],
        "discount": order["discount"],
        "total": order["total"],
        "payment_terms": "Simulated settlement only",
        "notice": "Synthetic demonstration document. Not a legally binding purchase order.",
    }


def archive_purchase_order(user_id: str, order_id: str) -> dict:
    document = purchase_order(user_id, order_id)
    if not settings().s3_endpoint_url:
        return {"status": "available_on_demand", "document_number": document["number"]}
    client = boto3.client(
        "s3",
        endpoint_url=settings().s3_endpoint_url,
        config=Config(connect_timeout=3, read_timeout=5, retries={"max_attempts": 1}),
    )
    bucket = settings().s3_bucket
    try:
        client.head_bucket(Bucket=bucket)
    except client.exceptions.ClientError as exc:
        if str(exc.response.get("Error", {}).get("Code")) not in {"404", "NoSuchBucket"}:
            raise
        client.create_bucket(Bucket=bucket)
    key = f"purchase-orders/{user_id}/{order_id}.json"
    client.put_object(
        Bucket=bucket, Key=key, Body=json.dumps(document).encode(), ContentType="application/json"
    )
    return {"status": "archived", "document_number": document["number"], "key": key}
