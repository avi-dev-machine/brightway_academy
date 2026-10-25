"""Notification delivery job: drain the queue in batches."""

import logging

from app.schemas.notification import ProcessResult
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

MAX_BATCHES_PER_RUN = 20


def process_notifications(service: NotificationService, batch_size: int = 50) -> ProcessResult:
    total = ProcessResult()
    for _ in range(MAX_BATCHES_PER_RUN):
        batch = service.process_due(batch_size)
        for field in ProcessResult.model_fields:
            setattr(total, field, getattr(total, field) + getattr(batch, field))
        if batch.claimed < batch_size:
            break
    if total.claimed:
        logger.info(
            "notifications processed", extra={"operation": "notifications", **total.model_dump()}
        )
    return total
