import os, base64, io, time, json, hashlib
from config import CFG
from openai import OpenAI
from cache import get_cached, set_cached

client = OpenAI(api_key=CFG["OPENAI_API_KEY"])

def _hash(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:12]

def generate_text(topic: str, brand_bullets: list[str], style: str, variants: int = 3):
    payload = {"topic": topic, "brand": brand_bullets, "style": style, "v": variants}
    cached, meta = get_cached("text_v1", payload)
    if cached: return json.loads(cached)

    sys = (
      "You are a social content generator. Return concise, high-signal posts with a strong hook, "
      "1 CTA, 3-5 hashtags (lowercase), and no fluff. Output JSON: {variants:[{title, body}]}."
    )
    user = f"Topic: {topic}\nBrand:\n- " + "\n- ".join(brand_bullets) + f"\nStyle: {style}\nVariants: {variants}"

    rsp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.4,
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
        response_format={"type":"json_object"}
    )
    out = rsp.choices[0].message.content
    set_cached("text_v1", payload, out, {"tokens": rsp.usage.total_tokens if rsp.usage else None})
    return json.loads(out)

def generate_image(prompt: str, size: str = "1024x1024") -> bytes:
    payload = {"img_prompt": prompt, "size": size}
    cached, meta = get_cached("img_v1", payload)
    if cached:
        # cached stores a path in metadata; re-read
        with open(meta["path"], "rb") as f: return f.read()

    img = client.images.generate(model="gpt-image-1", prompt=prompt, size=size)
    b64 = img.data[0].b64_json
    raw = base64.b64decode(b64)
    set_cached("img_v1", payload, "OK", {"note":"image cached via file"})
    return raw

def bmad_supervisor(topics: list[str], brand_bullets: list[str]):
    """
    Returns best (title, body, image_prompt)
    """
    sys = ("You are the BMAD Supervisor (Architect/Strategist/Developer/Debugger/Manager). "
           "Pick the best single content plan for LinkedIn & Facebook, return JSON: "
           "{title, body_style, image_prompt, reasoning}. Keep it under 900 chars body.")
    user = "Topics:\n- " + "\n- ".join(topics) + "\nBrand:\n- " + "\n- ".join(brand_bullets)
    rsp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
        response_format={"type":"json_object"}
    )
    return json.loads(rsp.choices[0].message.content)
