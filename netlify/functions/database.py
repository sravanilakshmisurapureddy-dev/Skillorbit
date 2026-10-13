"""
Campus2Career AI - Database Engine and ORM Layer
Member 1: Data Integration and Database Lead
"""

import sqlite3
import os
import shutil
import datetime
from werkzeug.security import generate_password_hash, check_password_hash


def get_db_path():
    """Returns database path, utilizing writable /tmp in serverless/Lambda environments."""
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('LAMBDA_TASK_ROOT') or os.environ.get('NETLIFY'):
        tmp_db = '/tmp/campus2career.db'
        orig_db = os.path.join(os.path.dirname(__file__), 'campus2career.db')
        if not os.path.exists(tmp_db) and os.path.exists(orig_db):
            try:
                shutil.copyfile(orig_db, tmp_db)
            except Exception:
                pass
        return tmp_db
    return os.path.join(os.path.dirname(__file__), 'campus2career.db')


DB_PATH = get_db_path()


def get_db():
    """Returns a SQLite connection with row-factory enabled."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    """Initializes all database tables required by the system."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Colleges Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS colleges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        contact_email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Users Table (Authentication and RBAC)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('college_admin', 'student', 'company')),
        college_id INTEGER,
        reference_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE SET NULL
    )
    """)

    # 3. Students Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        college_id INTEGER NOT NULL,
        roll_number TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        branch TEXT NOT NULL,
        academic_year TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        cgpa REAL NOT NULL,
        percentage REAL NOT NULL,
        certifications TEXT DEFAULT '',
        programming_languages TEXT DEFAULT '',
        technical_skills TEXT DEFAULT '',
        internship_details TEXT DEFAULT '',
        linkedin_url TEXT DEFAULT '',
        github_url TEXT DEFAULT '',
        soft_skills TEXT DEFAULT '',
        placement_status TEXT DEFAULT 'Eligible' CHECK(placement_status IN ('Eligible', 'Placed', 'Opted Out')),
        consent_status INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
    )
    """)

    # 4. Companies Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        industry TEXT NOT NULL,
        website TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 5. College - Company Collaborations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS college_collaborations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        college_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Pending', 'Terminated')),
        collaborated_since TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(college_id, company_id),
        FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE,
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
    )
    """)

    # 6. Opportunities / Job Postings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        college_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        role_type TEXT DEFAULT 'Full-time' CHECK(role_type IN ('Full-time', 'Internship', 'Special Event')),
        job_description TEXT NOT NULL,
        required_skills TEXT NOT NULL,
        min_cgpa REAL DEFAULT 6.0,
        eligible_branches TEXT DEFAULT 'All',
        salary_or_stipend TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
    )
    """)

    # 7. Student Invitations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invitations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        college_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        opportunity_id INTEGER,
        job_role TEXT NOT NULL,
        job_description TEXT,
        required_skills TEXT,
        eligibility_criteria TEXT,
        message TEXT,
        status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Accepted', 'Declined', 'Withdrawn')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE SET NULL
    )
    """)

    # 8. Shortlists Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shortlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        college_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, student_id),
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
    )
    """)

    # 9. Interventions Table (College Staff Action Items)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        college_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN ('Skill Gap Training', 'Resume Review', 'Mock Interview', 'Academic Tutoring', 'Attendance Counseling', 'Placement Mentoring')),
        notes TEXT,
        status TEXT DEFAULT 'Planned' CHECK(status IN ('Planned', 'In Progress', 'Completed')),
        assigned_to TEXT DEFAULT 'Placement Cell',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
    )
    """)

    # 10. Audit Logs Table (Activity Tracking)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        college_id INTEGER,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        performed_by TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def log_audit(college_id, action, entity_type, entity_id, performed_by, details=""):
    """Helper to append an audit log entry."""
    conn = get_db()
    conn.execute("""
        INSERT INTO audit_logs (college_id, action, entity_type, entity_id, performed_by, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (college_id, action, entity_type, str(entity_id), performed_by, details))
    conn.commit()
    conn.close()


