"""
Campus2Career AI - Data Integration Engine
Member 1: Data Integration & Database Lead
Handles CSV parsing, schema validation, duplicate detection, cleaning, and merging into SQLite.
"""

import io
import csv
import pandas as pd
from database import get_db, add_student_record, log_audit

REQUIRED_COLUMNS = [
    "roll_number", "full_name", "branch", "email", "cgpa"
]

OPTIONAL_COLUMNS = [
    "academic_year", "phone", "percentage", "certifications",
    "programming_languages", "technical_skills", "internship_details",
    "linkedin_url", "github_url", "soft_skills", "placement_status", "consent_status"
]

DATA_DICTIONARY = {
    "roll_number": {"type": "String", "required": True, "description": "Unique institutional student identifier (e.g. 2025CS101)"},
    "full_name": {"type": "String", "required": True, "description": "Official full name of student"},
    "branch": {"type": "String", "required": True, "description": "Academic department / engineering branch"},
    "academic_year": {"type": "String", "required": False, "description": "Current graduation year cohort"},
    "email": {"type": "Email", "required": True, "description": "Unique institutional or personal email address"},
    "phone": {"type": "Phone", "required": False, "description": "Contact telephone number"},
    "cgpa": {"type": "Float [0.0 - 10.0]", "required": True, "description": "Cumulative Grade Point Average"},
    "percentage": {"type": "Float [0.0 - 100.0]", "required": False, "description": "Equivalent percentage marks"},
    "certifications": {"type": "Comma-separated String", "required": False, "description": "Professional certifications acquired"},
    "programming_languages": {"type": "Comma-separated String", "required": False, "description": "Coding languages known"},
    "technical_skills": {"type": "Comma-separated String", "required": False, "description": "Frameworks, databases, and dev tools"},
    "internship_details": {"type": "Text", "required": False, "description": "Practical industry training or internship summary"},
    "linkedin_url": {"type": "URL", "required": False, "description": "Verified LinkedIn public profile URL"},
    "github_url": {"type": "URL", "required": False, "description": "Public GitHub or portfolio project link"},
    "soft_skills": {"type": "Comma-separated String", "required": False, "description": "Interpersonal, leadership, or communication attributes"},
    "placement_status": {"type": "Enum [Eligible, Placed, Opted Out]", "required": False, "description": "Recruitment drive eligibility status"},
    "consent_status": {"type": "Integer (1 or 0)", "required": False, "description": "Student consent for recruiter profile visibility"}
}


def get_data_dictionary():
    """Returns the official common schema data dictionary."""
    return DATA_DICTIONARY


def validate_and_clean_record(raw_row):
    """
    Validates a single record dictionary.
    Returns (is_valid, cleaned_data, list_of_errors, list_of_warnings)
    """
    errors = []
    warnings = []
    cleaned = {}

    # 1. Roll Number
    roll = str(raw_row.get("roll_number", "")).strip()
    if not roll:
        errors.append("Roll number is missing.")
    else:
        cleaned["roll_number"] = roll

    # 2. Full Name
    name = str(raw_row.get("full_name", "")).strip()
    if not name:
        errors.append("Full name is missing.")
    else:
        cleaned["full_name"] = name

    # 3. Email
    email = str(raw_row.get("email", "")).strip().lower()
    if not email or "@" not in email:
        errors.append(f"Invalid email address: '{email}'")
    else:
        cleaned["email"] = email

    # 4. Branch
    branch = str(raw_row.get("branch", "")).strip()
    if not branch:
        errors.append("Branch/Department is required.")
    else:
        cleaned["branch"] = branch

    # 5. CGPA
    cgpa_raw = raw_row.get("cgpa", "")
    try:
        cgpa_val = float(cgpa_raw)
        if cgpa_val < 0 or cgpa_val > 10.0:
            errors.append(f"CGPA must be between 0.0 and 10.0, got: {cgpa_val}")
        else:
            cleaned["cgpa"] = round(cgpa_val, 2)
    except (ValueError, TypeError):
        errors.append(f"Invalid CGPA value: '{cgpa_raw}'")

    # Percentage
    percentage_raw = raw_row.get("percentage", "")
    if percentage_raw and str(percentage_raw).strip() != "":
        try:
            pct = float(percentage_raw)
            cleaned["percentage"] = round(pct, 2)
        except (ValueError, TypeError):
            if "cgpa" in cleaned:
                cleaned["percentage"] = round(cleaned["cgpa"] * 9.5, 2)
                warnings.append("Invalid percentage; auto-calculated from CGPA * 9.5.")
    else:
        if "cgpa" in cleaned:
            cleaned["percentage"] = round(cleaned["cgpa"] * 9.5, 2)

    # Optional fields
    cleaned["academic_year"] = str(raw_row.get("academic_year", "Final Year (2025)")).strip()
    cleaned["phone"] = str(raw_row.get("phone", "")).strip()
    cleaned["certifications"] = str(raw_row.get("certifications", "")).strip()
    cleaned["programming_languages"] = str(raw_row.get("programming_languages", "")).strip()
    cleaned["technical_skills"] = str(raw_row.get("technical_skills", "")).strip()
    cleaned["internship_details"] = str(raw_row.get("internship_details", "")).strip()
    cleaned["linkedin_url"] = str(raw_row.get("linkedin_url", "")).strip()
    cleaned["github_url"] = str(raw_row.get("github_url", "")).strip()
    cleaned["soft_skills"] = str(raw_row.get("soft_skills", "")).strip()
    
    status = str(raw_row.get("placement_status", "Eligible")).strip()
    if status not in ["Eligible", "Placed", "Opted Out"]:
        status = "Eligible"
    cleaned["placement_status"] = status

    consent = raw_row.get("consent_status", 1)
    try:
        cleaned["consent_status"] = 1 if int(consent) == 1 else 0
    except (ValueError, TypeError):
        cleaned["consent_status"] = 1

    # Check for empty important technical fields
    if not cleaned["programming_languages"] and not cleaned["technical_skills"]:
        warnings.append("No programming languages or technical skills specified.")
    if not cleaned["internship_details"] or cleaned["internship_details"].lower() in ["none", "none recorded", ""]:
        warnings.append("No practical internship recorded.")

    is_valid = len(errors) == 0
    return is_valid, cleaned, errors, warnings


