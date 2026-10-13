"""
Campus2Career AI - College Dashboard Module
Member 3: Frontend Developer & College Dashboard Lead
Manages institutional analytics, student directory, filters, top-N selection, and intervention tracking.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, Response
from database import get_db, add_student_record, log_audit
from modules.success_score import calculate_student_success_score
from modules.risk_flags import evaluate_student_risk_flags
from modules.segmentation import classify_student_segment, compute_cohort_segmentation
from modules.trends import calculate_cohort_trends, get_top_n_students
from modules.data_integration import process_csv_upload, export_college_students_csv

college_bp = Blueprint("college", __name__, url_prefix="/college")


def check_college_admin_auth():
    """Verify session is an authenticated college administrator."""
    if session.get("role") != "college_admin" or not session.get("college_id"):
        return False
    return True


@college_bp.route("/dashboard")
def dashboard():
    if not check_college_admin_auth():
        flash("Please log in as a College Administrator.", "error")
        return redirect(url_for("login"))

    college_id = session.get("college_id")
    conn = get_db()
    cursor = conn.cursor()

    # Get College Details
    cursor.execute("SELECT * FROM colleges WHERE id = ?", (college_id,))
    college = cursor.fetchone()

    # Get All Students of this college
    cursor.execute("SELECT * FROM students WHERE college_id = ? ORDER BY id DESC", (college_id,))
    students_raw = [dict(row) for row in cursor.fetchall()]

    # Get Collaborated Companies
    cursor.execute("""
        SELECT c.*, cc.status as collab_status, cc.collaborated_since
        FROM companies c
        JOIN college_collaborations cc ON c.id = cc.company_id
        WHERE cc.college_id = ?
    """, (college_id,))
    collaborated_companies = [dict(row) for row in cursor.fetchall()]

    # Get Invitations & Recruitment activity
    cursor.execute("""
        SELECT inv.*, s.full_name as student_name, s.roll_number, s.branch, comp.name as company_name
        FROM invitations inv
        JOIN students s ON inv.student_id = s.id
        JOIN companies comp ON inv.company_id = comp.id
        WHERE inv.college_id = ?
        ORDER BY inv.created_at DESC
    """, (college_id,))
    invitations = [dict(row) for row in cursor.fetchall()]

    # Get Interventions
    cursor.execute("""
        SELECT i.*, s.full_name as student_name, s.roll_number
        FROM interventions i
        JOIN students s ON i.student_id = s.id
        WHERE i.college_id = ?
        ORDER BY i.created_at DESC
    """, (college_id,))
    interventions = [dict(row) for row in cursor.fetchall()]

    # Get Recent Audit Logs
    cursor.execute("""
        SELECT * FROM audit_logs
        WHERE college_id = ?
        ORDER BY timestamp DESC LIMIT 8
    """, (college_id,))
    audit_logs = [dict(row) for row in cursor.fetchall()]

    conn.close()

    # Calculate Rich Analytics for each student
    enriched_students = []
    for s in students_raw:
        score_data = calculate_student_success_score(s)
        risk_flags = evaluate_student_risk_flags(s, score_data)
        segment = classify_student_segment(s, score_data)
        enriched_students.append({
            **s,
            "score_data": score_data,
            "overall_score": score_data["overall_score"],
            "grade": score_data["grade"],
            "risk_flags": risk_flags,
            "risk_count": len(risk_flags),
            "has_critical_risk": any(f["severity"] == "critical" for f in risk_flags),
            "segment": segment
        })

    # Cohort-level Analytics
    trends = calculate_cohort_trends(students_raw)
    segmentation_data = compute_cohort_segmentation(students_raw)

    # Key KPI metrics
    total_students = len(enriched_students)
    distinct_branches = sorted(list(set(s["branch"] for s in enriched_students)))
    eligible_count = sum(1 for s in enriched_students if s.get("placement_status") == "Eligible" and s.get("consent_status") == 1)
    placed_count = sum(1 for s in enriched_students if s.get("placement_status") == "Placed")
    at_risk_count = sum(1 for s in enriched_students if s["has_critical_risk"])
    avg_score = trends["avg_score"]

    # Filter parameters from query string
    q_search = request.args.get("search", "").strip().lower()
    q_branch = request.args.get("branch", "All")
    q_year = request.args.get("year", "All")
    q_segment = request.args.get("segment", "All")
    q_risk = request.args.get("risk", "All")
    q_top_n = request.args.get("top_n", "")

    filtered_students = list(enriched_students)

    if q_search:
        filtered_students = [
            s for s in filtered_students
            if q_search in s["full_name"].lower()
            or q_search in s["roll_number"].lower()
            or q_search in s["email"].lower()
            or q_search in s["programming_languages"].lower()
            or q_search in s["technical_skills"].lower()
        ]

    if q_branch and q_branch != "All":
        filtered_students = [s for s in filtered_students if s["branch"] == q_branch]

    if q_year and q_year != "All":
        filtered_students = [s for s in filtered_students if s["academic_year"] == q_year]

    if q_segment and q_segment != "All":
        filtered_students = [s for s in filtered_students if s["segment"]["key"] == q_segment]

    if q_risk == "Critical":
        filtered_students = [s for s in filtered_students if s["has_critical_risk"]]
    elif q_risk == "Any":
        filtered_students = [s for s in filtered_students if s["risk_count"] > 0]

    # Top-N selection sorting
    if q_top_n:
        try:
            n_val = int(q_top_n)
            filtered_students.sort(key=lambda x: x["overall_score"], reverse=True)
            filtered_students = filtered_students[:n_val]
        except ValueError:
            pass

    return render_template(
        "college_dashboard.html",
        college=college,
        students=filtered_students,
        total_students=total_students,
        distinct_branches=distinct_branches,
        eligible_count=eligible_count,
        placed_count=placed_count,
        at_risk_count=at_risk_count,
        avg_score=avg_score,
        collaborated_companies=collaborated_companies,
        invitations=invitations,
        interventions=interventions,
        audit_logs=audit_logs,
        trends=trends,
        segmentation_data=segmentation_data,
        active_filters={
            "search": request.args.get("search", ""),
            "branch": q_branch,
            "year": q_year,
            "segment": q_segment,
            "risk": q_risk,
            "top_n": q_top_n
        }
    )


@college_bp.route("/student/add", methods=["POST"])
def add_student():
    if not check_college_admin_auth():
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    college_id = session.get("college_id")
    data = request.form.to_dict()

    # Default generated password if not provided
    generated_password = data.get("password", "student123").strip() or "student123"

    success, res = add_student_record(college_id, data, generated_password)
    if success:
        flash(f"Student profile created successfully! Login password: {generated_password}", "success")
    else:
        flash(f"Failed to add student: {res}", "error")

    return redirect(url_for("college.dashboard"))


@college_bp.route("/upload-csv", methods=["POST"])
def upload_csv():
    if not check_college_admin_auth():
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    college_id = session.get("college_id")
    if "csv_file" not in request.files:
        flash("No file was uploaded.", "error")
        return redirect(url_for("college.dashboard"))

    file = request.files["csv_file"]
    if file.filename == "":
        flash("Please select a valid CSV file.", "error")
        return redirect(url_for("college.dashboard"))

    try:
        content = file.read().decode("utf-8", errors="replace")
        report = process_csv_upload(content, college_id)
        if report.get("success"):
            flash(
                f"CSV Import Complete: {report['imported_count']} records imported. "
                f"({report['skipped_count']} skipped/duplicates).",
                "success"
            )
        else:
            flash(f"CSV Import Failed: {report.get('message', 'Unknown error')}", "error")
    except Exception as e:
        flash(f"Error processing CSV: {str(e)}", "error")

    return redirect(url_for("college.dashboard"))


@college_bp.route("/export-csv")
def export_csv():
    if not check_college_admin_auth():
        return redirect(url_for("login"))

    college_id = session.get("college_id")
    csv_str = export_college_students_csv(college_id)
    return Response(
        csv_str,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=campus2career_students.csv"}
    )


@college_bp.route("/intervention/add", methods=["POST"])
def add_intervention():
    if not check_college_admin_auth():
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    college_id = session.get("college_id")
    student_id = request.form.get("student_id")
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "Skill Gap Training")
    notes = request.form.get("notes", "").strip()
    assigned_to = request.form.get("assigned_to", "Placement Cell")

    if not student_id or not title:
        flash("Student and title are required for an intervention.", "error")
        return redirect(url_for("college.dashboard"))

    conn = get_db()
    conn.execute("""
        INSERT INTO interventions (student_id, college_id, title, category, notes, status, assigned_to)
        VALUES (?, ?, ?, ?, ?, 'Planned', ?)
    """, (student_id, college_id, title, category, notes, assigned_to))
    conn.commit()
    conn.close()

    log_audit(college_id, "ADD_INTERVENTION", "STUDENT", student_id,
              "College Staff", f"Assigned intervention '{title}' [{category}]")

    flash("Targeted intervention assigned successfully.", "success")
    return redirect(url_for("college.dashboard"))


@college_bp.route("/intervention/<int:interv_id>/update-status", methods=["POST"])
def update_intervention_status(interv_id):
    if not check_college_admin_auth():
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    college_id = session.get("college_id")
    new_status = request.form.get("status", "Completed")

    conn = get_db()
    conn.execute("""
        UPDATE interventions SET status = ? WHERE id = ? AND college_id = ?
    """, (new_status, interv_id, college_id))
    conn.commit()
    conn.close()

    flash(f"Intervention status updated to {new_status}.", "success")
    return redirect(url_for("college.dashboard"))
