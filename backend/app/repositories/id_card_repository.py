from uuid import UUID

from app.repositories.base import BaseRepository, Row


class IdCardTemplateRepository(BaseRepository):
    table = "id_card_templates"

    def get_default(self) -> Row | None:
        return self._one("select * from id_card_templates where is_default and active")

    def search(self) -> list[Row]:
        return self._all("select * from id_card_templates order by is_default desc, lower(name)")

    def clear_default(self) -> None:
        self.conn.execute("update id_card_templates set is_default = false where is_default")


class IdCardRepository(BaseRepository):
    table = "id_cards"

    def list_for_student(self, student_id: UUID) -> list[Row]:
        return self._all(
            "select * from id_cards where student_id = %s order by generated_at desc",
            (student_id,),
        )
