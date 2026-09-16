"""Explicit operator provisioning; never enable public arbitrary-role signup."""

import argparse
import getpass

from pwdlib import PasswordHash

from backend.db import Session
from backend.models import Cart, Role, User

parser = argparse.ArgumentParser()
parser.add_argument("email")
parser.add_argument("name")
parser.add_argument(
    "--role", choices=["CUSTOMER", "BUSINESS_USER", "SUPPORT_AGENT", "MANAGER", "ADMIN"], default="CUSTOMER"
)
args = parser.parse_args()
password = getpass.getpass("New account password (12+ characters): ")
if len(password) < 12:
    raise SystemExit("Use at least 12 characters")
with Session.begin() as db:
    if not db.get(Role, args.role):
        db.add(Role(name=args.role))
        db.flush()
    user = User(
        email=args.email.lower(),
        name=args.name,
        role=args.role,
        password_hash=PasswordHash.recommended().hash(password),
    )
    db.add(user)
    db.flush()
    db.add(Cart(user_id=user.id))
print("Account provisioned")
