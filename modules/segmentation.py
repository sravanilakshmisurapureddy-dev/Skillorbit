"""
Campus2Career AI - Student Segmentation Engine
Member 2: Analytics & AI Logic Lead
Segments student populations into actionable cohorts for targeted training and specialized recruitment.
"""

from modules.success_score import calculate_student_success_score


SEGMENT_DEFINITIONS = {
    "STAR_TALENT": {
        "title": "Star Talent / Day-1 Ready",
        "description": "High CGPA, proven coding competence, verified internships, and complete portfolio.",
        "badge_class": "badge-emerald",
        "color": "#10b981",
        "recruiter_pitch": "Prime candidates for Tier-1 engineering roles and competitive packages."
    },
    "HIGH_ACADEMIC_LOW_PRACTICAL": {
        "title": "High Academics / Low Practical Readiness",
        "description": "High exam marks (CGPA >= 8.0) but limited industry frameworks, internships, or GitHub code.",
        "badge_class": "badge-purple",
        "color": "#8b5cf6",
        "recruiter_pitch": "Strong intellect with quick learning capacity; requires practical bootcamps."
    },
    "PRACTICAL_BUILDERS": {
        "title": "Practical Builders & Hackers",
        "description": "Moderate academic CGPA with exceptional project proof, GitHub code, and internship experience.",
        "badge_class": "badge-cyan",
        "color": "#06b6d4",
        "recruiter_pitch": "Ready to write production code immediately; pragmatic problem solvers."
    },
    "EMERGING_CONTENDERS": {
        "title": "Emerging Contenders",
        "description": "Balanced academic and technical foundations; needs targeted interview prep to break into top tiers.",
        "badge_class": "badge-blue",
        "color": "#3b82f6",
        "recruiter_pitch": "Great potential for structured graduate training programs."
    },
    "PRIORITY_SUPPORT": {
        "title": "Needs Priority Support",
        "description": "At risk of missing corporate cutoffs; requires remedial mentoring and foundational skill building.",
        "badge_class": "badge-red",
        "color": "#ef4444",
        "recruiter_pitch": "Enrolled in intensive placement cell remediation programs."
    }
}


def classify_student_segment(student_dict, score_data=None):
    """
    Assigns a student into one of the 5 key segmentation cohorts.
    """
    if score_data is None:
        score_data = calculate_student_success_score(student_dict)

    cgpa = float(student_dict.get("cgpa", 0.0) or 0.0)
    overall = score_data["overall_score"]
    tech_score = score_data["pillars"]["technical"]["score"]
    prac_score = score_data["pillars"]["practical"]["score"]

    # Segment 1: High Academics but Low Placement Readiness (The specific persona Member 2 must flag)
    if cgpa >= 8.2 and (tech_score < 14.0 or prac_score <= 5.0):
        segment_key = "HIGH_ACADEMIC_LOW_PRACTICAL"

    # Segment 2: Star Talent / Day-1 Ready
    elif overall >= 82.0 and cgpa >= 7.8 and prac_score >= 15.0:
        segment_key = "STAR_TALENT"

    # Segment 3: Practical Builders
    elif prac_score >= 18.0 and tech_score >= 18.0 and cgpa < 8.0:
        segment_key = "PRACTICAL_BUILDERS"

    # Segment 4: Priority Support
    elif cgpa < 6.5 or overall < 48.0:
        segment_key = "PRIORITY_SUPPORT"

    # Segment 5: Emerging Contenders
    else:
        segment_key = "EMERGING_CONTENDERS"

    info = SEGMENT_DEFINITIONS[segment_key]
    return {
        "key": segment_key,
        "title": info["title"],
        "description": info["description"],
        "badge_class": info["badge_class"],
        "color": info["color"],
        "recruiter_pitch": info["recruiter_pitch"]
    }


def compute_cohort_segmentation(students_list):
    """
    Computes distribution of segments across an entire student cohort.
    Returns breakdown counts, percentages, and categorized student lists.
    """
    breakdown = {k: {"count": 0, "students": []} for k in SEGMENT_DEFINITIONS.keys()}
    total = len(students_list)

    for s in students_list:
        score = calculate_student_success_score(s)
        seg = classify_student_segment(s, score)
        breakdown[seg["key"]]["count"] += 1
        breakdown[seg["key"]]["students"].append({
            "id": s["id"],
            "roll_number": s["roll_number"],
            "full_name": s["full_name"],
            "branch": s["branch"],
            "cgpa": s["cgpa"],
            "overall_score": score["overall_score"]
        })

    result = {}
    for k, info in SEGMENT_DEFINITIONS.items():
        count = breakdown[k]["count"]
        pct = round((count / total) * 100.0, 1) if total > 0 else 0.0
        result[k] = {
            "key": k,
            "title": info["title"],
            "count": count,
            "percentage": pct,
            "color": info["color"],
            "badge_class": info["badge_class"],
            "description": info["description"],
            "students": breakdown[k]["students"]
        }

    return result
