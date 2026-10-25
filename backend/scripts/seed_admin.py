"""Create the first admin account.

Step 1: create the user in Supabase (Dashboard -> Authentication -> Add user), or let this
        script invite them when SUPABASE_SERVICE_ROLE_KEY is configured (--invite).
Step 2: run from backend/:
        python -m scripts.seed_admin --email owner@example.com [--invite]

Grants the ADMIN role by linking the Supabase Auth user to an application profile.
Requires direct database access (DATABASE_URL), so it is never exposed over HTTP.
"""

import argparse
import sys
from uuid import UUID

from app.config import get_settings
from app.db.client import Database
from app.integrations.supabase_auth import SupabaseAuthClient
from app.repositories.user_repository import UserRepository
from app.services.audit_service import record_audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Grant the ADMIN role to a Supabase Auth user")
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--invite", action="store_true", help="invite the user first (needs service key)"
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    db = Database(settings.database_url.get_secret_value(), min_size=1, max_size=1)
    db.open(wait=True)
    try:
        user_id: UUID | None = None
        if args.invite:
            client = SupabaseAuthClient(
                settings.supabase_url,
                settings.supabase_publishable_key,
                settings.supabase_service_role_key.get_secret_value(),
            )
            try:
                user_id = client.invite_user(args.email)
            finally:
                client.close()
        with db.transaction() as conn:
            users = UserRepository(conn)
            user_id = user_id or users.find_auth_user_id(args.email)
            if user_id is None:
                print(
                    f"No Supabase Auth user found for {args.email}. Create it first.",
                    file=sys.stderr,
                )
                return 1
            existing = users.get(user_id)
            if existing is not None:
                print(f"{args.email} already has the {existing['role']} role; nothing changed.")
                return 0
            users.insert({"user_id": user_id, "email": args.email, "role": "ADMIN"})
            record_audit(
                conn,
                actor_id=None,
                action="user.admin_seeded",
                entity_type="user_profile",
                entity_id=user_id,
                after={"email": args.email, "role": "ADMIN"},
            )
        print(f"{args.email} is now an ADMIN.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
