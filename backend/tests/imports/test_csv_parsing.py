from uuid import uuid4

import pytest

from app.exceptions import InvalidCSVError
from app.models.import_job import ImportRowStatus as S
from app.services.csv_import_service import (
    assess_rows,
    build_course_lookup,
    decode_csv,
    derive_course_code,
    parse_csv,
)

HEADER = "ID No.,Name,Guardian's Name,Address,Contact No.,Course\n"
DCA_ID = uuid4()
LOOKUP = build_course_lookup(
    [{"id": DCA_ID, "code": "DCA", "name": "Diploma in Computer Applications"}]
)


def assess(text: str, existing: set[str] | None = None):
    parsed = parse_csv(text, max_rows=1000)
    return assess_rows(parsed.rows, existing_keys=existing or set(), course_lookup=LOOKUP)


def test_header_variants_are_recognised():
    # BOM, odd spacing/case and a typographic apostrophe in "Guardian's Name".
    text = (
        "\ufeffid no , NAME,Guardian\u2019s Name,address,Contact No,COURSE,Remarks\n"
        "B1,Asha,G,A,9876543210,DCA,x\n"
    )
    parsed = parse_csv(text, max_rows=10)
    assert parsed.extra_columns == ["Remarks"]
    assert parsed.rows[0].values["id_no"] == "B1"
    assert parsed.rows[0].raw["Remarks"] == "x"  # extra columns are preserved in the raw record


def test_missing_columns_are_reported():
    with pytest.raises(InvalidCSVError) as info:
        parse_csv("ID No.,Name\nB1,Asha\n", max_rows=10)
    assert info.value.code == "MISSING_COLUMNS"
    assert "Guardian's Name" in info.value.details["missing"]


def test_duplicate_columns_are_rejected():
    with pytest.raises(InvalidCSVError, match="Duplicate columns"):
        parse_csv(HEADER.strip() + ",Name\n", max_rows=10)


def test_empty_file_and_row_limit():
    with pytest.raises(InvalidCSVError, match="empty"):
        parse_csv("", max_rows=10)
    rows = "".join(f"B{i},N,G,A,9876543210,DCA\n" for i in range(3))
    with pytest.raises(InvalidCSVError, match="more than 2 rows"):
        parse_csv(HEADER + rows, max_rows=2)


def test_blank_rows_are_counted_not_imported():
    parsed = parse_csv(HEADER + "B1,Asha,G,A,9876543210,DCA\n,,,,,\n\n", max_rows=10)
    assert len(parsed.rows) == 1 and parsed.blank_rows == 2


def test_decode_falls_back_to_windows_1252():
    assert decode_csv("Café".encode("cp1252")) == "Café"
    assert decode_csv("﻿Café".encode()) == "Café"


def test_quoted_fields_with_commas_and_newlines():
    parsed = parse_csv(HEADER + 'B1,Asha,G,"12, Main Rd\nKolkata",9876543210,DCA\n', max_rows=10)
    assert parsed.rows[0].values["address"] == "12, Main Rd Kolkata"


def test_row_statuses():
    rows = assess(
        HEADER
        + "B1,Asha Roy,Mr Roy,Kolkata,9876543210,DCA\n"  # valid
        + "B2,Binod,,Howrah,033 2456 7890,D.C.A.\n"  # warnings: no guardian, landline
        + ",No Id,G,A,9876543210,DCA\n"  # error: missing ID
        + "B4,,G,A,9876543210,DCA\n"  # error: missing name
        + "B5,Old,G,A,9876543210,DCA\n"  # exists in DB
        + "B6,Unknown Course,G,A,9876543210,Tally Prime\n",  # warning: unmapped course
        existing={"b5"},
    )
    assert [r.status for r in rows] == [S.VALID, S.WARNING, S.ERROR, S.ERROR, S.EXISTS, S.WARNING]
    codes = {m["code"] for m in rows[1].messages}
    assert {"MISSING_GUARDIAN", "INVALID_PHONE"} <= codes
    assert rows[1].normalized["course_id"] == str(DCA_ID)  # "D.C.A." matched the DCA code
    assert rows[1].normalized["contact"] == "033 2456 7890"  # raw contact preserved
    assert rows[5].normalized["course_id"] is None
    assert any(m["code"] == "UNMAPPED_COURSE" for m in rows[5].messages)


def test_identical_duplicates_keep_the_first_row():
    rows = assess(HEADER + "B1,Asha,G,A,9876543210,DCA\n" + "b1,Asha,G,A,9876543210,DCA\n")
    # Case differs in the ID, so the data differs: both rows are errors.
    assert [r.status for r in rows] == [S.ERROR, S.ERROR]
    rows = assess(HEADER + "B1,Asha,G,A,9876543210,DCA\n" * 2)
    assert [r.status for r in rows] == [S.VALID, S.DUPLICATE]


def test_conflicting_duplicates_are_errors():
    rows = assess(HEADER + "B1,Asha,G,A,9876543210,DCA\nB1,Binod,G,A,9876543210,DCA\n")
    assert [r.status for r in rows] == [S.ERROR, S.ERROR]
    assert (
        "rows 2, 3"
        in next(m for m in rows[0].messages if m["code"] == "DUPLICATE_ID_NO")["message"]
    )


def test_overlong_values_are_errors():
    rows = assess(HEADER + f"B1,{'x' * 201},G,A,9876543210,DCA\n")
    assert rows[0].status == S.ERROR


def test_derive_course_code():
    taken = {"TALLY-PRIME"}
    assert derive_course_code("Tally Prime", taken.__contains__) == "TALLY-PRIME-2"
    assert derive_course_code("!!!", set().__contains__) == "COURSE"
