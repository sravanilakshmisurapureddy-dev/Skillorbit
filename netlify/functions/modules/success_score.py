"""
Campus2Career AI - Explainable Student Success Score Engine
Member 2: Analytics & AI Logic Lead
Calculates a multi-dimensional, transparent 0-100 readiness score with explainable indicator breakdown.
"""

def _parse_list(val):
    if not val or str(val).lower() in ["none", "none recorded", "n/a", ""]:
        return []
    items = [x.strip() for x in str(val).split(",") if x.strip()]
    return [x for x in items if x.lower() not in ["none", "none recorded", "n/a"]]


def calculate_student_success_score(student_dict):
    """
    Computes transparent Student Success Score (0-100) across 4 core pillars:
    - Academic Pillar (30 max)
    - Technical Competency Pillar (30 max)
    - Practical Experience Pillar (25 max)
    - Professional & Soft Skills Pillar (15 max)
    
    Returns structured dictionary with overall score, pillar sub-scores,
    and positive/negative indicator explanations.
    """
    positive_indicators = []
    negative_indicators = []

    # 1. ACADEMIC PILLAR (Max 30)
    cgpa = float(student_dict.get("cgpa", 0.0) or 0.0)
    # CGPA component: 0.0 to 10.0 scaled to 30
    academic_score = min(30.0, max(0.0, (cgpa / 10.0) * 30.0))
    academic_pct = (academic_score / 30.0) * 100.0

    if cgpa >= 9.0:
        positive_indicators.append(f"Outstanding academic standing (CGPA {cgpa:.2f} / 10.0)")
    elif cgpa >= 7.5:
        positive_indicators.append(f"Solid academic foundation (CGPA {cgpa:.2f} / 10.0)")
    elif cgpa < 6.5:
        negative_indicators.append(f"Low academic average (CGPA {cgpa:.2f} / 10.0), below most corporate eligibility filters")

    # 2. TECHNICAL COMPETENCY PILLAR (Max 30)
    # Breakdown: Languages (10 pts), Tools/Frameworks (10 pts), Certifications (10 pts)
    langs = _parse_list(student_dict.get("programming_languages", ""))
    skills = _parse_list(student_dict.get("technical_skills", ""))
    certs = _parse_list(student_dict.get("certifications", ""))

    # Languages scoring: 3+ languages = 10 pts, 2 = 7 pts, 1 = 4 pts, 0 = 0 pts
    if len(langs) >= 3:
        lang_score = 10.0
        positive_indicators.append(f"Broad polyglot coding foundations ({len(langs)} languages: {', '.join(langs[:3])})")
    elif len(langs) == 2:
        lang_score = 7.0
    elif len(langs) == 1:
        lang_score = 4.0
        negative_indicators.append(f"Single programming language known ({langs[0]}); industry prefers versatile coding knowledge")
    else:
        lang_score = 0.0
        negative_indicators.append("No verified programming languages recorded")

    # Skills scoring: 4+ tools = 10 pts, 3 = 7.5 pts, 2 = 5 pts, 1 = 2.5 pts, 0 = 0 pts
    if len(skills) >= 4:
        skill_score = 10.0
        positive_indicators.append(f"Strong modern tech stack mastery ({len(skills)} tools/frameworks)")
    elif len(skills) == 3:
        skill_score = 7.5
    elif len(skills) == 2:
        skill_score = 5.0
    elif len(skills) == 1:
        skill_score = 2.5
    else:
        skill_score = 0.0
        negative_indicators.append("Limited modern framework/database exposure")

    # Certifications scoring: 2+ certs = 10 pts, 1 cert = 6 pts, 0 certs = 0 pts
    if len(certs) >= 2:
        cert_score = 10.0
        positive_indicators.append(f"Multiple industry certifications verified ({', '.join(certs[:2])})")
    elif len(certs) == 1:
        cert_score = 6.0
        positive_indicators.append(f"Recognized credential: {certs[0]}")
    else:
        cert_score = 0.0
        negative_indicators.append("No cloud or professional credentials documented")

    technical_score = lang_score + skill_score + cert_score
    technical_pct = (technical_score / 30.0) * 100.0

    # 3. PRACTICAL EXPERIENCE PILLAR (Max 25)
    # Internship (15 pts) + GitHub/Project evidence (10 pts)
    internship = str(student_dict.get("internship_details", "")).strip()
    github = str(student_dict.get("github_url", "")).strip()

    intern_score = 0.0
    if internship and internship.lower() not in ["none", "none recorded", "n/a", ""]:
        intern_score = 15.0
        positive_indicators.append("Verified real-world industry internship experience")
    else:
        negative_indicators.append("No practical internship recorded")

    github_score = 0.0
    if github and "github.com" in github.lower():
        github_score = 10.0
        positive_indicators.append("Public GitHub portfolio with transparent code proof")
    else:
        github_score = 0.0
        negative_indicators.append("Missing public GitHub repository proof")

    practical_score = intern_score + github_score
    practical_pct = (practical_score / 25.0) * 100.0

    # 4. PROFESSIONAL & SOFT SKILLS PILLAR (Max 15)
    # LinkedIn (8 pts) + Soft Skills (7 pts)
    linkedin = str(student_dict.get("linkedin_url", "")).strip()
    soft_skills = _parse_list(student_dict.get("soft_skills", ""))

    linkedin_score = 8.0 if (linkedin and "linkedin.com" in linkedin.lower()) else 0.0
    if linkedin_score > 0:
        positive_indicators.append("Professional LinkedIn profile linked")
    else:
        negative_indicators.append("LinkedIn profile not linked")

    if len(soft_skills) >= 3:
        soft_score = 7.0
        positive_indicators.append(f"Demonstrated interpersonal skills ({', '.join(soft_skills[:3])})")
    elif len(soft_skills) >= 1:
        soft_score = 4.0
    else:
        soft_score = 0.0
        negative_indicators.append("No soft skills or leadership attributes documented")

    professional_score = linkedin_score + soft_score
    professional_pct = (professional_score / 15.0) * 100.0

    # OVERALL SCORE (Max 100)
    overall_score = round(academic_score + technical_score + practical_score + professional_score, 1)

    # Determine Grade and Tier
    if overall_score >= 88.0:
        grade = "S Tier (Day-1 Ready)"
        badge_class = "badge-emerald"
    elif overall_score >= 75.0:
        grade = "A Tier (Highly Competitive)"
        badge_class = "badge-blue"
    elif overall_score >= 60.0:
        grade = "B Tier (Placement Ready)"
        badge_class = "badge-amber"
    elif overall_score >= 45.0:
        grade = "C Tier (Emerging Potential)"
        badge_class = "badge-orange"
    else:
        grade = "D Tier (Urgent Intervention Needed)"
        badge_class = "badge-red"

    return {
        "overall_score": overall_score,
        "grade": grade,
        "badge_class": badge_class,
        "pillars": {
            "academic": {
                "score": round(academic_score, 1),
                "max": 30.0,
                "percentage": round(academic_pct, 1),
                "label": "Academic Foundation (CGPA)"
            },
            "technical": {
                "score": round(technical_score, 1),
                "max": 30.0,
                "percentage": round(technical_pct, 1),
                "label": "Technical Stack & Certifications"
            },
            "practical": {
                "score": round(practical_score, 1),
                "max": 25.0,
                "percentage": round(practical_pct, 1),
                "label": "Internship & GitHub Evidence"
            },
            "professional": {
                "score": round(professional_score, 1),
                "max": 15.0,
                "percentage": round(professional_pct, 1),
                "label": "Soft Skills & Professional Brand"
            }
        },
        "positive_indicators": positive_indicators,
        "negative_indicators": negative_indicators
    }
