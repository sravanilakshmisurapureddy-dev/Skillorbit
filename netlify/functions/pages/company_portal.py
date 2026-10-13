"""
Campus2Career AI - Company Portal & Talent Matching Module
Member 4: Recruitment Engineer
Provides partnered companies with scoped student discovery, opportunity creation, AI candidate matching, shortlisting, and invitation dispatch.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_db, log_audit
from modules.success_score import calculate_student_success_score
from modules.risk_flags import evaluate_student_risk_flags
from modules.segmentation import classify_student_segment
from modules.matching import compute_student_opportunity_match, rank_candidates_for_opportunity

company_bp = Blueprint("company", __name__, url_prefix="/company")


def check_company_auth():
    """Verify session is an authenticated corporate recruiter with an authorized college link."""
    return session.get("role") == "company" and session.get("college_id") and session.get("company_id")


@company_bp.route("/dashboard")
def dashboard():
    if not check_company_auth():
        flash("Company login and authorized college collaboration required.", "error")
        return redirect(url_for("login"))

    company_id = session.get("company_id")
    college_id = session.get("college_id")

    conn = get_db()
    cursor = conn.cursor()

    # Verify active collaboration
    cursor.execute("""
        SELECT * FROM college_collaborations 
        WHERE college_id = ? AND company_id = ? AND status = 'Active'
    """, (college_id, company_id))
    collab = cursor.fetchone()
    if not collab:
        conn.close()
        flash("Access denied: Company is not an active collaborator with this college.", "error")
        return redirect(url_for("login"))

    # Fetch company and college details
    cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
    company = dict(cursor.fetchone())

    cursor.execute("SELECT * FROM colleges WHERE id = ?", (college_id,))
    college = dict(cursor.fetchone())

    # Fetch company opportunities posted for this college
    cursor.execute("""
        SELECT * FROM opportunities 
        WHERE company_id = ? AND college_id = ?
        ORDER BY created_at DESC
    """, (company_id, college_id))
    opportunities = [dict(row) for row in cursor.fetchall()]

    # Fetch shortlists by this company
    cursor.execute("""
        SELECT student_id FROM shortlists 
        WHERE company_id = ? AND college_id = ?
    """, (company_id, college_id))
    shortlisted_ids = set(row[0] for row in cursor.fetchall())

    # Fetch invitations sent by this company to this college's students
    cursor.execute("""
        SELECT inv.*, s.full_name as student_name, s.roll_number, s.branch, s.email as student_email, s.phone as student_phone, s.cgpa
        FROM invitations inv
        JOIN students s ON inv.student_id = s.id
        WHERE inv.company_id = ? AND inv.college_id = ?
        ORDER BY inv.created_at DESC
    """, (company_id, college_id))
    sent_invitations = [dict(row) for row in cursor.fetchall()]

    # Fetch all students belonging to this collaborated college
    # Respect consent status & placement status (students can opt-out from recruiter discovery)
    cursor.execute("""
        SELECT * FROM students 
        WHERE college_id = ? AND consent_status = 1 AND placement_status != 'Opted Out'
        ORDER BY cgpa DESC
    """, (college_id,))
    students_raw = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Active opportunity for matching selection
    selected_opp_id = request.args.get("opportunity_id", "")
    active_opp = None
    if selected_opp_id:
        for opp in opportunities:
            if str(opp["id"]) == selected_opp_id:
                active_opp = opp
                break
    if not active_opp and len(opportunities) > 0:
        active_opp = opportunities[0]

    # Enrich students with scores, segments, match percentages, and shortlist flags
    enriched_students = []
    for s in students_raw:
        score_data = calculate_student_success_score(s)
        segment = classify_student_segment(s, score_data)
        
        # Match calculation against active opportunity
        if active_opp:
            match_data = compute_student_opportunity_match(s, active_opp)
        else:
            match_data = {"match_percentage": round(score_data["overall_score"], 1), "is_eligible": True, "explanation": "General Readiness"}

        is_shortlisted = s["id"] in shortlisted_ids
        
        # Check if already invited
        invited_inv = next((inv for inv in sent_invitations if inv["student_id"] == s["id"]), None)

        enriched_students.append({
            **s,
            "score_data": score_data,
            "overall_score": score_data["overall_score"],
            "segment": segment,
            "match_data": match_data,
            "match_pct": match_data["match_percentage"],
            "is_shortlisted": is_shortlisted,
            "invited_inv": invited_inv
        })

    # Filters
    q_search = request.args.get("search", "").strip().lower()
    q_branch = request.args.get("branch", "All")
    q_min_cgpa = request.args.get("min_cgpa", "")
    q_skill = request.args.get("skill", "").strip().lower()
    q_segment = request.args.get("segment", "All")
    q_shortlist_only = request.args.get("shortlisted", "0")

    filtered = list(enriched_students)

    if q_search:
        filtered = [
            s for s in filtered
            if q_search in s["full_name"].lower()
            or q_search in s["roll_number"].lower()
            or q_search in s["programming_languages"].lower()
            or q_search in s["technical_skills"].lower()
            or q_search in s["certifications"].lower()
        ]

    if q_branch and q_branch != "All":
        filtered = [s for s in filtered if s["branch"] == q_branch]

    if q_min_cgpa:
        try:
            val = float(q_min_cgpa)
            filtered = [s for s in filtered if float(s["cgpa"]) >= val]
        except ValueError:
            pass

    if q_skill:
        filtered = [
            s for s in filtered
            if q_skill in s["programming_languages"].lower()
            or q_skill in s["technical_skills"].lower()
            or q_skill in s["certifications"].lower()
        ]

    if q_segment and q_segment != "All":
        filtered = [s for s in filtered if s["segment"]["key"] == q_segment]

    if q_shortlist_only == "1":
        filtered = [s for s in filtered if s["is_shortlisted"]]

    # Sort primarily by match % descending
    filtered.sort(key=lambda x: (x["match_pct"], x["overall_score"]), reverse=True)

    # Distinct branches for dropdown
    distinct_branches = sorted(list(set(s["branch"] for s in students_raw)))

    return render_template(
        "company_portal.html",
        company=company,
        college=college,
        opportunities=opportunities,
        active_opportunity=active_opp,
        students=filtered,
        total_college_candidates=len(students_raw),
        distinct_branches=distinct_branches,
        shortlisted_count=len(shortlisted_ids),
        sent_invitations=sent_invitations,
        active_filters={
            "search": request.args.get("search", ""),
            "branch": q_branch,
            "min_cgpa": q_min_cgpa,
            "skill": request.args.get("skill", ""),
            "segment": q_segment,
            "shortlisted": q_shortlist_only,
            "opportunity_id": selected_opp_id
        }
    )


@company_bp.route("/opportunity/create", methods=["POST"])
def create_opportunity():
    if not check_company_auth():
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    company_id = session.get("company_id")
    college_id = session.get("college_id")

    title = request.form.get("title", "").strip()
    role_type = request.form.get("role_type", "Full-time")
    job_desc = request.form.get("job_description", "").strip()
    req_skills = request.form.get("required_skills", "").strip()
    min_cgpa = float(request.form.get("min_cgpa", 6.5) or 6.5)
    eligible_branches = request.form.get("eligible_branches", "All").strip()
    salary = request.form.get("salary_or_stipend", "").strip()

    if not title or not req_skills:
        flash("Job Title and Required Skills are mandatory.", "error")
        return redirect(url_for("company.dashboard"))

    conn = get_db()
    conn.execute("""
        INSERT INTO opportunities (
            company_id, college_id, title, role_type, job_description,
            required_skills, min_cgpa, eligible_branches, salary_or_stipend
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (company_id, college_id, title, role_type, job_desc, req_skills, min_cgpa, eligible_branches, salary))
    conn.commit()
    conn.close()

    log_audit(college_id, "CREATE_OPPORTUNITY", "OPPORTUNITY", title,
              session.get("email"), f"Created recruitment opportunity '{title}' [{role_type}]")

    flash(f"Recruitment opportunity '{title}' created successfully!", "success")
    return redirect(url_for("company.dashboard"))


