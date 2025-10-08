"""
cost.py - Cost calculation and budget enforcement.
Tracks OpenAI API usage costs per model.
Prevents runaway spending with daily/monthly limits.
"""
from datetime import datetime, timezone
from db import get_db, record_cost
from config import CFG

# Pricing as of 2025 (approximate, adjust as needed)
PRICING = {
    "gpt-4o-mini": {"input": 0.00015 / 1000, "output": 0.0006 / 1000},
    "gpt-4o": {"input": 0.0025 / 1000, "output": 0.01 / 1000},
    "dall-e-3": {"1024x1024": 0.040, "1792x1024": 0.080},
    "gpt-image-1": {"1024x1024": 0.040},  # assuming similar to DALL-E-3
}

def calculate_text_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for text completion models."""
    if model not in PRICING:
        return 0.0
    p = PRICING[model]
    return (input_tokens * p["input"]) + (output_tokens * p["output"])

def calculate_image_cost(model: str, size: str = "1024x1024") -> float:
    """Calculate cost for image generation."""
    if model not in PRICING:
        return 0.0
    return PRICING[model].get(size, 0.0)

def check_budget_limit(scope: str = "all") -> dict:
    """
    Check if we're within budget limits.
    Returns: {"ok": bool, "daily": float, "monthly": float, "reason": str}
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    month_start = datetime.now(timezone.utc).replace(day=1).strftime("%Y-%m-%d")
    
    with get_db() as db:
        # Daily total
        cur = db.execute("SELECT SUM(cost_usd) as total FROM costs WHERE date=?", (today,))
        daily_total = cur.fetchone()["total"] or 0.0
        
        # Monthly total
        cur = db.execute("SELECT SUM(cost_usd) as total FROM costs WHERE date>=?", (month_start,))
        monthly_total = cur.fetchone()["total"] or 0.0
    
    result = {
        "ok": True,
        "daily": daily_total,
        "monthly": monthly_total,
        "reason": ""
    }
    
    if daily_total >= CFG["DAILY_COST_LIMIT_USD"]:
        result["ok"] = False
        result["reason"] = f"Daily limit ${CFG['DAILY_COST_LIMIT_USD']} exceeded: ${daily_total:.4f}"
    elif monthly_total >= CFG["MONTHLY_COST_LIMIT_USD"]:
        result["ok"] = False
        result["reason"] = f"Monthly limit ${CFG['MONTHLY_COST_LIMIT_USD']} exceeded: ${monthly_total:.4f}"
    
    return result

def log_openai_cost(scope: str, model: str, usage: dict, meta: dict = None):
    """
    Log cost from OpenAI response usage object.
    usage dict should have: {prompt_tokens, completion_tokens, total_tokens}
    """
    input_tok = usage.get("prompt_tokens", 0)
    output_tok = usage.get("completion_tokens", 0)
    total_tok = usage.get("total_tokens", 0)
    
    cost = calculate_text_cost(model, input_tok, output_tok)
    record_cost(scope, model, total_tok, cost, meta)
    return cost
