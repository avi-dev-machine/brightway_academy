from typing import Any
from uuid import UUID

from app.repositories.base import BaseRepository, Row


class ReceiptRepository(BaseRepository):
    table = "receipts"

    def get_by_payment(self, payment_id: UUID) -> Row | None:
        return self._one("select * from receipts where payment_id = %s", (payment_id,))

    def next_number(self) -> int:
        return int(self._scalar("select nextval('receipt_number_seq')"))

    def create_if_absent(
        self,
        *,
        receipt_number: str,
        payment_id: UUID,
        student_id: UUID,
        fee_id: UUID,
        amount_paise: int,
    ) -> Row:
        row = self._one(
            "insert into receipts (receipt_number, payment_id, student_id, fee_id, amount_paise)"
            " values (%s, %s, %s, %s, %s) on conflict (payment_id) do nothing returning *",
            (receipt_number, payment_id, student_id, fee_id, amount_paise),
        )
        if row is None:
            row = self.get_by_payment(payment_id)
        assert row is not None
        return row

    def set_pdf_path(self, receipt_id: UUID, path: str) -> None:
        self.conn.execute(
            "update receipts set pdf_path = %s where id = %s and pdf_path is null",
            (path, receipt_id),
        )

    def search(self, *, student_id: UUID | None, limit: int, offset: int) -> tuple[list[Row], int]:
        params: list[Any] = []
        where = ""
        if student_id is not None:
            where = "where student_id = %s"
            params.append(student_id)
        total = self._scalar(f"select count(*) from receipts {where}", params)
        rows = self._all(
            f"select * from receipts {where} order by issued_at desc, id limit %s offset %s",
            [*params, limit, offset],
        )
        return rows, int(total or 0)

    def detail(self, receipt_id: UUID) -> Row | None:
        return self._one(
            """
            select r.*, p.provider, p.method, p.provider_payment_id, p.reference, p.paid_at,
                   f.title as fee_title, f.amount_paise as fee_amount_paise,
                   f.concession_paise as fee_concession_paise, f.paid_paise as fee_paid_paise,
                   s.id_no, s.name as student_name, s.guardian_name, c.name as course_name
            from receipts r
            join payments p on p.id = r.payment_id
            join fees f on f.id = r.fee_id
            join students s on s.id = r.student_id
            left join courses c on c.id = s.course_id
            where r.id = %s
            """,
            (receipt_id,),
        )
