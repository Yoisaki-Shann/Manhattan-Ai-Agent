import re

import api.apiwarpper as api
import db.database as db
from tools import stats

# Get the circle id
def _circle_id(ctx, circle_id=None):
    if circle_id:                                   # 1. named in the question
        return circle_id
    user = db.get_user(ctx["discord_id"])
    if user:                                        # 2. the asker's own circle
        cid = _users_circle(user["viewer_id"])
        if cid:
            return cid
    cid = db.get_guild_circle(ctx.get("guild_id"))  # 3. server default
    if not cid:
        raise ValueError("I don't know which circle. Run !link <viewer_id>, "
                         "or ask an admin to run !setcircle <circle_id>.")
    return cid

# Get the linked viewer id
def _linked_viewer(ctx):
    user = db.get_user(ctx["discord_id"])
    if not user:
        raise ValueError("This Discord account isn't linked. Run: Contact an admin to link your viewer ID .")
    return user["viewer_id"]

# Resolve viewer_id from target (viewer_id, trainer name, @mention, or asking user)
def _resolve_viewer_id(ctx, target=None):
    """Resolve viewer_id from target (viewer_id, trainer name, @mention, or asking user)."""
    if not target:
        return _linked_viewer(ctx)

    s = str(target).strip()
    s_lower = s.lower()
    self_placeholders = {
        "me", "my", "myself", "none", "null",
        "viewer_id", "user", "self", "current_user", "asking_user", "author", "player"
    }
    if s_lower in {"him", "her", "his", "their", "them"}:
        raise ValueError(
            f"I can't tell who '{s}' refers to. Use the player's trainer name or viewer ID."
        )
    if s_lower in self_placeholders or (s.startswith("<") and s.endswith(">") and not re.search(r"\d", s)):
        return _linked_viewer(ctx)

    cleaned = re.sub(r"[<@!>]", "", s)
    if cleaned.isdigit():
        user = db.get_user(int(cleaned))
        if user:
            return user["viewer_id"]
        if len(cleaned) >= 9:
            return cleaned

    # Search by trainer_name in circle members
    try:
        cid = _circle_id(ctx)
        circle_data = api.get_circle(cid)
        members = circle_data.get("members", [])
        for m in members:
            if m.get("trainer_name", "").lower() == s.lower():
                return str(m["viewer_id"])
        for m in members:
            if s.lower() in m.get("trainer_name", "").lower():
                return str(m["viewer_id"])
    except Exception:
        pass

    if cleaned.isdigit():
        return cleaned

    raise ValueError(f"Could not find a player named '{target}' in the circle.")


# Get the circle leaderboard
def get_circle_leaderboard(ctx, days: int = 7, limit: int = 10, circle_id: str = None):
    data = api.get_circle(_circle_id(ctx, circle_id))
    return {"circle": data["circle"]["name"], **stats.leaderboard(data, days, limit)}


def get_circle_info(ctx, circle_id: str = None):
    data = api.get_circle(_circle_id(ctx, circle_id))
    c = data["circle"]
    return {
        "name": c["name"], "member_count": c["member_count"],
        "club_rank": data.get("club_rank"),
        "monthly_point": c["monthly_point"], "monthly_rank": c["monthly_rank"],
        "live_points": c["live_points"], "live_rank": c["live_rank"],
        "fans_to_next_tier": data.get("fans_to_next_tier"),
        "fans_to_lower_tier": data.get("fans_to_lower_tier"),
        "data_last_updated": c.get("last_updated"),
    }

# Get the circle the user is in
def _users_circle(viewer_id):
    """The circle the player is really in, or None (also None if their data is stale)."""
    try:
        profile = api.get_user(viewer_id)
        circle_id = (profile.get("circle") or {}).get("circle_id")
        if not circle_id:
            return None
        circle = api.get_circle(circle_id)
        return circle_id if stats.find_member(circle, viewer_id) else None
    except Exception:
        return None
