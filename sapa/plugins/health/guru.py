"""Health Bot personality and teaching module."""

from datetime import datetime
from typing import Optional

from .api_client import get_client
from ...config import get_config


GURU_SYSTEM_PROMPT = """You are an Health Bot - a serial builder and product shipper who has launched multiple successful products and now mentors developers who want to build and ship faster.

Your personality:
- Bias toward action - ship first, iterate later
- Practical and no-nonsense, cut through the hype
- Honest about what AI tools actually work vs what's vaporware
- Encouraging but pushes for execution over planning
- Celebrates shipping, not just learning

Your expertise:
- Using AI tools (Claude, ChatGPT, Cursor, v0, Bolt, Replit Agent, etc.) to build faster
- Rapid prototyping and MVP development
- Finding and validating product ideas
- Self-promotion, personal branding, and job hunting in tech
- Staying on the bleeding edge without getting distracted by hype

Your teaching style:
- Focus on what you can build TODAY, not theoretical knowledge
- Give specific tool recommendations with real workflows
- Share tactics for standing out in the job market
- Call out when something is overhyped vs actually useful
- Always connect learning to shipping something tangible

Context about the learner:
- Name: {user_name}
- They are a developer/builder who wants to USE AI tools to ship products
- They are NOT a data scientist or ML engineer
- They want to stay current on AI tools and land their next tech job

Keep advice practical and actionable. No fluff. Ship it."""


class MedBot:
    def __init__(self):
        self.config = get_config()
        self.client = get_client()
        self.conversation_history: list[dict] = []

    def _get_system_prompt(self) -> str:
        return GURU_SYSTEM_PROMPT.format(user_name=self.config.user_name)

    def _get_greeting(self) -> str:
        hour = datetime.now().hour
        if hour < 12:
            return "Good morning"
        elif hour < 17:
            return "Good afternoon"
        else:
            return "Good evening"

    def _chat(self, user_message: str, keep_history: bool = True) -> str:
        if keep_history:
            self.conversation_history.append({"role": "user", "content": user_message})
            messages = self.conversation_history.copy()
        else:
            messages = [{"role": "user", "content": user_message}]

        response = self.client.chat(messages=messages, system=self._get_system_prompt(), temperature=0.7)

        if keep_history:
            self.conversation_history.append({"role": "assistant", "content": response})

        return response

    def clear_history(self) -> None:
        self.conversation_history = []

    def ask_anything(self, question: str) -> str:
        return self._chat(question)

    def deep_dive(self, topic: str, duration_minutes: int = 15) -> str:
        prompt = f"""I want to learn about: {topic}

Give me a {duration_minutes}-minute practical deep dive:

1. **What it is** - Cut through the marketing, what does it actually do?
2. **Is it real or hype?** - Honest assessment, does it actually work well today?
3. **How to use it** - Practical workflow, how would I actually use this to build/ship faster?
4. **Hands-on example** - Show me exactly how to try it right now
5. **Job market angle** - Is this worth putting on my resume? How do I talk about it?
6. **Verdict** - Should I invest time learning this or skip it?

Be honest. If something is overhyped, say so. I want to know what actually helps me ship."""

        return self._chat(prompt)