def process_csv_upload(csv_content_or_stream, college_id, default_password="student123"):
    """
    Parses, validates, detects duplicates, and imports student records.
    Returns comprehensive batch report:
    {
        'total_rows': N,
        'imported_count': N,
        'skipped_count': N,
        'errors': [{'row': i, 'errors': [...]}, ...],
        'warnings': [{'row': i, 'warnings': [...]}, ...],
        'duplicate_ids': [...],
        'success': True/False
    }
    """
    if isinstance(csv_content_or_stream, str):
        stream = io.StringIO(csv_content_or_stream)
    elif isinstance(csv_content_or_stream, bytes):
        stream = io.StringIO(csv_content_or_stream.decode('utf-8', errors='replace'))
    else:
        stream = csv_content_or_stream

    reader = csv.DictReader(stream)
    
    # Check headers
    if not reader.fieldnames:
        return {
            "success": False,
            "message": "Uploaded CSV appears to be empty or has no header row."
        }

    # Normalize header names (lowercase, strip whitespace)
    normalized_fieldnames = {col.strip().lower(): col for col in reader.fieldnames}
    
    missing_required_headers = [
        col for col in REQUIRED_COLUMNS if col not in normalized_fieldnames
    ]
    if missing_required_headers:
        return {
            "success": False,
            "message": f"CSV missing mandatory columns: {', '.join(missing_required_headers)}"
        }

    # Fetch existing roll numbers & emails for college to prevent duplicates
    conn = get_db()
    existing_rolls = set(row[0] for row in conn.execute("SELECT roll_number FROM students WHERE college_id = ?", (college_id,)).fetchall())
    existing_emails = set(row[0] for row in conn.execute("SELECT email FROM students WHERE college_id = ?", (college_id,)).fetchall())
    conn.close()

    total_rows = 0
    imported_count = 0
    skipped_count = 0
    error_list = []
    warning_list = []
    duplicates = []

    seen_batch_rolls = set()
    seen_batch_emails = set()

    rows_to_insert = []

    for idx, raw_row in enumerate(reader, start=1):
        total_rows += 1
        # Normalize keys in raw_row
        row = {k.strip().lower(): v for k, v in raw_row.items() if k}

        is_valid, cleaned, errs, warns = validate_and_clean_record(row)
        
        if not is_valid:
            error_list.append({"row": idx, "roll": row.get("roll_number", "N/A"), "errors": errs})
            skipped_count += 1
            continue

        roll = cleaned["roll_number"]
        email = cleaned["email"]

        # Duplicate check against database
        if roll in existing_rolls or email in existing_emails:
            duplicates.append(f"Row {idx}: Student ID '{roll}' or email '{email}' already exists in database.")
            skipped_count += 1
            continue

        # Duplicate check within current CSV file
        if roll in seen_batch_rolls or email in seen_batch_emails:
            duplicates.append(f"Row {idx}: Duplicate record within file for '{roll}' or '{email}'.")
            skipped_count += 1
            continue

        seen_batch_rolls.add(roll)
        seen_batch_emails.add(email)

        if warns:
            warning_list.append({"row": idx, "roll": roll, "warnings": warns})

        rows_to_insert.append(cleaned)

    # Insert valid records
    for record in rows_to_insert:
        success, res = add_student_record(college_id, record, default_password)
        if success:
            imported_count += 1
            existing_rolls.add(record["roll_number"])
            existing_emails.add(record["email"])
        else:
            error_list.append({"row": "DB", "roll": record["roll_number"], "errors": [res]})
            skipped_count += 1

    log_audit(
        college_id, "CSV_IMPORT", "STUDENTS", f"{imported_count} imported",
        "College Staff", f"Processed {total_rows} rows. Imported {imported_count}, skipped {skipped_count}."
    )

    return {
        "success": True,
        "total_rows": total_rows,
        "imported_count": imported_count,
        "skipped_count": skipped_count,
        "errors": error_list,
        "warnings": warning_list,
        "duplicate_ids": duplicates
    }


def export_college_students_csv(college_id):
    """Exports all students of a college to CSV formatted string."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT roll_number, full_name, branch, academic_year, email, phone,
               cgpa, percentage, certifications, programming_languages,
               technical_skills, internship_details, linkedin_url, github_url,
               soft_skills, placement_status, consent_status
        FROM students
        WHERE college_id = ?
        ORDER BY roll_number ASC
    """, (college_id,))
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "roll_number", "full_name", "branch", "academic_year", "email", "phone",
        "cgpa", "percentage", "certifications", "programming_languages",
        "technical_skills", "internship_details", "linkedin_url", "github_url",
        "soft_skills", "placement_status", "consent_status"
    ])
    for r in rows:
        writer.writerow(list(r))
    return output.getvalue()
