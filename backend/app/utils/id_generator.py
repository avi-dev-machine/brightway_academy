"""Generation of human-readable student ID numbers for new admissions.

Legacy ID numbers are never changed; generated IDs skip any value already taken.
"""

from collections.abc import Callable

MAX_ATTEMPTS = 1000


def format_student_id(prefix: str, number: int) -> str:
    return f"{prefix}{number:05d}"


def generate_student_id(
    prefix: str, next_number: Callable[[], int], exists: Callable[[str], bool]
) -> str:
    for _ in range(MAX_ATTEMPTS):
        candidate = format_student_id(prefix, next_number())
        if not exists(candidate):
            return candidate
    raise RuntimeError("Could not allocate a free student ID number.")
