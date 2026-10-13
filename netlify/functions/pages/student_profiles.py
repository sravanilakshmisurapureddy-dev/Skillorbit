"""
Campus2Career AI - Student Profiles Module
Member 3: Frontend Developer & College Dashboard Lead
Manages detailed individual student profile pages, performance breakdowns, edits, removals, and credential resets.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_db, update_student_record, delete_student_record, reset_student_password, log_audit
from modules.success_score import calculate_student_success_score
from modules.risk_flags import evaluate_student_risk_flags
from modules.segmentation import classify_student_segment
from modules.insights import generate_student_insights

profiles_bp = Blueprint("profiles", __name__, url_prefix="/college/student")


def check_college_admin_auth():
    return session.get("role") == "college_admin" and session.get("college_id")


@profiles_bp.route("/<int:student_id>")
def view_profile(student_id):
    if not check_college_admin_auth():
        flash("Unauthorized access. College administrator credentials required.", "error")
        return redirect(url_for("login"))

    college_id = session.get("college_id")
    conn = get_db()
    cursor = conn.cursor()

    # Fetch student
    cursor.execute("SELECT * FROM students WHERE id = ? AND college_id = ?", (student_id, college_id))
    student = cursor.fetchone()
    if not student:
        conn.close()
        flash("Student record not found or access denied.", "error")
        return redirect(url_for("college.dashboard"))

    student_dict = dict(student)

    # Fetch invitations received by this student
    cursor.execute("""
        SELECT inv.*, comp.name as company_name, comp.industry, comp.website
        FROM invitations inv
        JOIN companies comp ON inv.company_id = comp.id
        WHERE inv.student_id = ?
        ORDER BY inv.created_at DESC
    """, (student_id,))
    invitations = [dict(row) for row in cursor.fetchall()]

    # Fetch student interventions
    cursor.execute("""
        SELECT * FROM interventions
        WHERE student_id = ?
        ORDER BY created_at DESC
    """, (student_id,))
    interventions = [dict(row) for row in cursor.fetchall()]

    # Fetch audit logs for this student
    cursor.execute("""
        SELECT * FROM audit_logs
        WHERE (entity_type = 'STUDENT' AND (entity_id = ? OR entity_id = ?))
        ORDER BY timestamp DESC LIMIT 6
    """, (str(student_id), student["roll_number"]))
    audit_logs = [dict(row) for row in cursor.fetchall()]

    conn.close()

    # Generate Explainable Insights
    insights = generate_student_insights(student_dict)

    return render_template(
        "student_detail.html",
        student=student_dict,
        score_data=insights["score_data"],
        segment=insights["segment"],
        risk_flags=insights["risk_flags"],
        strengths=insights["strengths"],
        growth_areas=insights["growth_areas"],
        career_pathways=insights["career_pathways"],
        action_items=insights["action_items"],
        invitations=invitations,
        interventions=interventions,
        audit_logs=audit_logs
    )


@profiles_bp.route("/<int:student_id>/edit", methods=["POST"])
def edit_profile(student_id):
    if not check_college_admin_auth():
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    college_id = session.get("college_id")
    form_data = request.form.to_dict()

    success, msg = update_student_record(student_id, college_id, form_data)
    if success:
        flash("Student profile successfully updated.", "success")
    else:
        flash(f"Failed to update profile: {msg}", "error")

    return redirect(url_for("profiles.view_profile", student_id=student_id))


@profiles_bp.route("/<int:student_id>/delete", methods=["POST"])
def delete_profile(student_id):
    if not check_college_admin_auth():
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    college_id = session.get("college_id")
    success, msg = delete_student_record(student_id, college_id)
    if success:
        flash("Student profile and associated credentials successfully removed.", "success")
    else:
        flash(f"Error removing student: {msg}", "error")

    return redirect(url_for("college.dashboard"))


@profiles_bp.route("/<int:student_id>/reset-password", methods=["POST"])
def reset_password(student_id):
    if not check_college_admin_auth():
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    new_pw = request.form.get("new_password", "student123").strip() or "student123"
    success, msg = reset_student_password(student_id, new_pw)
    if success:
        flash(f"Student password reset successfully to: {new_pw}", "success")
    else:
        flash(f"Password reset failed: {msg}", "error")

    return redirect(url_for("profiles.view_profile", student_id=student_id))
