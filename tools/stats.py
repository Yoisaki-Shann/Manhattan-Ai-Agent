"""
daily_fans is a list of cumulative fan totals, one slot per day, with 0 for
days that have no data yet. We therefore never trust slot positions as
calendar days; we work from the last non-zero slot instead.
"""

# Get the filled indices of the daily fans list
def _filled(member) -> list[int]:
    return [i for i, v in enumerate(member["daily_fans"]) if v]

# Find a member in the circle data
def find_member(circle_data: dict, viewer_id):
    for m in circle_data["members"]:
        if str(m["viewer_id"]) == str(viewer_id):
            return m
    return None

# Get the fan gain over a period of days
def gain_over_days(member, days: int):
    """Fan gain over the last `days` days of available data, or None."""
    d, nz = member["daily_fans"], _filled(member)
    if len(nz) < 2:
        return None
    last = nz[-1]
    start = max(nz[0], last - days)
    return {"gain": d[last] - d[start], "days_covered": last - start}


# Get the fans today
def fans_today(member):
    """Latest day's gain (as of the last data update), or None."""
    d, nz = member["daily_fans"], _filled(member)
    if len(nz) < 2:
        return None
    last = nz[-1]
    if d[last - 1] == 0:
        return None
    return d[last] - d[last - 1]


# Get the leaderboard
def leaderboard(circle_data: dict, days: int = 7, limit: int = 10) -> dict:
    rows, skipped = [], 0
    for m in circle_data["members"]:
        g = gain_over_days(m, days)
        if g is None:
            skipped += 1
            continue
        rows.append({
            "trainer_name": m["trainer_name"],
            "viewer_id": str(m["viewer_id"]),
            "gain": g["gain"],
            "days_covered": g["days_covered"],
            "daily_avg": round(g["gain"] / g["days_covered"]) if g["days_covered"] else 0,
        })
    rows.sort(key=lambda r: r["gain"], reverse=True)
    for i, r in enumerate(rows[:limit], 1):
        r["rank"] = i
    return {
        "period_days": days,
        "players": rows[:limit],
        "members_skipped_not_enough_data": skipped,
        "data_last_updated": circle_data["circle"].get("last_updated"),
    }