@company_bp.route("/shortlist/toggle", methods=["POST"])
def toggle_shortlist():
    if not check_company_auth():
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    company_id = session.get("company_id")
    college_id = session.get("college_id")
    student_id = request.form.get("student_id")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM shortlists 
        WHERE company_id = ? AND student_id = ?
    """, (company_id, student_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM shortlists WHERE id = ?", (existing["id"],))
        is_shortlisted = False
        action = "REMOVED_SHORTLIST"
    else:
        cursor.execute("""
            INSERT INTO shortlists (company_id, student_id, college_id)
            VALUES (?, ?, ?)
        """, (company_id, student_id, college_id))
        is_shortlisted = True
        action = "ADDED_SHORTLIST"

    conn.commit()
    conn.close()

    log_audit(college_id, action, "STUDENT", student_id, session.get("email"), "Shortlist status toggled.")
    return jsonify({"success": True, "is_shortlisted": is_shortlisted})


@company_bp.route("/invite", methods=["POST"])
def send_invitation():
    if not check_company_auth():
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    company_id = session.get("company_id")
    college_id = session.get("college_id")

    student_id = request.form.get("student_id")
    opp_id = request.form.get("opportunity_id") or None
    job_role = request.form.get("job_role", "").strip()
    job_desc = request.form.get("job_description", "").strip()
    req_skills = request.form.get("required_skills", "").strip()
    eligibility = request.form.get("eligibility_criteria", "").strip()
    message = request.form.get("message", "").strip()

    if not student_id or not job_role:
        flash("Student ID and Job Role are required to dispatch an invitation.", "error")
        return redirect(url_for("company.dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    # Check for existing pending invitation for same student and company
    cursor.execute("""
        SELECT id, status FROM invitations 
        WHERE company_id = ? AND student_id = ? AND job_role = ?
    """, (company_id, student_id, job_role))
    existing = cursor.fetchone()

    if existing and existing["status"] in ["Pending", "Accepted"]:
        conn.close()
        flash(f"An active invitation for '{job_role}' already exists for this candidate.", "error")
        return redirect(url_for("company.dashboard"))

    cursor.execute("""
        INSERT INTO invitations (
            company_id, college_id, student_id, opportunity_id,
            job_role, job_description, required_skills, eligibility_criteria,
            message, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
    """, (company_id, college_id, student_id, opp_id, job_role, job_desc, req_skills, eligibility, message))
    new_inv_id = cursor.lastrowid
    conn.commit()
    conn.close()

    log_audit(college_id, "SEND_INVITATION", "INVITATION", new_inv_id,
              session.get("email"), f"Sent interview invitation to student ID {student_id} for '{job_role}'")

    flash(f"Recruitment invitation dispatched to candidate successfully!", "success")
    return redirect(url_for("company.dashboard"))


@company_bp.route("/invitation/<int:inv_id>/withdraw", methods=["POST"])
def withdraw_invitation(inv_id):
    if not check_company_auth():
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    company_id = session.get("company_id")
    college_id = session.get("college_id")

    conn = get_db()
    conn.execute("""
        UPDATE invitations 
        SET status = 'Withdrawn', updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND company_id = ?
    """, (inv_id, company_id))
    conn.commit()
    conn.close()

    log_audit(college_id, "WITHDRAW_INVITATION", "INVITATION", inv_id,
              session.get("email"), "Company withdrew recruitment invitation.")

    flash("Invitation withdrawn.", "info")
    return redirect(url_for("company.dashboard"))
