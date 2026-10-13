"""
Campus2Career AI - Student Portal Module
Member 4 & 5: Student Portal & Integration
Provides the authenticated student with a secure, read-only institutional profile view, explainable analytics, and interactive company invitation responses.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_db, log_audit
from modules.insights import generate_student_insights

student_bp = Blueprint("student", __name__, url_prefix="/student")


def check_student_auth():
    """Verify session is an authenticated student."""
    return session.get("role") == "student" and session.get("student_id")


@student_bp.route("/dashboard")
def dashboard():
    if not check_student_auth():
        flash("Please log in with your student credentials.", "error")
        return redirect(url_for("login"))

    student_id = session.get("student_id")
    conn = get_db()
    cursor = conn.cursor()

    # Fetch strictly this student's record
    cursor.execute("""
        SELECT s.*, c.name as college_name, c.code as college_code, c.location as college_location
        FROM students s
        JOIN colleges c ON s.college_id = c.id
        WHERE s.id = ?
    """, (student_id,))
    student_row = cursor.fetchone()

    if not student_row:
        conn.close()
        flash("Student profile record not found.", "error")
        return redirect(url_for("login"))

    student = dict(student_row)

    # Fetch all invitations received by this student
    cursor.execute("""
        SELECT inv.*, comp.name as company_name, comp.industry, comp.website, comp.description as company_desc
        FROM invitations inv
        JOIN companies comp ON inv.company_id = comp.id
        WHERE inv.student_id = ?
        ORDER BY inv.created_at DESC
    """, (student_id,))
    invitations = [dict(row) for row in cursor.fetchall()]

    # Fetch student interventions recorded by college mentors
    cursor.execute("""
        SELECT * FROM interventions
        WHERE student_id = ?
        ORDER BY created_at DESC
    """, (student_id,))
    interventions = [dict(row) for row in cursor.fetchall()]

    conn.close()

    # Generate Explainable AI Insights & Scores
    insights = generate_student_insights(student)

    # Count invitation statuses
    pending_count = sum(1 for inv in invitations if inv["status"] == "Pending")
    accepted_count = sum(1 for inv in invitations if inv["status"] == "Accepted")

    return render_template(
        "student_portal.html",
        student=student,
        score_data=insights["score_data"],
        segment=insights["segment"],
        risk_flags=insights["risk_flags"],
        strengths=insights["strengths"],
        growth_areas=insights["growth_areas"],
        career_pathways=insights["career_pathways"],
        action_items=insights["action_items"],
        invitations=invitations,
        interventions=interventions,
        pending_count=pending_count,
        accepted_count=accepted_count
    )


@student_bp.route("/invitation/<int:inv_id>/respond", methods=["POST"])
def respond_invitation(inv_id):
    if not check_student_auth():
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    student_id = session.get("student_id")
    decision = request.form.get("decision", "").strip().capitalize()

    if decision not in ["Accepted", "Declined"]:
        flash("Invalid response action.", "error")
        return redirect(url_for("student.dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    # Verify that the invitation belongs to this student and is in 'Pending' status
    cursor.execute("""
        SELECT inv.*, comp.name as company_name
        FROM invitations inv
        JOIN companies comp ON inv.company_id = comp.id
        WHERE inv.id = ? AND inv.student_id = ?
    """, (inv_id, student_id))
    invitation = cursor.fetchone()

    if not invitation:
        conn.close()
        flash("Invitation not found or unauthorized.", "error")
        return redirect(url_for("student.dashboard"))

    if invitation["status"] == "Withdrawn":
        conn.close()
        flash("This invitation was withdrawn by the employer.", "warning")
        return redirect(url_for("student.dashboard"))

    cursor.execute("""
        UPDATE invitations
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND student_id = ?
    """, (decision, inv_id, student_id))
    conn.commit()
    conn.close()

    log_audit(
        session.get("college_id"), "STUDENT_INVITATION_RESPONSE", "INVITATION", inv_id,
        session.get("email"), f"Student responded: {decision} to {invitation['company_name']} for {invitation['job_role']}"
    )

    if decision == "Accepted":
        flash(f"🎉 Congratulations! You accepted the recruitment invitation for {invitation['job_role']} from {invitation['company_name']}.", "success")
    else:
        flash(f"You declined the invitation for {invitation['job_role']} from {invitation['company_name']}.", "info")

    return redirect(url_for("student.dashboard"))
