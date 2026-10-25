from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from app.repositories.base import BaseRepository, Row


class PaymentRepository(BaseRepository):
    table = "payments"

    def get_by_order_id(self, order_id: str, *, for_update: bool = False) -> Row | None:
        query = "select * from payments where provider_order_id = %s"
        if for_update:
            query += " for update"
        return self._one(query, (order_id,))

    def get_by_provider_payment_id(self, provider_payment_id: str) -> Row | None:
        return self._one(
            "select * from payments where provider_payment_id = %s", (provider_payment_id,)
        )

    def get_by_idempotency_key(self, key: str) -> Row | None:
        return self._one("select * from payments where idempotency_key = %s", (key,))

    def find_open_order(
        self, *, fee_id: UUID, amount_paise: int, provider: str, created_after: datetime
    ) -> Row | None:
        """A recent unpaid order for the same fee and amount, reused instead of a new order."""
        return self._one(
            "select * from payments where fee_id = %s and amount_paise = %s and provider = %s"
            " and status = 'CREATED' and provider_order_id is not null and created_at >= %s"
            " order by created_at desc limit 1",
            (fee_id, amount_paise, provider, created_after),
        )

    def search(
        self,
        *,
        student_id: UUID | None,
        fee_id: UUID | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Row], int]:
        conditions: list[str] = []
        params: list[Any] = []
        for column, value in (("student_id", student_id), ("fee_id", fee_id), ("status", status)):
            if value is not None:
                conditions.append(f"{column} = %s")
                params.append(value)
        where = f"where {' and '.join(conditions)}" if conditions else ""
        total = self._scalar(f"select count(*) from payments {where}", params)
        rows = self._all(
            f"select * from payments {where} order by created_at desc, id limit %s offset %s",
            [*params, limit, offset],
        )
        return rows, int(total or 0)


class PaymentEventRepository(BaseRepository):
    table = "payment_events"

    def insert_if_new(
        self, *, provider: str, event_id: str, event_type: str, payload: dict[str, Any]
    ) -> Row | None:
        return self._one(
            "insert into payment_events (provider, event_id, event_type, payload)"
            " values (%s, %s, %s, %s) on conflict (provider, event_id) do nothing returning *",
            (provider, event_id, event_type, Jsonb(payload)),
        )

    def get(self, provider: str, event_id: str) -> Row | None:
        return self._one(
            "select * from payment_events where provider = %s and event_id = %s",
            (provider, event_id),
        )

    def mark(self, event_row_id: UUID, *, status: str, result: str) -> None:
        self.conn.execute(
            "update payment_events set status = %s, result = %s, processed_at = now()"
            " where id = %s",
            (status, result, event_row_id),
        )
