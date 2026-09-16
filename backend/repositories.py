from typing import Any, TypeVar

from sqlalchemy.orm import Session

from backend.errors import DomainError

T = TypeVar("T")


def required(db: Session, model: type[T], identity: Any) -> T:
    """Load a required record through the writer. Replica routing belongs on read-only queries."""
    row = db.get(model, identity)
    if row is None:
        raise DomainError("Requested record not found.", 404, "not_found")
    return row
