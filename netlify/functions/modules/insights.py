"""
Campus2Career AI - Student Insights & Recommendations Engine
Member 2: Analytics & AI Logic Lead
Generates explainable, evidence-based recommendations and personalized career pathways.
"""

from modules.success_score import calculate_student_success_score, _parse_list
from modules.risk_flags import evaluate_student_risk_flags
from modules.segmentation import classify_student_segment


def generate_student_insights(student_dict):
    """
    Synthesizes score, risk flags, and profile attributes to produce
    actionable student insights and tailored recommendations.
    """
    score_data = calculate_student_success_score(student_dict)
    risk_flags = evaluate_student_risk_flags(student_dict, score_data)
    segment = classify_student_segment(student_dict, score_data)

    langs = _parse_list(student_dict.get("programming_languages", ""))
    skills = _parse_list(student_dict.get("technical_skills", ""))
    certs = _parse_list(student_dict.get("certifications", ""))
    internship = str(student_dict.get("internship_details", "")).strip()

    strengths = []
    growth_areas = []
    career_pathways = []
    action_items = []

    # Identify Key Strengths
    if float(student_dict.get("cgpa", 0)) >= 8.5:
        strengths.append("High academic distinction (CGPA >= 8.5) qualifies for Tier-1 engineering roles.")
    if len(certs) >= 1:
        strengths.append(f"Industry verified credentials: {', '.join(certs)}.")
    if internship and internship.lower() not in ["none", "none recorded", "n/a", ""]:
        strengths.append("Demonstrated industry exposure through verified internship engagement.")
    if any(k in [l.lower() for l in langs] for k in ["python", "c++", "go", "rust"]):
        strengths.append("Strong systems and analytical programming foundation.")
    if any(k in [s.lower() for s in skills] for k in ["docker", "kubernetes", "aws", "gcp", "azure"]):
        strengths.append("High-demand cloud infrastructure and containerization skills.")
    if any(k in [s.lower() for s in skills] for k in ["react", "next.js", "vue", "angular"]):
        strengths.append("Modern responsive web application frontend engineering capability.")

    if not strengths:
        strengths.append("Foundational academic enrollment ready for hands-on technical skill building.")

    # Identify Growth Areas
    for flag in risk_flags:
        growth_areas.append(flag["evidence"])
        action_items.append(flag["recommended_action"])

    if not growth_areas:
        growth_areas.append("Profile is well balanced across all four readiness pillars.")
        action_items.append("Prepare for system design interviews and participate in open-source hackathons.")

    # Recommended Career Pathways based on profile patterns
    all_text = (" ".join(langs) + " " + " ".join(skills) + " " + student_dict.get("branch", "")).lower()
    if "cloud" in all_text or "docker" in all_text or "aws" in all_text or "kubernetes" in all_text:
        career_pathways.append({
            "role": "Cloud DevOps & Infrastructure Engineer",
            "match_level": "High Match",
            "recommended_focus": "Deepen Terraform and CI/CD pipelines"
        })
    if "react" in all_text or "javascript" in all_text or "node" in all_text or "frontend" in all_text:
        career_pathways.append({
            "role": "Full Stack / Frontend Software Engineer",
            "match_level": "High Match",
            "recommended_focus": "Build end-to-end full stack web applications with authentication"
        })
    if "ai" in all_text or "pytorch" in all_text or "tensorflow" in all_text or "data" in all_text:
        career_pathways.append({
            "role": "AI / Machine Learning Engineer",
            "match_level": "High Match",
            "recommended_focus": "Deploy ML models behind FastAPI microservices with Docker"
        })
    if "embedded" in all_text or "verilog" in all_text or "matlab" in all_text or "iot" in all_text:
        career_pathways.append({
            "role": "Embedded Systems & IoT Engineer",
            "match_level": "High Match",
            "recommended_focus": "Focus on RTOS and hardware communication protocols (I2C, SPI, MQTT)"
        })

    # Default fallback pathway if none matched
    if not career_pathways:
        career_pathways.append({
            "role": "Graduate Systems Software Engineer",
            "match_level": "Recommended Foundation",
            "recommended_focus": "Master Data Structures & Algorithms and relational databases (SQL)"
        })

    return {
        "score_data": score_data,
        "segment": segment,
        "risk_flags": risk_flags,
        "strengths": strengths,
        "growth_areas": growth_areas,
        "career_pathways": career_pathways,
        "action_items": action_items
    }
