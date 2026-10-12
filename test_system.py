"""
Campus2Career AI - Full System Integration Test Suite
Member 5: Integration, Testing & Demo Lead
Validates database integrity, analytics, scoring, risk flags, matching, and Flask routes.
"""

import unittest
from app import app
from database import get_db, init_db, seed_demo_data
from modules.success_score import calculate_student_success_score
from modules.risk_flags import evaluate_student_risk_flags
from modules.segmentation import classify_student_segment, compute_cohort_segmentation
from modules.matching import compute_student_opportunity_match
from modules.data_integration import process_csv_upload, get_data_dictionary


class TestCampus2CareerSystem(unittest.TestCase):
    def setUp(self):
        init_db()
        seed_demo_data()
        self.app = app.test_client()
        self.app.testing = True

    def test_database_counts(self):
        conn = get_db()
        colleges = conn.execute("SELECT COUNT(*) FROM colleges").fetchone()[0]
        students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        companies = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()

        self.assertGreaterEqual(colleges, 2, "Expected at least 2 colleges")
        self.assertGreaterEqual(students, 15, "Expected at least 15 students")
        self.assertGreaterEqual(companies, 5, "Expected at least 5 companies")
        self.assertGreaterEqual(users, 20, "Expected generated user credentials")

    def test_scoring_and_risk_engine(self):
        conn = get_db()
        # Fetch Arjun (Star)
        arjun = dict(conn.execute("SELECT * FROM students WHERE roll_number = '2025CS101'").fetchone())
        # Fetch Priya (High Academics / Low Practical)
        priya = dict(conn.execute("SELECT * FROM students WHERE roll_number = '2025CS102'").fetchone())
        conn.close()

        # Score Arjun
        arjun_score = calculate_student_success_score(arjun)
        self.assertGreater(arjun_score["overall_score"], 85.0)

        # Score Priya
        priya_score = calculate_student_success_score(priya)
        priya_flags = evaluate_student_risk_flags(priya, priya_score)
        priya_seg = classify_student_segment(priya, priya_score)

        # Verify that Member 2's specific requirement is detected!
        has_disconnect = any(f["code"] == "HIGH_ACADEMIC_LOW_READINESS" for f in priya_flags)
        self.assertTrue(has_disconnect, "Priya Nair should trigger HIGH_ACADEMIC_LOW_READINESS flag")
        self.assertEqual(priya_seg["key"], "HIGH_ACADEMIC_LOW_PRACTICAL")

    def test_talent_matching_engine(self):
        conn = get_db()
        arjun = dict(conn.execute("SELECT * FROM students WHERE roll_number = '2025CS101'").fetchone())
        opp = dict(conn.execute("SELECT * FROM opportunities WHERE id = 1").fetchone())
        conn.close()

        match = compute_student_opportunity_match(arjun, opp)
        self.assertGreaterEqual(match["match_percentage"], 75.0)
        self.assertTrue(match["is_eligible"])
        self.assertIn("Python", match["matched_skills"])

    def test_flask_routes_and_rbac(self):
        # 1. Landing Page
        res = self.app.get("/")
        self.assertEqual(res.status_code, 200)

        # 2. Login Page
        res = self.app.get("/login")
        self.assertEqual(res.status_code, 200)

        # 3. Unauthorized access to college dashboard without login
        res = self.app.get("/college/dashboard")
        self.assertEqual(res.status_code, 302)  # Redirects to login

        # 4. College Admin Demo Login
        res = self.app.get("/quick-demo-login/college_admin", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Tech University", res.data)

        # 5. Student Profile view from College Admin
        res = self.app.get("/college/student/1")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Arjun Sharma", res.data)

        # 6. Student Demo Login
        res = self.app.get("/quick-demo-login/student_top", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Recruitment Invitations Hub", res.data)

        # 7. Student RBAC: Student cannot access College Dashboard
        res = self.app.get("/college/dashboard")
        self.assertEqual(res.status_code, 302)

        # 8. Company Demo Login
        res = self.app.get("/quick-demo-login/company_google", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Candidate Discovery", res.data)


if __name__ == "__main__":
    unittest.main()
