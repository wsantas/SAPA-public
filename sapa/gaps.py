"""Shared gap analysis: computation and JS generator.

Both health and homestead plugins use identical gap analysis logic.
This module provides everything they need — plugins just supply data.
"""

import json
from pathlib import Path

_STATIC_DIR = Path(__file__).parent / "static"


def compute_gap_analysis(learned_topics: set[str], gap_targets: dict) -> dict:
    """Compute gap analysis from learned topics and target definitions.

    Args:
        learned_topics: Set of lowercase topic name strings.
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

    categories = []
    total_target = 0
    total_covered = 0

    for category_name, category_data in gap_targets.items():
        target_topics = category_data["topics"]
        priority = category_data["priority"]

        covered = []
        gaps = []

        for topic in target_topics:
            topic_lower = topic.lower()
            is_covered = any(
                topic_lower in learned or learned in topic_lower
                for learned in learned_topics
            )
            if is_covered:
                covered.append(topic)
            else:
                gaps.append(topic)

        coverage_pct = (len(covered) / len(target_topics) * 100) if target_topics else 0

        categories.append({
            "name": category_name,
            "priority": priority,
            "coverage": round(coverage_pct),
            "covered": covered,
            "gaps": gaps,
            "total": len(target_topics),
        })

        total_target += len(target_topics)
        total_covered += len(covered)

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    categories.sort(key=lambda x: (priority_order.get(x["priority"], 99), x["coverage"]))

    overall_coverage = (total_covered / total_target * 100) if total_target else 0

    top_gaps = []
    for cat in categories:
        if cat["priority"] in ["critical", "high"]:
            for gap in cat["gaps"][:3]:
                top_gaps.append({"topic": gap, "category": cat["name"], "priority": cat["priority"]})

    # Ranked suggestions: priority weight * (100 - coverage%) * gap count
    priority_weight = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    suggestions = []
    for cat in categories:
        if not cat["gaps"]:
            continue
        weight = priority_weight.get(cat["priority"], 1)
        score = weight * (100 - cat["coverage"]) * len(cat["gaps"])
        for gap in cat["gaps"][:2]:
            suggestions.append({
                "topic": gap,
                "category": cat["name"],
                "priority": cat["priority"],
                "score": round(score, 1),
            })
    suggestions.sort(key=lambda s: s["score"], reverse=True)

    return {
        "categories": categories,
        "summary": {
            "overall_coverage": round(overall_coverage),
            "total_topics": total_target,
            "topics_covered": total_covered,
            "topics_remaining": total_target - total_covered,
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
    """Generate namespaced gap analysis JS for a plugin.

    Args:
        plugin_id: PascalCase plugin name, e.g. "Health" or "Homestead".
        summary_el: DOM element id for summary container.
        top_gaps_el: DOM element id for top gaps container.
        categories_el: DOM element id for categories container.
        prompts: Dict of lowercase topic -> prompt string.
        default_prompt: Template string with $TOPIC$ and $CATEGORY$ placeholders.

    Returns:
        JavaScript string with all gap rendering functions.
    """
    # Build a lowercase variable prefix from plugin_id
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
