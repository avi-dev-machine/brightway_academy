from pydantic import BaseModel


class ProcessResult(BaseModel):
    claimed: int = 0
    sent: int = 0
    retried: int = 0
    failed: int = 0
    skipped: int = 0


class ReminderRunResult(BaseModel):
    checked: int = 0
    queued: int = 0
    already_sent: int = 0
    skipped_no_contact: int = 0
