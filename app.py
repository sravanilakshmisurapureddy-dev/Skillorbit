"""
Campus2Career AI - Main Application & Integration Engine
Member 5: Integration, Testing & Demo Lead
Assembles data, analytics, dashboards, and role-based workflows into a unified platform.
"""

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
from database import init_db, seed_demo_data, get_db, log_audit

# Import Page Blueprints
from pages.college_dashboard import college_bp
from pages.student_profiles import profiles_bp
from pages.company_portal import company_bp
from pages.student_portal import student_bp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "campus2career_super_secret_hackathon_key_2025")

# Register All Module Blueprints
app.register_blueprint(college_bp)
app.register_blueprint(profiles_bp)
app.register_blueprint(company_bp)
app.register_blueprint(student_bp)

# Auto-initialize DB on startup (works with gunicorn on Render)
with app.app_context():
    init_db()
    seed_demo_data()



@app.context_processor
def inject_global_context():
    """Injects current session details and institutional metadata to all templates."""
    user = None
    if "user_id" in session:
        user = {
            "id": session.get("user_id"),
            "email": session.get("email"),
            "role": session.get("role"),
            "name": session.get("name"),
            "college_name": session.get("college_name"),
            "college_code": session.get("college_code")
        }
    return dict(current_user=user)


@app.route("/")
def index():
    """Landing Page showcasing the platform, architecture, and portal gateways."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM students")
    total_students = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM companies")
    total_companies = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM invitations")
    total_invitations = cursor.fetchone()["cnt"]

    cursor.execute("SELECT * FROM colleges")
    colleges = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return render_template(
        "index.html",
        total_students=total_students,
        total_companies=total_companies,
        total_invitations=total_invitations,
        colleges=colleges
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    """Unified Secure Authentication Portal supporting College Admins, Students, and Companies."""
    if request.method == "POST":
        role = request.form.get("role")
        identifier = request.form.get("identifier", "").strip()  # email / roll / phone
        password = request.form.get("password", "")
        college_code = request.form.get("college_code", "").strip().upper()

        if not identifier or not password:
            flash("Please provide all required login credentials.", "error")
            return render_template("login.html")

        conn = get_db()
        cursor = conn.cursor()

        if role == "college_admin":
            cursor.execute("""
                SELECT u.*, c.name as college_name, c.code as college_code
                FROM users u
                JOIN colleges c ON u.college_id = c.id
                WHERE (u.email = ? OR u.username = ?) AND u.role = 'college_admin'
            """, (identifier.lower(), identifier))
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["email"] = user["email"]
                session["role"] = "college_admin"
                session["college_id"] = user["college_id"]
                session["college_name"] = user["college_name"]
                session["college_code"] = user["college_code"]
                session["name"] = "College Administrator"
                conn.close()
                flash(f"Welcome back, Administrator of {user['college_name']}!", "success")
                return redirect(url_for("college.dashboard"))
            else:
                conn.close()
                flash("Invalid administrator email or password.", "error")
                return render_template("login.html")

        elif role == "student":
            # Can login via registered email OR phone number OR roll number
            cursor.execute("""
                SELECT u.*, s.id as student_id, s.full_name, s.roll_number, c.name as college_name, c.code as college_code
                FROM users u
                JOIN students s ON (u.email = s.email OR u.username = s.roll_number)
                JOIN colleges c ON s.college_id = c.id
                WHERE (u.email = ? OR u.phone = ? OR u.username = ?) AND u.role = 'student'
            """, (identifier.lower(), identifier, identifier))
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["email"] = user["email"]
                session["role"] = "student"
                session["student_id"] = user["student_id"]
                session["college_id"] = user["college_id"]
                session["college_name"] = user["college_name"]
                session["college_code"] = user["college_code"]
                session["name"] = user["full_name"]
                session["roll_number"] = user["roll_number"]
                conn.close()
                flash(f"Welcome back, {user['full_name']}!", "success")
                return redirect(url_for("student.dashboard"))
            else:
                conn.close()
                flash("Invalid student email, phone, or password.", "error")
                return render_template("login.html")

        elif role == "company":
            # Requires College Code + Company Credentials
            if not college_code:
                conn.close()
                flash("College code is mandatory for partnered company login.", "error")
                return render_template("login.html")

            # 1. Verify College Code exists
            cursor.execute("SELECT id, name, code FROM colleges WHERE code = ?", (college_code,))
            college = cursor.fetchone()
            if not college:
                conn.close()
                flash(f"Invalid college code: '{college_code}'. Please check with the institution.", "error")
                return render_template("login.html")

            # 2. Verify Company User Credentials
            cursor.execute("""
                SELECT u.*, comp.id as company_id, comp.name as company_name
                FROM users u
                JOIN companies comp ON u.reference_id = comp.id
                WHERE (u.email = ? OR u.username = ?) AND u.role = 'company'
            """, (identifier.lower(), identifier))
            user = cursor.fetchone()

            if not user or not check_password_hash(user["password_hash"], password):
                conn.close()
                flash("Invalid company credentials.", "error")
                return render_template("login.html")

            # 3. Verify Active College-Company Collaboration
            cursor.execute("""
                SELECT * FROM college_collaborations
                WHERE college_id = ? AND company_id = ? AND status = 'Active'
            """, (college["id"], user["company_id"]))
            collab = cursor.fetchone()

            if not collab:
                conn.close()
                flash(f"Access denied: {user['company_name']} does not have an active partnership with {college['name']} ({college_code}).", "error")
                return render_template("login.html")

            session.clear()
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            session["role"] = "company"
            session["company_id"] = user["company_id"]
            session["company_name"] = user["company_name"]
            session["college_id"] = college["id"]
            session["college_name"] = college["name"]
            session["college_code"] = college["code"]
            session["name"] = f"{user['company_name']} Recruiter"
            conn.close()

            flash(f"Logged in as {user['company_name']} (Partnered with {college['name']})", "success")
            return redirect(url_for("company.dashboard"))

        else:
            conn.close()
            flash("Please choose a valid role to log in.", "error")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/quick-demo-login/<demo_key>")
def quick_demo_login(demo_key):
    """
    1-Click Demo Login switcher for Judges and Hackathon evaluators to test
    different personas instantly without manually typing passwords.
    """
    session.clear()
    conn = get_db()
    cursor = conn.cursor()

    if demo_key == "college_admin":
        cursor.execute("""
            SELECT u.*, c.name as college_name, c.code as college_code
            FROM users u
            JOIN colleges c ON u.college_id = c.id
            WHERE u.email = 'admin@techuniv.edu'
        """)
        u = cursor.fetchone()
        session["user_id"] = u["id"]
        session["email"] = u["email"]
        session["role"] = "college_admin"
        session["college_id"] = u["college_id"]
        session["college_name"] = u["college_name"]
        session["college_code"] = u["college_code"]
        session["name"] = "Tech Univ Placement Administrator"
        conn.close()
        flash("Logged in as College Administrator (Tech University).", "success")
        return redirect(url_for("college.dashboard"))

    elif demo_key == "student_top":
        # Arjun Sharma (Star Day-1 Ready)
        cursor.execute("""
            SELECT s.*, c.name as college_name, c.code as college_code
            FROM students s
            JOIN colleges c ON s.college_id = c.id
            WHERE s.roll_number = '2025CS101'
        """)
        s = cursor.fetchone()
        session["user_id"] = 1001
        session["email"] = s["email"]
        session["role"] = "student"
        session["student_id"] = s["id"]
        session["college_id"] = s["college_id"]
        session["college_name"] = s["college_name"]
        session["college_code"] = s["college_code"]
        session["name"] = s["full_name"]
        session["roll_number"] = s["roll_number"]
        conn.close()
        flash("Logged in as Arjun Sharma (Star Talent / Day-1 Ready persona).", "success")
        return redirect(url_for("student.dashboard"))

    elif demo_key == "student_disconnect":
        # Priya Nair (High Academic / Low Placement Readiness persona)
        cursor.execute("""
            SELECT s.*, c.name as college_name, c.code as college_code
            FROM students s
            JOIN colleges c ON s.college_id = c.id
            WHERE s.roll_number = '2025CS102'
        """)
        s = cursor.fetchone()
        session["user_id"] = 1002
        session["email"] = s["email"]
        session["role"] = "student"
        session["student_id"] = s["id"]
        session["college_id"] = s["college_id"]
        session["college_name"] = s["college_name"]
        session["college_code"] = s["college_code"]
        session["name"] = s["full_name"]
        session["roll_number"] = s["roll_number"]
        conn.close()
        flash("Logged in as Priya Nair (High CGPA 9.15 / Low Practical Readiness persona - member 2 risk flag demo).", "success")
        return redirect(url_for("student.dashboard"))

    elif demo_key == "company_google":
        cursor.execute("SELECT * FROM companies WHERE id = 1")
        comp = cursor.fetchone()
        cursor.execute("SELECT * FROM colleges WHERE id = 1")
        col = cursor.fetchone()
        session["user_id"] = 2001
        session["email"] = "recruiter@google.com"
        session["role"] = "company"
        session["company_id"] = comp["id"]
        session["company_name"] = comp["name"]
        session["college_id"] = col["id"]
        session["college_name"] = col["name"]
        session["college_code"] = col["code"]
        session["name"] = "Google Cloud Campus Recruiter"
        conn.close()
        flash(f"Logged in as Google Cloud Recruiter (Partnered with {col['name']}).", "success")
        return redirect(url_for("company.dashboard"))

    elif demo_key == "company_msft":
        cursor.execute("SELECT * FROM companies WHERE id = 2")
        comp = cursor.fetchone()
        cursor.execute("SELECT * FROM colleges WHERE id = 1")
        col = cursor.fetchone()
        session["user_id"] = 2002
        session["email"] = "recruiter@microsoft.com"
        session["role"] = "company"
        session["company_id"] = comp["id"]
        session["company_name"] = comp["name"]
        session["college_id"] = col["id"]
        session["college_name"] = col["name"]
        session["college_code"] = col["code"]
        session["name"] = "Microsoft Innovation Hub Recruiter"
        conn.close()
        flash(f"Logged in as Microsoft Recruiter (Partnered with {col['name']}).", "success")
        return redirect(url_for("company.dashboard"))

    conn.close()
    flash("Unknown demo persona.", "error")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("login"))


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html", error=str(e)), 500


if __name__ == "__main__":
    init_db()
    seed_demo_data()
    print("Campus2Career AI Server Online on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
