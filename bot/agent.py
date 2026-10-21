"""The LLM loop: question -> tool calls -> answer. Talks to LM Studio (OpenAI-style API)."""
import json
import re

from openai import OpenAI

import config
from tools.registry import TOOLS, run_tool

client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)

# System prompt for the LLM
SYSTEM = (
    "You are Manhattan, a friendly Discord bot for an Uma Musume circle. "
    "Answer questions about fan counts, leaderboards, circle stats, player profiles, and active days using the tools. "
    "For profile questions, all-time active days, or total fans, use get_player_summary. "
    "Use get_my_fans_today only when asked specifically about fans earned today; it cannot answer profile or all-time total questions. "
    "Users may begin a message with 'Manhattan' to address you; that is your bot name, not a player's name. "
    "When a user asks about 'my' or 'me', call the player statistics tool without a player argument. "
    "For follow-up questions, use the recent conversation to identify who pronouns refer to and pass that player's name to the tool. "
    "Never treat a third-person pronoun as the asking user. If the person cannot be identified from context, ask who the user means instead of guessing. "
    "Never invent numbers; if a tool returns an error, explain it simply. "
    "Format numbers readably (e.g. 39.4M, 114 days) and leaderboards as short numbered lists. "
    "Use natural, conversational phrasing; avoid referring to someone as 'the asking user'. Include the player's name when known. "
    "Mention when the data was last updated if it is relevant. Keep answers brief."
)

_CHANNEL_HISTORIES: dict[tuple[int | str, int | str], list[dict]] = {}
MAX_HISTORY = 6  # Keep last 6 messages (3 Q&A pairs) per channel for conversational context

# remove <think>...</think> blocks from the LLM output
def _clean(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


def _correct_self_profile_target(question: str, tool_name: str, args: dict) -> dict:
    player = args.get("player")
    asks_for_own_stats = re.search(
        r"\bmy\b.{0,40}\b(profile|stats?|fans?|active days)\b",
        question,
        flags=re.I,
    )
    if (
        tool_name == "get_player_summary"
        and isinstance(player, str)
        and player.casefold() == "manhattan"
        and asks_for_own_stats
    ):
        args = {**args, "player": None}
    return args

# Ask the LLM a question and return the answer
def ask(question: str, ctx: dict, max_steps: int = 5) -> str:
    channel_key = (
        ctx.get("channel_id") or "default",
        ctx.get("discord_id") or "default",
    )
    history = _CHANNEL_HISTORIES.get(channel_key, [])

    messages = [
        {"role": "system", "content": SYSTEM},
        *history,
        {"role": "user", "content": f"{question} /no_think"},  # turns off Qwen3 thinking
    ]
    for _ in range(max_steps):
        resp = client.chat.completions.create(
            model=config.LLM_MODEL, messages=messages, tools=TOOLS, temperature=0.2)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            answer = _clean(msg.content) or "Sorry, I don't have an answer for that."
            new_history = history + [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ]
            _CHANNEL_HISTORIES[channel_key] = new_history[-MAX_HISTORY:]
            return answer
        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            args = _correct_self_profile_target(question, call.function.name, args)
            result = run_tool(call.function.name, args, ctx)
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(result, ensure_ascii=False)})
    return "Sorry, I got stuck working that out. Try asking another way."