def seed_demo_data():
    """Populates realistic demo data for colleges, users, students, companies, and invitations."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if colleges already exist
    cursor.execute("SELECT COUNT(*) as count FROM colleges")
    if cursor.fetchone()["count"] > 0:
        conn.close()
        return

    # Seed Colleges
    cursor.execute("""
        INSERT INTO colleges (code, name, location, contact_email)
        VALUES 
        ('TECH-2025', 'Tech University of Engineering & Science', 'Silicon Valley Campus, Hyderabad', 'placement@techuniv.edu'),
        ('APEX-2025', 'Apex Institute of Technology & Research', 'Knowledge City, Bengaluru', 'careers@apexinstitute.edu')
    """)
    college_tech_id = 1
    college_apex_id = 2

    # Seed Admin Users
    # Password for all demo accounts:
    # college_admin: admin123
    # companies: google123, msft123, aws123, infy123, deloitte123
    # students: student123
    admin_pw_hash = generate_password_hash("admin123")
    student_pw_hash = generate_password_hash("student123")
    google_pw_hash = generate_password_hash("google123")
    msft_pw_hash = generate_password_hash("msft123")
    aws_pw_hash = generate_password_hash("aws123")
    infy_pw_hash = generate_password_hash("infy123")
    deloitte_pw_hash = generate_password_hash("deloitte123")

    cursor.execute("""
        INSERT INTO users (username, email, phone, password_hash, role, college_id)
        VALUES
        ('admin_tech', 'admin@techuniv.edu', '+91 9876543210', ?, 'college_admin', ?),
        ('admin_apex', 'admin@apexinstitute.edu', '+91 9876543211', ?, 'college_admin', ?)
    """, (admin_pw_hash, college_tech_id, admin_pw_hash, college_apex_id))

    # Seed Companies
    cursor.execute("""
        INSERT INTO companies (name, email, industry, website, description)
        VALUES
        ('Google Cloud & AI Labs', 'recruiter@google.com', 'Technology & Cloud Solutions', 'https://cloud.google.com', 'Global technology leader specializing in search, cloud computing, and AI systems.'),
        ('Microsoft Innovation Hub', 'recruiter@microsoft.com', 'Enterprise Software & Cloud', 'https://microsoft.com', 'World leader in productivity software, Azure cloud, and enterprise computing.'),
        ('Amazon Web Services Talent', 'recruiter@amazon.com', 'Cloud Infrastructure & E-Commerce', 'https://aws.amazon.com', 'Pioneering cloud computing platform powering modern digital businesses.'),
        ('Infosys Digital Campus', 'recruiter@infosys.com', 'IT Consulting & Services', 'https://infosys.com', 'Global leader in next-generation digital services and consulting.'),
        ('Deloitte Consulting Tech', 'recruiter@deloitte.com', 'Advisory & Systems Integration', 'https://deloitte.com', 'Premier global consulting firm delivering digital transformation and strategy.')
    """)

    c_google_id = 1
    c_msft_id = 2
    c_aws_id = 3
    c_infy_id = 4
    c_deloitte_id = 5

    # Company user accounts
    cursor.execute("""
        INSERT INTO users (username, email, phone, password_hash, role, college_id, reference_id)
        VALUES
        ('google_recruiter', 'recruiter@google.com', '+91 9876500001', ?, 'company', ?, ?),
        ('msft_recruiter', 'recruiter@microsoft.com', '+91 9876500002', ?, 'company', ?, ?),
        ('aws_recruiter', 'recruiter@amazon.com', '+91 9876500003', ?, 'company', ?, ?),
        ('infy_recruiter', 'recruiter@infosys.com', '+91 9876500004', ?, 'company', ?, ?),
        ('deloitte_recruiter', 'recruiter@deloitte.com', '+91 9876500005', ?, 'company', ?, ?)
    """, (
        google_pw_hash, college_tech_id, c_google_id,
        msft_pw_hash, college_tech_id, c_msft_id,
        aws_pw_hash, college_tech_id, c_aws_id,
        infy_pw_hash, college_tech_id, c_infy_id,
        deloitte_pw_hash, college_tech_id, c_deloitte_id
    ))

    # Link Collaborations with TECH-2025 (all 5) and APEX-2025 (Infosys, Deloitte)
    cursor.execute("""
        INSERT INTO college_collaborations (college_id, company_id, status)
        VALUES
        (?, ?, 'Active'),
        (?, ?, 'Active'),
        (?, ?, 'Active'),
        (?, ?, 'Active'),
        (?, ?, 'Active'),
        (?, ?, 'Active'),
        (?, ?, 'Active')
    """, (
        college_tech_id, c_google_id,
        college_tech_id, c_msft_id,
        college_tech_id, c_aws_id,
        college_tech_id, c_infy_id,
        college_tech_id, c_deloitte_id,
        college_apex_id, c_infy_id,
        college_apex_id, c_deloitte_id
    ))

    # Seed Opportunities for TECH-2025
    cursor.execute("""
        INSERT INTO opportunities (company_id, college_id, title, role_type, job_description, required_skills, min_cgpa, eligible_branches, salary_or_stipend)
        VALUES
        (?, ?, 'Associate Cloud Software Engineer', 'Full-time', 'Design, build, and deploy high-concurrency microservices on cloud infrastructure.', 'Python, Docker, Kubernetes, AWS/GCP, SQL, Git', 7.5, 'Computer Science, Information Technology, AI & Data Science', '₹16,50,000 / annum'),
        (?, ?, 'Full Stack Software Engineer', 'Full-time', 'Develop enterprise-grade web applications utilizing modern front-end frameworks and robust backend services.', 'JavaScript, React, Node.js, TypeScript, PostgreSQL', 7.0, 'Computer Science, Information Technology, Electronics & Communication', '₹14,00,000 / annum'),
        (?, ?, 'Cloud DevOps Intern', 'Internship', '6-month paid internship focusing on CI/CD pipelines, containerization, and infrastructure-as-code.', 'Linux, Python, Docker, Git, Bash', 6.8, 'All', '₹50,000 / month'),
        (?, ?, 'Systems Engineer Trainee', 'Full-time', 'Exciting entry-level position across global client platforms with comprehensive training.', 'Java, Python, C++, SQL, Problem Solving', 6.5, 'All', '₹7,50,000 / annum'),
        (?, ?, 'Technology Consultant Analyst', 'Full-time', 'Analyze business workflows, design IT architecture solutions, and consult with corporate clients.', 'Python, Data Analysis, SQL, Agile, Communication', 7.0, 'Computer Science, Information Technology, Electronics & Communication', '₹11,00,000 / annum')
    """, (
        c_google_id, college_tech_id,
        c_msft_id, college_tech_id,
        c_aws_id, college_tech_id,
        c_infy_id, college_tech_id,
        c_deloitte_id, college_tech_id
    ))

    # Comprehensive Students Dataset (16 students representing varied performance personas)
    students_data = [
        # 1. Star All-Rounder (High Academic, High Practical)
        (
            college_tech_id, "2025CS101", "Arjun Sharma", "Computer Science & Engineering", "Final Year (2025)",
            "arjun.sharma@techuniv.edu", "+91 9123456701", 9.42, 91.5,
            "AWS Certified Solutions Architect, HackerRank 5-Star Python",
            "Python, C++, TypeScript, Go",
            "Docker, Kubernetes, React, FastAPI, PostgreSQL, Redis",
            "Summer Software Intern at Razorpay (3 months) - Scaled payment webhook processing pipeline.",
            "https://linkedin.com/in/arjun-sharma-tech", "https://github.com/arjunsharma-dev",
            "Team Leadership, Technical Communication, Agile Problem Solving",
            "Eligible", 1
        ),
        # 2. High Academic / Low Placement Readiness (The specific persona Member 2 must flag!)
        (
            college_tech_id, "2025CS102", "Priya Nair", "Computer Science & Engineering", "Final Year (2025)",
            "priya.nair@techuniv.edu", "+91 9123456702", 9.15, 88.0,
            "None",
            "C, Java",
            "Basic SQL, MS Excel",
            "None recorded",
            "https://linkedin.com/in/priyanair-profile", "",
            "Written Communication, Punctuality",
            "Eligible", 1
        ),
        # 3. Practical Builder (Moderate CGPA, Outstanding Coding & Internships)
        (
            college_tech_id, "2025IT201", "Kavya Patel", "Information Technology", "Final Year (2025)",
            "kavya.patel@techuniv.edu", "+91 9123456703", 7.28, 71.0,
            "Meta Frontend Developer Specialization, LeetCode 300+ Solved",
            "JavaScript, TypeScript, Python, HTML/CSS",
            "React, Next.js, Node.js, Express, MongoDB, TailwindCSS, Git",
            "Frontend Engineer Intern at Swiggy (4 months) - Revamped restaurant onboarding web portal.",
            "https://linkedin.com/in/kavyapatel-ui", "https://github.com/kavya-builder",
            "Creative UI Design, Cross-functional Collaboration, Rapid Prototyping",
            "Eligible", 1
        ),
        # 4. AI & Data Specialist
        (
            college_tech_id, "2025AI301", "Rohan Verma", "AI & Data Science", "Final Year (2025)",
            "rohan.verma@techuniv.edu", "+91 9123456704", 8.85, 85.5,
            "TensorFlow Developer Certificate, DeepLearning.AI Specialization",
            "Python, R, SQL, C++",
            "PyTorch, Pandas, Scikit-learn, OpenCV, Hugging Face, MLflow",
            "Computer Vision Research Intern at DRDO Labs (6 months) - Automated satellite imagery analysis.",
            "https://linkedin.com/in/rohanverma-ml", "https://github.com/rohan-ai-labs",
            "Analytical Thinking, Research Documentation, Data Storytelling",
            "Eligible", 1
        ),
        # 5. Core Electronics & Embedded Systems
        (
            college_tech_id, "2025EC401", "Ananya Deshmukh", "Electronics & Communication", "Final Year (2025)",
            "ananya.d@techuniv.edu", "+91 9123456705", 8.35, 81.0,
            "ARM Embedded Systems Certified, MATLAB Associate",
            "C, Embedded C, Python, Verilog",
            "MATLAB, Keil uVision, Arduino, RTOS, PCB Design",
            "Hardware Engineering Intern at Bosch Mobility (3 months) - Sensor integration for telematics.",
            "https://linkedin.com/in/ananya-deshmukh-ec", "https://github.com/ananya-embedded",
            "Root Cause Analysis, Hardware Troubleshooting, Systematic Testing",
            "Eligible", 1
        ),
        # 6. Student Needing Urgent Support / Low Scores
        (
            college_tech_id, "2025CS103", "Vikramaditya Rao", "Computer Science & Engineering", "Final Year (2025)",
            "vikram.rao@techuniv.edu", "+91 9123456706", 5.92, 57.5,
            "None",
            "C++",
            "Basic HTML",
            "None",
            "", "",
            "Adaptability",
            "Eligible", 1
        ),
        # 7. Cloud DevOps Enthusiast
        (
            college_tech_id, "2025IT202", "Neha Sundaram", "Information Technology", "Final Year (2025)",
            "neha.s@techuniv.edu", "+91 9123456707", 8.10, 78.5,
            "AWS Certified Developer Associate, HashiCorp Terraform Associate",
            "Python, Bash, Go, YAML",
            "AWS, Docker, Kubernetes, Terraform, GitHub Actions, Linux",
            "Cloud Ops Intern at Cloud9 Technologies (3 months) - Automated multi-region deployment scripts.",
            "https://linkedin.com/in/nehasundaram-cloud", "https://github.com/neha-cloudops",
            "DevOps Mindset, Incident Management, Documentation",
            "Eligible", 1
        ),
        # 8. Placed Star Candidate
        (
            college_tech_id, "2025CS104", "Tanmay Sen", "Computer Science & Engineering", "Final Year (2025)",
            "tanmay.sen@techuniv.edu", "+91 9123456708", 9.60, 93.0,
            "Google Professional Cloud Architect, ICPC Regional Finalist",
            "Java, C++, Python, Rust",
            "Spring Boot, Microservices, Kafka, PostgreSQL, Distributed Systems",
            "SWE Intern at Atlassian (6 months) - Built high-throughput collaboration APIs.",
            "https://linkedin.com/in/tanmaysen-swe", "https://github.com/tanmay-systems",
            "System Architecture, Mentorship, High-stakes Problem Solving",
            "Placed", 1
        ),
        # 9. Cybersecurity Specialist
        (
            college_tech_id, "2025CS105", "Meera Krishnan", "Computer Science & Engineering", "Final Year (2025)",
            "meera.k@techuniv.edu", "+91 9123456709", 8.40, 82.0,
            "CompTIA Security+, Certified Ethical Hacker (CEH)",
            "Python, Bash, C, Assembly",
            "Wireshark, Metasploit, Burp Suite, Linux, Network Security, SIEM",
            "Security Analyst Intern at QuickHeal (3 months) - Performed vulnerability assessments.",
            "https://linkedin.com/in/meerakrishnan-sec", "https://github.com/meera-cybersec",
            "Ethical Hacking, Risk Assessment, Security Compliance",
            "Eligible", 1
        ),
        # 10. Mechanical Engineering Transitioning to Tech / Robotics
        (
            college_tech_id, "2025ME501", "Sameer Kulkarni", "Mechanical Engineering", "Final Year (2025)",
            "sameer.k@techuniv.edu", "+91 9123456710", 7.65, 74.0,
            "SolidWorks Certified Professional, ROS Basics Certificate",
            "Python, C++, MATLAB",
            "ROS2, SolidWorks, OpenCV, Fusion 360, Linux",
            "Robotics Intern at Tata Advanced Systems (3 months) - Kinematics modeling for robotic arm.",
            "https://linkedin.com/in/sameerkulkarni-robotics", "https://github.com/sameer-robotics",
            "Interdisciplinary Coordination, Mechanical CAD, Precision Fabrication",
            "Eligible", 1
        ),
        # 11. Third Year Rising Star (Pre-final year)
        (
            college_tech_id, "2026CS201", "Divya Raghavan", "Computer Science & Engineering", "Third Year (2026)",
            "divya.r@techuniv.edu", "+91 9123456711", 8.90, 86.0,
            "Oracle Certified Java Associate",
            "Java, Python, Kotlin",
            "Android SDK, Spring Boot, MySQL, Git",
            "Mobile App Development Intern at Local FinTech Startup (2 months).",
            "https://linkedin.com/in/divyaraghavan-dev", "https://github.com/divya-mobileapps",
            "User Centric Design, Fast Learner, Empathy",
            "Eligible", 1
        ),
        # 12. Emerging Web Developer
        (
            college_tech_id, "2025IT203", "Aakash Gupta", "Information Technology", "Final Year (2025)",
            "aakash.g@techuniv.edu", "+91 9123456712", 7.10, 69.5,
            "FreeCodeCamp Full Stack Certificate",
            "JavaScript, Python, HTML/CSS",
            "Django, React, SQLite, Bootstrap",
            "None recorded",
            "https://linkedin.com/in/aakashgupta-web", "https://github.com/aakash-fullstack",
            "Persistence, Enthusiastic Learner",
            "Eligible", 1
        ),
        # 13. High Academic / Academic Focus / Low Tech breadth
        (
            college_tech_id, "2025EC402", "Siddharth Menon", "Electronics & Communication", "Final Year (2025)",
            "siddharth.m@techuniv.edu", "+91 9123456713", 8.75, 84.5,
            "None",
            "C, MATLAB",
            "VLSI Basics, Verilog",
            "None recorded",
            "https://linkedin.com/in/siddharthmenon-ec", "",
            "Analytical Thinking, Math Aptitude",
            "Eligible", 1
        ),
        # 14. ECE / Embedded IoT Developer
        (
            college_tech_id, "2025EC403", "Pooja Hegde", "Electronics & Communication", "Final Year (2025)",
            "pooja.h@techuniv.edu", "+91 9123456714", 7.95, 77.0,
            "Cisco Certified Network Associate (CCNA)",
            "Python, C, Embedded C",
            "Raspberry Pi, MQTT, AWS IoT, ESP32, Wireshark",
            "IoT Firmware Intern at L&T Smart World (3 months) - Smart streetlight monitoring.",
            "https://linkedin.com/in/poojahegde-iot", "https://github.com/pooja-iot-devices",
            "Hands-on Prototyping, Network Debugging",
            "Eligible", 1
        ),
        # 15. Student with Opted-out / Higher Studies plan
        (
            college_tech_id, "2025CS106", "Karthik Nambiar", "Computer Science & Engineering", "Final Year (2025)",
            "karthik.n@techuniv.edu", "+91 9123456715", 9.10, 89.0,
            "GRE Score 332, TOEFL 115",
            "Python, C++",
            "Algorithms, Graph Theory, LaTeX",
            "Academic Research Fellow at IIT Madras (4 months) - Theoretical computer science.",
            "https://linkedin.com/in/karthiknambiar-research", "https://github.com/karthik-research",
            "Research Paper Writing, Mathematical Rigor",
            "Opted Out", 0
        ),
        # 16. Apex Institute Demo Student
        (
            college_apex_id, "2025AP101", "Sneha Roy", "Computer Science & Engineering", "Final Year (2025)",
            "sneha.roy@apexinstitute.edu", "+91 9123456716", 8.60, 83.0,
            "Microsoft Certified: Azure Fundamentals",
            "Java, Python, SQL",
            "Azure, Spring Boot, MySQL, Docker",
            "Junior Developer Intern at Wipro (2 months).",
            "https://linkedin.com/in/sneharoy-tech", "https://github.com/sneha-roy-apex",
            "Collaborative, Quick Learner",
            "Eligible", 1
        )
    ]

    for s in students_data:
        cursor.execute("""
            INSERT INTO students (
                college_id, roll_number, full_name, branch, academic_year,
                email, phone, cgpa, percentage, certifications,
                programming_languages, technical_skills, internship_details,
                linkedin_url, github_url, soft_skills, placement_status, consent_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, s)
        student_id = cursor.lastrowid

        # Create student user authentication record
        # Note: Students log in using their email or phone number + password (default 'student123')
        cursor.execute("""
            INSERT INTO users (username, email, phone, password_hash, role, college_id, reference_id)
            VALUES (?, ?, ?, ?, 'student', ?, ?)
        """, (s[1], s[5], s[6], student_pw_hash, s[0], student_id))

    # Seed Sample Invitations
    # Arjun Sharma (id: 1) -> Invited by Google & Microsoft
    cursor.execute("""
        INSERT INTO invitations (
            company_id, college_id, student_id, opportunity_id,
            job_role, job_description, required_skills, eligibility_criteria,
            message, status, created_at, updated_at
        )
        VALUES
        (?, ?, 1, 1, 'Associate Cloud Software Engineer', 
         'Build high-performance microservices and cloud automation at Google Cloud.', 
         'Python, Docker, Kubernetes, AWS/GCP, SQL, Git', 'CGPA >= 7.5, Strong CS Fundamentals',
         'Hello Arjun! Your exceptional profile and open-source cloud projects caught our attention. We invite you to interview for our Cloud Engineering team.',
         'Pending', datetime('now', '-2 days'), datetime('now', '-2 days')),

        (?, ?, 1, 2, 'Full Stack Software Engineer', 
         'Enterprise software engineering for Azure cloud developer services.', 
         'JavaScript, React, Node.js, TypeScript, PostgreSQL', 'CGPA >= 7.0, Proven full-stack projects',
         'Hi Arjun, Microsoft Innovation Hub is impressed by your Razorpay internship and technical stack. We would love to discuss an interview opportunity.',
         'Accepted', datetime('now', '-4 days'), datetime('now', '-1 days')),

        (?, ?, 3, 2, 'Full Stack Software Engineer', 
         'Enterprise software engineering for Azure cloud developer services.', 
         'React, Next.js, Node.js, Express, MongoDB, TailwindCSS, Git', 'CGPA >= 7.0, Strong UI/UX focus',
         'Hi Kavya, your React/Next.js portfolio and Swiggy internship work align perfectly with our frontend team requirements.',
         'Pending', datetime('now', '-1 days'), datetime('now', '-1 days')),

        (?, ?, 4, 1, 'Associate Cloud Software Engineer', 
         'Build AI/ML inference infrastructure on cloud.', 
         'Python, PyTorch, Docker, Linux, SQL', 'CGPA >= 7.5, Deep learning familiarity',
         'Hello Rohan, your DRDO computer vision internship and ML credentials make you a standout candidate for our AI infrastructure team.',
         'Declined', datetime('now', '-5 days'), datetime('now', '-2 days')),

        (?, ?, 7, 3, 'Cloud DevOps Intern', 
         '6-month paid internship focusing on CI/CD pipelines and infrastructure-as-code.', 
         'Linux, Python, Docker, Git, Terraform', 'CGPA >= 6.8',
         'Neha, your AWS and Terraform certifications demonstrate exactly the skills we need for our DevOps internship drive.',
         'Pending', datetime('now', '-6 hours'), datetime('now', '-6 hours'))
    """, (
        c_google_id, college_tech_id,
        c_msft_id, college_tech_id,
        c_msft_id, college_tech_id,
        c_google_id, college_tech_id,
        c_aws_id, college_tech_id
    ))

    # Seed Sample Shortlists
    cursor.execute("""
        INSERT INTO shortlists (company_id, student_id, college_id)
        VALUES
        (?, 1, ?),
        (?, 4, ?),
        (?, 7, ?),
        (?, 1, ?),
        (?, 3, ?)
    """, (
        c_google_id, college_tech_id,
        c_google_id, college_tech_id,
        c_aws_id, college_tech_id,
        c_msft_id, college_tech_id,
        c_msft_id, college_tech_id
    ))

    # Seed Sample Interventions for College Dashboard tracking
    cursor.execute("""
        INSERT INTO interventions (student_id, college_id, title, category, notes, status, assigned_to)
        VALUES
        (2, ?, 'Placement Readiness Mentoring & Practical Project Assignment', 'Skill Gap Training', 'Student possesses outstanding 9.15 CGPA but lacks practical GitHub projects and internships. Assigned to Professor Rao for live web-app capstone guidance.', 'In Progress', 'Prof. K. Rao (Placement Coordinator)'),
        (6, ?, 'Remedial Coding & Academic Counseling', 'Academic Tutoring', 'Low CGPA (5.92) and basic coding proficiency. Enrolled in 4-week weekend Data Structures intensive tutoring and mock tests.', 'Planned', 'Prof. S. Mehra'),
        (12, ?, 'Resume Review & Competitive Coding Target', 'Resume Review', 'Review portfolio projects and encourage LeetCode problem practice to improve technical round clearance rate.', 'Completed', 'Placement Cell Mentor Team')
    """, (college_tech_id, college_tech_id, college_tech_id))

    # Seed Initial Audit Logs
    cursor.execute("""
        INSERT INTO audit_logs (college_id, action, entity_type, entity_id, performed_by, details)
        VALUES
        (?, 'SYSTEM_INIT', 'DATABASE', 'ALL', 'System Seed Script', 'Initial system seed executed with colleges, sample students, and industry partners.'),
        (?, 'CREATE_STUDENT', 'STUDENT', '2025CS101', 'admin@techuniv.edu', 'Profile created with roll number 2025CS101 for Arjun Sharma.'),
        (?, 'INVITATION_SENT', 'INVITATION', '1', 'recruiter@google.com', 'Sent invitation to student Arjun Sharma for Cloud Software Engineer.'),
        (?, 'INVITATION_STATUS_UPDATE', 'INVITATION', '2', 'arjun.sharma@techuniv.edu', 'Student accepted invitation from Microsoft Innovation Hub.')
    """, (college_tech_id, college_tech_id, college_tech_id, college_tech_id))

    conn.commit()
    conn.close()


