"""Constants shared across the application."""

from enum import StrEnum

API_V1_PREFIX = "/api/v1"
CURRENCY = "INR"
# Razorpay's minimum order amount is INR 1.00 (100 paise).
MIN_ONLINE_PAYMENT_PAISE = 100
MAX_PAGE_SIZE = 100


class Role(StrEnum):
    ADMIN = "ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"
