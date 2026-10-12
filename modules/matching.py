"""
Campus2Career AI - Talent Matching Engine
Member 4: Recruitment Engineer
Matches candidates to corporate opportunity requirements and computes explainable match percentages.
"""

from modules.success_score import calculate_student_success_score, _parse_list


def compute_student_opportunity_match(student_dict, opportunity_dict):
    """
    Computes an explainable candidate-to-opportunity match score (0-100%).
    Factors:
    - Skill Match (50% weight): Required skills vs student's languages, tools, and certifications
    - Academic Cutoff (25% weight): CGPA vs min_cgpa
    - Branch Alignment (15% weight): Student branch vs eligible branches
    - Practical Experience Bonus (10% weight): Relevant internship
    
    Returns structured result with match percentage, breakdown, matched/missing skills, and narrative explanation.
    """
    # 1. Parse Required Skills
    req_skills_raw = _parse_list(opportunity_dict.get("required_skills", ""))
    student_all_skills = (
        _parse_list(student_dict.get("programming_languages", "")) +
        _parse_list(student_dict.get("technical_skills", "")) +
        _parse_list(student_dict.get("certifications", ""))
    )
    student_skills_lower = [s.lower() for s in student_all_skills]

    matched_skills = []
    missing_skills = []

    for req in req_skills_raw:
        req_clean = req.strip()
        req_lower = req_clean.lower()
        # Direct or substring match
        if any(req_lower in s or s in req_lower for s in student_skills_lower):
            matched_skills.append(req_clean)
        else:
            missing_skills.append(req_clean)

    total_req = max(1, len(req_skills_raw))
    skill_ratio = len(matched_skills) / total_req
    skill_score = skill_ratio * 50.0

    # 2. Academic Cutoff
    min_cgpa = float(opportunity_dict.get("min_cgpa", 0.0) or 0.0)
    student_cgpa = float(student_dict.get("cgpa", 0.0) or 0.0)
    cgpa_eligible = student_cgpa >= min_cgpa

    if min_cgpa <= 0:
        academic_score = 25.0
    elif student_cgpa >= min_cgpa:
        # Give full 25 plus bonus scaling if student significantly exceeds cutoff
        surplus = min(1.0, (student_cgpa - min_cgpa) / 2.0)
        academic_score = 20.0 + (surplus * 5.0)
    else:
        # Partial credit if slightly below, but flagged
        academic_score = max(0.0, (student_cgpa / min_cgpa) * 15.0)

    # 3. Branch Alignment
    eligible_branches_str = str(opportunity_dict.get("eligible_branches", "All")).strip()
    student_branch = str(student_dict.get("branch", "")).strip()

    if eligible_branches_str.lower() in ["all", "any", "all branches", ""]:
        branch_eligible = True
        branch_score = 15.0
    else:
        eligible_branches = [b.strip().lower() for b in eligible_branches_str.split(",")]
        branch_eligible = any(eb in student_branch.lower() or student_branch.lower() in eb for eb in eligible_branches)
        branch_score = 15.0 if branch_eligible else 5.0

    # 4. Practical Experience Bonus
    internship = str(student_dict.get("internship_details", "")).strip()
    has_internship = bool(internship and internship.lower() not in ["none", "none recorded", "n/a", ""])
    practical_bonus = 10.0 if has_internship else 2.0

    # Total Match Percentage
    total_match = round(min(100.0, max(0.0, skill_score + academic_score + branch_score + practical_bonus)), 1)

    # Overall Eligibility Status
    is_fully_eligible = cgpa_eligible and branch_eligible

    # Narrative explanation
    explanation_parts = []
    if len(matched_skills) > 0:
        explanation_parts.append(f"Matches {len(matched_skills)}/{len(req_skills_raw)} required skills ({', '.join(matched_skills[:3])}).")
    if missing_skills:
        explanation_parts.append(f"Missing skills: {', '.join(missing_skills[:3])}.")
    if cgpa_eligible:
        explanation_parts.append(f"Exceeds CGPA threshold ({student_cgpa:.2f} >= {min_cgpa:.2f}).")
    else:
        explanation_parts.append(f"Below CGPA requirement ({student_cgpa:.2f} < {min_cgpa:.2f}).")

    if branch_eligible:
        explanation_parts.append(f"Branch '{student_branch}' is eligible.")
    else:
        explanation_parts.append(f"Branch '{student_branch}' not in listed preference.")

    return {
        "match_percentage": total_match,
        "is_eligible": is_fully_eligible,
        "cgpa_eligible": cgpa_eligible,
        "branch_eligible": branch_eligible,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "explanation": " ".join(explanation_parts),
        "breakdown": {
            "skills": round(skill_score, 1),
            "academic": round(academic_score, 1),
            "branch": round(branch_score, 1),
            "experience": round(practical_bonus, 1)
        }
    }


def rank_candidates_for_opportunity(students_list, opportunity_dict):
    """
    Ranks all students against an opportunity by match percentage descending.
    """
    ranked = []
    for s in students_list:
        # Check consent status - respect student profile visibility and consent!
        if int(s.get("consent_status", 1)) != 1 or s.get("placement_status") == "Opted Out":
            continue

        match_info = compute_student_opportunity_match(s, opportunity_dict)
        score_data = calculate_student_success_score(s)

        ranked.append({
            "student": s,
            "match_info": match_info,
            "match_percentage": match_info["match_percentage"],
            "is_eligible": match_info["is_eligible"],
            "success_score": score_data["overall_score"]
        })

    # Sort primarily by match_percentage, then by success_score
    ranked.sort(key=lambda x: (x["match_percentage"], x["success_score"]), reverse=True)
    return ranked