def reset_student_password(student_id, new_password):
    """Resets the password for a student user account."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT email, roll_number FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return False, "Student record not found"

    new_hash = generate_password_hash(new_password)
    cursor.execute("""
        UPDATE users 
        SET password_hash = ? 
        WHERE (email = ? OR username = ?) AND role = 'student'
    """, (new_hash, student["email"], student["roll_number"]))
    conn.commit()
    conn.close()
    return True, "Password reset successfully"


def add_student_record(college_id, student_data, password="student123"):
    """Adds a single student to database and generates their login user account."""
    conn = get_db()
    cursor = conn.cursor()

    # Check for duplicate roll_number or email
    cursor.execute("SELECT id FROM students WHERE roll_number = ? OR email = ?", 
                   (student_data['roll_number'], student_data['email']))
    if cursor.fetchone():
        conn.close()
        return False, "Student with this roll number or email already exists."

    cursor.execute("""
        INSERT INTO students (
            college_id, roll_number, full_name, branch, academic_year,
            email, phone, cgpa, percentage, certifications,
            programming_languages, technical_skills, internship_details,
            linkedin_url, github_url, soft_skills, placement_status, consent_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        college_id,
        student_data['roll_number'].strip(),
        student_data['full_name'].strip(),
        student_data['branch'].strip(),
        student_data.get('academic_year', 'Final Year (2025)').strip(),
        student_data['email'].strip().lower(),
        student_data.get('phone', '').strip(),
        float(student_data['cgpa']),
        float(student_data.get('percentage', float(student_data['cgpa']) * 9.5)),
        student_data.get('certifications', '').strip(),
        student_data.get('programming_languages', '').strip(),
        student_data.get('technical_skills', '').strip(),
        student_data.get('internship_details', '').strip(),
        student_data.get('linkedin_url', '').strip(),
        student_data.get('github_url', '').strip(),
        student_data.get('soft_skills', '').strip(),
        student_data.get('placement_status', 'Eligible'),
        int(student_data.get('consent_status', 1))
    ))
    new_student_id = cursor.lastrowid

    # Create User login credentials
    user_pw_hash = generate_password_hash(password)
    cursor.execute("""
        INSERT INTO users (username, email, phone, password_hash, role, college_id, reference_id)
        VALUES (?, ?, ?, ?, 'student', ?, ?)
    """, (
        student_data['roll_number'].strip(),
        student_data['email'].strip().lower(),
        student_data.get('phone', '').strip(),
        user_pw_hash,
        college_id,
        new_student_id
    ))

    conn.commit()
    conn.close()

    log_audit(college_id, "CREATE_STUDENT", "STUDENT", new_student_id, 
              "College Staff", f"Created student {student_data['full_name']} ({student_data['roll_number']})")
    return True, new_student_id


