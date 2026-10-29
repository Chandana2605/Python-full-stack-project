import csv
from io import BytesIO, StringIO

from openpyxl import Workbook


def candidates_to_csv(candidates: list[dict]) -> str:
    output = StringIO()
    fields = [
        "id",
        "email",
        "eligible_phase",
        "intake_year",
        "name",
        "college",
        "graduation_year",
        "tech_stack",
        "percentage",
        "batch_id",
        "uid",
        "employee_email",
        "offer_accepted",
        "source",
        "status",
        "pre_onboarding_score",
        "post_onboarding_score",
        "knowledge_check_python_score",
        "knowledge_check_java_score",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(candidates)
    return output.getvalue()


def workbook_bytes(headers: list[str], sample_rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in sample_rows:
        worksheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream.read()


def master_database_template_bytes() -> bytes:
    return workbook_bytes(["name", "college", "email", "percentage"], [["Candidate Name", "College Name", "candidate@company.com", 78]])


def baseline_template_bytes() -> bytes:
    return workbook_bytes(["candidate_email", "attended", "score", "max_score", "pass_percentage"], [["candidate@company.com", "yes", 72, 100, 60], ["absent@company.com", "no", 0, 100, 60]])


def knowledge_check_template_bytes() -> bytes:
    return workbook_bytes(["name", "college", "candidate_email", "percentage", "coding_name", "score", "max_score", "pass_percentage", "attempt"], [["Candidate Name", "College Name", "candidate@company.com", 82, "Python Challenge", 81, 100, 60, 1]])
