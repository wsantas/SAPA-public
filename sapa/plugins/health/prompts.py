"""Prompt templates for Health Bot."""

from datetime import datetime
from ...config import get_config


def get_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"


SYSTEM_CONTEXT = """You are an Health Bot - a serial builder and product shipper who mentors developers who want to build and ship faster using AI tools.

Your style:
- Bias toward action - ship first, iterate later
- Practical and no-nonsense, cut through the hype
- Honest about what AI tools actually work vs what's vaporware
- Focus on what you can build TODAY

The user is a developer who wants to USE AI tools to ship products. They are NOT a data scientist."""


def daily_briefing_prompt(recent_topics: list[str] = None, knowledge_gaps: list[str] = None) -> str:
    config = get_config()
    greeting = get_greeting()
    today = datetime.now().strftime("%Y-%m-%d")

    context_section = ""
    if recent_topics or knowledge_gaps:
        context_section = "\n\n**My Learning Context:**\n"
        if recent_topics:
            context_section += f"- Recently learned: {', '.join(recent_topics[:5])}\n"
        if knowledge_gaps:
            context_section += f"- Need to review: {', '.join(knowledge_gaps[:3])}\n"
        context_section += "\nBuild on what I've been learning, and suggest what I should learn next.\n"

    return f"""{SYSTEM_CONTEXT}

{greeting}! Create a daily AI builder briefing for {config.user_name} on {today}.
{context_section}
Search for and include:
1. **Top AI Tool News** - New releases, updates to Cursor/Copilot/Claude/ChatGPT/v0/Bolt/Replit, etc.
2. **Product Launches** - AI startups or tools that launched recently
3. **Job Market Pulse** - Any notable hiring/layoff news in tech
4. **Tool of the Day** - One specific tool or technique to try today

For each news item, explain WHY it matters for someone who builds products.

End with:
- **Today's Challenge** - One actionable thing I could do today
- **Job Hunting Tip** - One tip for self-promotion
- **Suggested Next Topics** - Based on what I've been learning, what 2-3 topics should I deep dive into next?

Keep it punchy. No fluff. What actually matters for shipping products?"""


def extract_topics_prompt(content: str) -> str:
    return f"""Analyze this content and extract the key topics, tools, and concepts mentioned.

Content:
---
{content[:3000]}
---

Return ONLY a simple list of topics/tools/concepts, one per line.
Focus on:
- AI tools mentioned (Claude, Cursor, v0, etc.)
- Technologies and frameworks
- Concepts and techniques
- Skills worth learning

Keep each topic short (1-3 words). Return 5-10 topics max. Just the list, no explanation."""
