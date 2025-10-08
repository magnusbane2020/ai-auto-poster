def enforce_platform_rules(text: str, platform: str) -> str:
    # Keep it simple: tighten length & remove multiple links
    max_len = 1200 if platform == "linkedin" else 2000
    t = text.strip()
    if len(t) > max_len:
        t = t[:max_len-3] + "..."
    # example link policy: max 1 link
    parts = t.split("http")
    if len(parts) > 2:
        t = "http".join(parts[:2])  # keep first link only
    return t