def update_student_record(student_id, college_id, update_data):
    """Updates an existing student's college-managed record."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE id = ? AND college_id = ?", (student_id, college_id))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return False, "Student not found or access denied."

    cursor.execute("""
        UPDATE students SET
            full_name = ?,
            branch = ?,
            academic_year = ?,
            phone = ?,
            cgpa = ?,
            percentage = ?,
            certifications = ?,
            programming_languages = ?,
            technical_skills = ?,
            internship_details = ?,
            linkedin_url = ?,
            github_url = ?,
            soft_skills = ?,
            placement_status = ?,
            consent_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND college_id = ?
    """, (
        update_data.get('full_name', existing['full_name']),
        update_data.get('branch', existing['branch']),
        update_data.get('academic_year', existing['academic_year']),
        update_data.get('phone', existing['phone']),
        float(update_data.get('cgpa', existing['cgpa'])),
        float(update_data.get('percentage', existing['percentage'])),
        update_data.get('certifications', existing['certifications']),
        update_data.get('programming_languages', existing['programming_languages']),
        update_data.get('technical_skills', existing['technical_skills']),
        update_data.get('internship_details', existing['internship_details']),
        update_data.get('linkedin_url', existing['linkedin_url']),
        update_data.get('github_url', existing['github_url']),
        update_data.get('soft_skills', existing['soft_skills']),
        update_data.get('placement_status', existing['placement_status']),
        int(update_data.get('consent_status', existing['consent_status'])),
        student_id,
        college_id
    ))
    conn.commit()
    conn.close()

    log_audit(college_id, "UPDATE_STUDENT", "STUDENT", student_id, 
              "College Staff", f"Updated student profile ID {student_id}")
    return True, "Profile updated successfully."


def delete_student_record(student_id, college_id):
    """Deletes a student record and associated user login."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT roll_number, email, full_name FROM students WHERE id = ? AND college_id = ?", 
                   (student_id, college_id))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return False, "Student record not found."

    cursor.execute("DELETE FROM users WHERE college_id = ? AND (email = ? OR username = ?)", 
                   (college_id, student["email"], student["roll_number"]))
    cursor.execute("DELETE FROM invitations WHERE student_id = ?", (student_id,))
    cursor.execute("DELETE FROM shortlists WHERE student_id = ?", (student_id,))
    cursor.execute("DELETE FROM interventions WHERE student_id = ?", (student_id,))
    cursor.execute("DELETE FROM students WHERE id = ? AND college_id = ?", (student_id, college_id))

    conn.commit()
    conn.close()

    log_audit(college_id, "DELETE_STUDENT", "STUDENT", student_id, 
              "College Staff", f"Deleted student {student['full_name']} ({student['roll_number']})")
    return True, "Student record and credentials deleted."
