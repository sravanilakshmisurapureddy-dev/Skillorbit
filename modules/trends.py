"""
Campus2Career AI - Trends & Analytics Engine
Member 2: Analytics & AI Logic Lead
Computes cohort-level trends, branch comparisons, skill distributions, and top-N student rankings.
"""

from collections import Counter
from modules.success_score import calculate_student_success_score, _parse_list
from modules.risk_flags import evaluate_student_risk_flags


def calculate_cohort_trends(students_list):
    """
    Analyzes student cohort to extract key institutional trends:
    - Average success score & CGPA
    - Branch-wise performance comparison
    - Top in-demand skills in cohort
    - Risk flag distribution
    - Placement eligibility distribution
    """
    if not students_list:
        return {
            "total_students": 0,
            "avg_score": 0,
            "avg_cgpa": 0,
            "branch_trends": [],
            "top_skills": [],
            "top_languages": [],
            "risk_distribution": {},
            "readiness_tiers": {}
        }

    total = len(students_list)
    scores = []
    cgpas = []
    branch_map = {}
    all_skills = []
    all_langs = []
    risk_counter = Counter()
    tier_counter = Counter()

    for s in students_list:
        score_data = calculate_student_success_score(s)
        score = score_data["overall_score"]
        cgpa = float(s.get("cgpa", 0.0) or 0.0)
        branch = s.get("branch", "Other")

        scores.append(score)
        cgpas.append(cgpa)

        # Branch grouping
        if branch not in branch_map:
            branch_map[branch] = {"scores": [], "cgpas": [], "count": 0}
        branch_map[branch]["scores"].append(score)
        branch_map[branch]["cgpas"].append(cgpa)
        branch_map[branch]["count"] += 1

        # Skills & Languages
        langs = _parse_list(s.get("programming_languages", ""))
        skills = _parse_list(s.get("technical_skills", ""))
        all_langs.extend(langs)
        all_skills.extend(skills)

        # Risk Flags
        flags = evaluate_student_risk_flags(s, score_data)
        for f in flags:
            risk_counter[f["code"]] += 1

        # Tiers
        tier_counter[score_data["grade"].split()[0]] += 1

    # Branch trends list
    branch_trends = []
    for b_name, b_data in branch_map.items():
        branch_trends.append({
            "branch": b_name,
            "student_count": b_data["count"],
            "avg_score": round(sum(b_data["scores"]) / len(b_data["scores"]), 1),
            "avg_cgpa": round(sum(b_data["cgpas"]) / len(b_data["cgpas"]), 2),
            "max_score": round(max(b_data["scores"]), 1)
        })
    branch_trends.sort(key=lambda x: x["avg_score"], reverse=True)

    # Top skills
    top_skills = [{"name": skill, "count": cnt} for skill, cnt in Counter(all_skills).most_common(8)]
    top_languages = [{"name": lang, "count": cnt} for lang, cnt in Counter(all_langs).most_common(6)]

    return {
        "total_students": total,
        "avg_score": round(sum(scores) / total, 1),
        "avg_cgpa": round(sum(cgpas) / total, 2),
        "max_score": round(max(scores), 1),
        "min_score": round(min(scores), 1),
        "branch_trends": branch_trends,
        "top_skills": top_skills,
        "top_languages": top_languages,
        "risk_distribution": dict(risk_counter),
        "tier_distribution": dict(tier_counter)
    }


def get_top_n_students(students_list, n=10, branch=None, min_cgpa=0.0, required_skill=None):
    """
    Configurable Top-N selection engine for placement drives and shortlist nominations.
    """
    enriched = []
    for s in students_list:
        score_data = calculate_student_success_score(s)
        cgpa = float(s.get("cgpa", 0.0) or 0.0)

        # Filters
        if branch and branch != "All" and s.get("branch") != branch:
            continue
        if cgpa < min_cgpa:
            continue
        if required_skill:
            skills = _parse_list(s.get("technical_skills", "")) + _parse_list(s.get("programming_languages", ""))
            if not any(required_skill.lower() in sk.lower() for sk in skills):
                continue

        enriched.append({
            "student": s,
            "score_data": score_data,
            "score": score_data["overall_score"]
        })

    enriched.sort(key=lambda x: x["score"], reverse=True)
    return enriched[:n]
