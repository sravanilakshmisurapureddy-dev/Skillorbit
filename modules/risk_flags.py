"""
Campus2Career AI - Evidence-Based Risk Flags Engine
Member 2: Analytics & AI Logic Lead
Identifies placement vulnerabilities and produces actionable remediation steps.
"""

from modules.success_score import calculate_student_success_score, _parse_list


def evaluate_student_risk_flags(student_dict, score_data=None):
    """
    Evaluates evidence-based placement risk flags for a student.
    Returns list of risk flag objects with severity, reason, and recommended actions.
    """
    if score_data is None:
        score_data = calculate_student_success_score(student_dict)

    flags = []
    cgpa = float(student_dict.get("cgpa", 0.0) or 0.0)
    internship = str(student_dict.get("internship_details", "")).strip()
    has_internship = bool(internship and internship.lower() not in ["none", "none recorded", "n/a", ""])
    github = str(student_dict.get("github_url", "")).strip()
    has_github = bool(github and "github.com" in github.lower())
    linkedin = str(student_dict.get("linkedin_url", "")).strip()
    has_linkedin = bool(linkedin and "linkedin.com" in linkedin.lower())
    
    langs = _parse_list(student_dict.get("programming_languages", ""))
    skills = _parse_list(student_dict.get("technical_skills", ""))
    certs = _parse_list(student_dict.get("certifications", ""))
    soft_skills = _parse_list(student_dict.get("soft_skills", ""))

    tech_score = score_data["pillars"]["technical"]["score"]
    prac_score = score_data["pillars"]["practical"]["score"]

    # 1. CORE DISCONNECT: High Academics but Low Placement Readiness
    # Student scores high marks in exams, but lacks practical coding/internship readiness
    if cgpa >= 8.2 and (tech_score < 15.0 or prac_score <= 5.0):
        flags.append({
            "code": "HIGH_ACADEMIC_LOW_READINESS",
            "title": "High Academics / Low Placement Readiness Disconnect",
            "severity": "critical",
            "icon": "alert-triangle",
            "evidence": f"Outstanding CGPA of {cgpa:.2f}, but technical competency is only {tech_score:.1f}/30 and practical experience is {prac_score:.1f}/25.",
            "recommended_action": "Assign to hands-on software development capstone and mandate a 4-week industry micro-internship before campus drive."
        })

    # 2. Critical Academic Risk
    if cgpa < 6.5:
        flags.append({
            "code": "ACADEMIC_AT_RISK",
            "title": "Below Corporate Eligibility CGPA Cutoff",
            "severity": "critical",
            "icon": "shield-alert",
            "evidence": f"Current CGPA is {cgpa:.2f}. Most tier-1 recruiters require a minimum 6.50 - 7.00 threshold.",
            "recommended_action": "Schedule immediate academic tutoring for upcoming semester subjects and focus on high-weightage internal assignments."
        })

    # 3. Missing Industry Internship
    if not has_internship:
        flags.append({
            "code": "NO_INTERNSHIP_EXPERIENCE",
            "title": "No Verified Practical Industry Internship",
            "severity": "warning",
            "icon": "briefcase",
            "evidence": "Student has no recorded industry internship or corporate training on file.",
            "recommended_action": "Connect student to placement cell partnered summer internships or college incubation live projects."
        })

    # 4. Technical Breadth Gap
    if len(langs) < 2 or len(skills) < 2:
        flags.append({
            "code": "TECHNICAL_BREADTH_GAP",
            "title": "Narrow Programming & Framework Stack",
            "severity": "warning",
            "icon": "code",
            "evidence": f"Recorded stack includes only {len(langs)} language(s) and {len(skills)} framework(s).",
            "recommended_action": "Enroll in high-demand full stack or cloud certification workshops (e.g. AWS Cloud Practitioner, Docker & React)."
        })

    # 5. Missing Public Code Proof / GitHub Portfolio
    if not has_github:
        flags.append({
            "code": "NO_GITHUB_PORTFOLIO",
            "title": "Missing Public GitHub Repository Proof",
            "severity": "info",
            "icon": "git-branch",
            "evidence": "No active GitHub or portfolio link attached to profile.",
            "recommended_action": "Conduct a Git & GitHub workshop to assist student in publishing 2 substantial full-stack or data projects with clean READMEs."
        })

    # 6. Incomplete Professional Digital Footprint
    if not has_linkedin or len(soft_skills) == 0:
        flags.append({
            "code": "PROFESSIONAL_FOOTPRINT_GAP",
            "title": "Incomplete Professional Digital Presence",
            "severity": "info",
            "icon": "user-check",
            "evidence": "Missing LinkedIn profile or soft skills self-assessment.",
            "recommended_action": "Host placement cell profile optimization clinic to set up professional LinkedIn headline and summary."
        })

    return flags
