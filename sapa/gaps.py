"""Shared gap analysis: computation and JS generator.

Both health and homestead plugins use identical gap analysis logic.
This module provides everything they need — plugins just supply data.

Uses DFWM (Decayed Frequency-Weighted Mastery) to compute per-topic
mastery scores based on the Ebbinghaus forgetting curve and
depth-weighted confidence growth.
"""

import json
import math
from datetime import datetime
from pathlib import Path

_STATIC_DIR = Path(__file__).parent / "static"

MASTERY_THRESHOLD = 30


def compute_mastery(topic_row: dict, now: datetime | None = None) -> int:
    """Compute current mastery % for a topic using DFWM.

    mastery = confidence * retrievability * 100
    where retrievability = e^(-days_since_review / stability)
    and stability = 3.0 * (1 + review_count)^1.5
    """
    if now is None:
        now = datetime.now()
    confidence = topic_row.get("confidence_score", 0)
    review_count = topic_row.get("review_count", 0)
    last_reviewed = topic_row.get("last_reviewed")

    if not last_reviewed or confidence <= 0:
        return 0

    if isinstance(last_reviewed, str):
        try:
            last_reviewed = datetime.fromisoformat(last_reviewed)
        except (ValueError, TypeError):
            return 0

    days_since = max((now - last_reviewed).total_seconds() / 86400, 0)
    stability = 3.0 * (1 + review_count) ** 1.5
    retrievability = math.exp(-days_since / stability)
    return round(confidence * retrievability * 100)


def compute_gap_analysis(topic_rows: list[dict], gap_targets: dict) -> dict:
    """Compute gap analysis using mastery-weighted scoring.

    Args:
        topic_rows: List of topic dicts with name, confidence_score,
                    review_count, last_reviewed.
        gap_targets: Dict of category_name -> {"topics": [...], "priority": str}.

    Returns:
        {"categories": [...], "summary": {...}, "top_gaps": [...]}
    """
    if not gap_targets:
        return {
            "categories": [],
            "summary": {
                "overall_coverage": 0,
                "total_topics": 0,
                "topics_covered": 0,
                "topics_remaining": 0,
            },
            "top_gaps": [],
        }

    now = datetime.now()

    # Build lookup: topic_name_lower -> mastery %
    mastery_lookup: dict[str, int] = {}
    for row in topic_rows:
        name = row["name"].lower()
        m = compute_mastery(row, now)
        if name not in mastery_lookup or m > mastery_lookup[name]:
            mastery_lookup[name] = m

    categories = []
    total_mastery_sum = 0
    total_target = 0

    for category_name, category_data in gap_targets.items():
        target_topics = category_data["topics"]
        priority = category_data["priority"]

        covered = []
        gaps = []
        category_mastery_sum = 0

        for topic in target_topics:
            topic_lower = topic.lower()
            mastery = 0
            for learned_name, learned_mastery in mastery_lookup.items():
                if topic_lower in learned_name or learned_name in topic_lower:
                    mastery = max(mastery, learned_mastery)

            if mastery >= MASTERY_THRESHOLD:
                covered.append({"name": topic, "mastery": mastery})
            else:
                gaps.append({"name": topic, "mastery": mastery})
            category_mastery_sum += mastery

        avg_mastery = round(category_mastery_sum / len(target_topics)) if target_topics else 0

        categories.append({
            "name": category_name,
            "priority": priority,
            "coverage": avg_mastery,
            "covered": covered,
            "gaps": gaps,
            "total": len(target_topics),
        })

        total_mastery_sum += category_mastery_sum
        total_target += len(target_topics)

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    categories.sort(key=lambda x: (priority_order.get(x["priority"], 99), x["coverage"]))

    overall_coverage = round(total_mastery_sum / total_target) if total_target else 0

    top_gaps = []
    for cat in categories:
        if cat["priority"] in ["critical", "high"]:
            for gap in cat["gaps"][:3]:
                top_gaps.append({
                    "topic": gap["name"],
                    "category": cat["name"],
                    "priority": cat["priority"],
                })

    priority_weight = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    suggestions = []
    for cat in categories:
        if not cat["gaps"]:
            continue
        weight = priority_weight.get(cat["priority"], 1)
        score = weight * (100 - cat["coverage"]) * len(cat["gaps"])
        for gap in cat["gaps"][:2]:
            suggestions.append({
                "topic": gap["name"],
                "category": cat["name"],
                "priority": cat["priority"],
                "score": round(score, 1),
            })
    suggestions.sort(key=lambda s: s["score"], reverse=True)

    topics_above_threshold = sum(
        1 for cat in categories for t in cat["covered"]
    )

    return {
        "categories": categories,
        "summary": {
            "overall_coverage": overall_coverage,
            "total_topics": total_target,
            "topics_covered": topics_above_threshold,
            "topics_remaining": total_target - topics_above_threshold,
        },
        "top_gaps": top_gaps[:10],
        "suggestions": suggestions[:5],
    }


def generate_gap_js(
    plugin_id: str,
    summary_el: str,
    top_gaps_el: str,
    categories_el: str,
    prompts: dict[str, str],
    default_prompt: str,
) -> str:
    """Generate namespaced gap analysis JS for a plugin."""
    plugin_var = plugin_id[0].lower() + plugin_id[1:]

    js = (_STATIC_DIR / "gap-template.js").read_text()
    js = js.replace("$PLUGIN_ID$", plugin_id)
    js = js.replace("$PLUGIN_VAR$", plugin_var)
    js = js.replace("$SUMMARY_EL$", summary_el)
    js = js.replace("$TOP_GAPS_EL$", top_gaps_el)
    js = js.replace("$CATEGORIES_EL$", categories_el)
    js = js.replace("$PROMPTS_JSON$", json.dumps(prompts))
    js = js.replace("$DEFAULT_PROMPT_JSON$", json.dumps(default_prompt))
    return js