# Get the asking user's fans today
def get_my_fans_today(ctx):
    viewer_id = _linked_viewer(ctx)
    circle_id = _users_circle(viewer_id)
    if not circle_id:
        return {"error": "You don't seem to be in a circle right now, "
                         "or your data is out of date."}
    circle = api.get_circle(circle_id)
    member = stats.find_member(circle, viewer_id)
    gain = stats.fans_today(member)
    return {
        "trainer_name": member["trainer_name"],
        "fans_today": gain,
        "note": None if gain is not None else "No usable data for today yet.",
        "data_last_updated": circle["circle"].get("last_updated"),
    }

# Get a player's fan summary, all-time and monthly stats
def get_player_summary(ctx, player: str = None, viewer_id: str = None):
    target = player or viewer_id
    resolved_id = _resolve_viewer_id(ctx, target)
    p = api.get_user(resolved_id)
    history = p.get("fan_history") or {}
    rolling = history.get("rolling")
    monthly = history.get("monthly") or []
    alltime = history.get("alltime") or {}
    latest_month = monthly[0] if monthly else {}
    return {
        "trainer_name": (p.get("trainer") or {}).get("name"),
        "viewer_id": str(resolved_id),
        "circle": (p.get("circle") or {}).get("name"),
        "alltime": {
            "active_days": alltime.get("active_days"),
            "total_fans": alltime.get("total_fans"),
            "total_gain": alltime.get("total_gain"),
            "avg_day": alltime.get("avg_day"),
            "rank": alltime.get("rank"),
        } if alltime else None,
        "monthly": {
            "year": latest_month.get("year"),
            "month": latest_month.get("month"),
            "active_days": latest_month.get("active_days"),
            "monthly_gain": latest_month.get("monthly_gain"),
            "total_fans": latest_month.get("total_fans"),
            "rank": latest_month.get("rank"),
        } if latest_month else None,
        "rolling": rolling,
        "note": None if (alltime or rolling) else "No activity data found for this player.",
    }


HANDLERS = {
    "get_circle_leaderboard": get_circle_leaderboard,
    "get_circle_info": get_circle_info,
    "get_my_fans_today": get_my_fans_today,
    "get_player_summary": get_player_summary,
}

# Create a tool definition
def _tool(name, description, props=None, required=None):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": props or {}, "required": required or []}}}


TOOLS = [
    _tool("get_circle_leaderboard",
          "Top players in the circle ranked by fan gain over the last N days "
          "(7 = this week, 1 = today). Uses the server's default circle unless circle_id is given.",
          {"days": {"type": "integer", "description": "Period in days, default 7"},
           "limit": {"type": "integer", "description": "How many players, default 10"},
           "circle_id": {"type": "string", "description": "Optional; omit for the default circle"}}),
    _tool("get_circle_info",
          "Circle overview: name, member count, rank, points, and fans needed for the next tier.",
          {"circle_id": {"type": "string", "description": "Optional"}}),
    _tool("get_my_fans_today",
          "Use only to find how many fans the asking user earned today. Do not use for profile questions, total fans, or all-time stats."),
    _tool("get_player_summary",
          "Use for player profile questions, all-time active days, total fans, total gain, average daily gain, all-time rank, recent 3/7/30-day gains, or monthly stats. This is the correct tool for 'my profile total fans'. Accepts a trainer name or viewer ID. Omit player only when the user explicitly asks about their own stats.",
          {"player": {"type": "string", "description": "Trainer name or viewer ID; omit only for an explicit question about the asking user's own stats"}}),
]

# Run a tool by name with arguments and context, returning the result or an error message
def run_tool(name: str, args: dict, ctx: dict):
    fn = HANDLERS.get(name)
    if fn is None:
        return {"error": f"unknown tool {name}"}
    try:
        return fn(ctx, **(args or {}))
    except TypeError as e:
        return {"error": f"bad arguments: {e}"}
    except Exception as e:  # report to the model instead of crashing the bot
        return {"error": str(e)}
