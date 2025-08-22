import argparse
import os
import random
import re
import sys
import io
from datetime import datetime

import pdfplumber
from fpdf import FPDF
from PIL import Image
import requests

# -------------- Utility: seeded randomness (stable funny) --------------
random.seed(42)

# -------------- Safe-ish playful replacements --------------
FUNNY_MAP = {
    # tone-softening substitutions
    r"\bobese\b": "chonky",
    r"\boverweight\b": "chonky",
    r"\bfat\b": "snack-powered",
    r"\bbullied\b": "got roasted",
    r"\bargue\b": "enter a spicy debate",
    r"\bangry\b": "internally screaming",
    r"\bmanager\b": "email overlord",
    r"\bprincipal\b": "rule grandmaster",
    r"\bteacher\b": "knowledge dispenser",
    r"\bboss\b": "overlord of coffee",
    r"\bworked hard\b": "sweated like a gamer on 1% battery",
    r"\bmeeting\b": "snooze summit",
    r"\bstudy\b": "lore grind",
    r"\bstudent\b": "XP farmer",
}

EMOJIS = ["😂", "😼", "✨", "🙃", "🫠", "🔥", "🥲", "🧠", "🫡", "🤝", "🍿", "🐱", "📚", "☕", "🌀", "🧃"]

FAKE_CITES = [
    "(TotallyRealJournal, 2024)",
    "(See: Figure 69)",
    "(Peer-reviewed by 3 cats)",
    "(Source: Trust me bro)",
    "(As foretold by ancient memes)",
]

STYLES = {"mild": 0.2, "spicy": 0.5, "chaotic": 0.9}

# -------------- Extraction --------------

def extract_text(path):
    chunks = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            t = p.extract_text() or ""
            chunks.append(t)
    return "\n".join(chunks)

# -------------- Humor transforms --------------

def apply_word_fun(text, intensity):
    # Replace words probabilistically
    for pat, repl in FUNNY_MAP.items():
        def subfun(m):
            return repl if random.random() < intensity else m.group(0)
        text = re.sub(pat, subfun, text, flags=re.IGNORECASE)
    return text


def sprinkle_emojis(text, intensity):
    if intensity <= 0: return text
    out_lines = []
    for line in text.splitlines():
        if not line.strip():
            out_lines.append(line)
            continue
        # Add 0–2 emojis per line based on intensity
        count = int(random.random() < intensity) + int(random.random() < intensity/2)
        if count:
            picks = " ".join(random.choice(EMOJIS) for _ in range(count))
            line = f"{line} {picks}"
        out_lines.append(line)
    return "\n".join(out_lines)


def add_fake_citations(text, intensity):
    if intensity <= 0: return text
    sentences = re.split(r"(\.|\?|!)(\s+)", text)
    out = []
    for i in range(0, len(sentences), 3):
        chunk = sentences[i]
        punct = sentences[i+1] if i+1 < len(sentences) else ""
        space = sentences[i+2] if i+2 < len(sentences) else ""
        if chunk.strip() and random.random() < intensity / 3:
            chunk += " " + random.choice(FAKE_CITES)
        out.extend([chunk, punct, space])
    return "".join(out)

# -------------- Optional AI rewrite --------------

def ai_rewrite(text, style):
    """Optionally rewrite paragraphs via OpenAI if enabled in env and requested.
       Keeps it short and playful; avoids slurs.
    """
    ai = os.getenv("AI_MODE", "none")
    if ai == "none":
        return text
    if ai != "openai":
        return text
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        return text

    # Chunk roughly to <= 800 chars per prompt to stay fast
    paras = [p for p in text.split("\n\n") if p.strip()]
    out_paras = []
    for p in paras:
        seg = p.strip()
        if not seg:
            out_paras.append(p)
            continue
        seg = seg[:1200]
        try:
            # Use the REST API directly to avoid extra deps
            import json, urllib.request
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                method="POST",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": model,
                    "messages": [
                        {"role": "system", "content": (
                            "Rewrite user text with playful, meme-like humor; keep meaning; "
                            "avoid slurs/insults; keep it PG-13; add mild sarcasm; "
                            f"style={style}."
                        )},
                        {"role": "user", "content": seg},
                    ],
                    "temperature": 0.9,
                    "max_tokens": 300,
                }).encode("utf-8"),
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            out_paras.append(content.strip() or p)
        except Exception as e:
            # Fallback quietly on any error
            out_paras.append(p)
    return "\n\n".join(out_paras)

# -------------- Cat images --------------

def fetch_random_cat():
    url = "https://cataas.com/cat"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        # Fallback: tiny 1x1 white image
        img = Image.new("RGB", (10, 10), (255, 255, 255))
        return img

# -------------- PDF Writer --------------

class FunnyPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, "Chaotic PDF Reader – Fun Edition", align="C")
        self.ln(10)

    def footer(self):n
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.cell(0, 10, f"Page {self.page_no()}  •  generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")


def render_pdf(text, out_path, insert_cats=True, cat_every=4):
    pdf = FunnyPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    paragraphs = [p for p in text.split("\n\n")]
    pcount = 0

    for p in paragraphs:
        pcount += 1
        p = p.replace("\t", " ")
        p = re.sub(r"\s+", " ", p)
        # Wrap via multi_cell
        pdf.multi_cell(0, 6, p)
        pdf.ln(2)

        if insert_cats and cat_every and pcount % cat_every == 0:
            try:
                img = fetch_random_cat()
                # Resize to width 120mm, keep aspect
                max_w = 120
                w, h = img.size
                scale = max_w / w
                new_w, new_h = int(w * scale), int(h * scale)
                img = img.resize((new_w, new_h))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                buf.seek(0)
                # Center image
                x = (210 - (new_w * 0.264583)) / 2  # px→mm approx
                pdf.image(buf, x=x, w=new_w * 0.264583)
                pdf.ln(5)
            except Exception:
                pass

    pdf.output(out_path)

# -------------- Pipeline orchestrator --------------

def build_pipeline(raw_text, style_key, enable_emoji=True, ai_mode="none"):
    intensity = STYLES.get(style_key, 0.2)
    t = raw_text

    # Rule-based first (fast)
    t = apply_word_fun(t, intensity)

    # Optional AI rewrite (set env AI_MODE=openai to enable)
    os.environ["AI_MODE"] = ai_mode
    if ai_mode == "openai":
        t = ai_rewrite(t, style_key)

    # Sprinkle extras
    if enable_emoji:
        t = sprinkle_emojis(t, intensity)
    t = add_fake_citations(t, intensity)

    return t

# -------------- CLI --------------

def main():
    p = argparse.ArgumentParser(description="Chaotic PDF Reader – funny-ify PDFs")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", dest="outp", required=True)
    p.add_argument("--style", default="mild", choices=list(STYLES.keys()))
    p.add_argument("--cats", default="true")
    p.add_argument("--emoji", default="true")
    p.add_argument("--ai", default="none", choices=["none", "openai"])  # set OPENAI_API_KEY to use
    p.add_argument("--cat-every", default="4")
    args = p.parse_args()

    try:
        raw = extract_text(args.inp)
        if not raw.strip():
            raise RuntimeError("No extractable text. (Scanned PDFs need OCR.)")

        funny = build_pipeline(
            raw,
            style_key=args.style,
            enable_emoji=(args.emoji.lower() == "true"),
            ai_mode=args.ai,
        )

        render_pdf(
            funny,
            args.outp,
            insert_cats=(args.cats.lower() == "true"),
            cat_every=max(1, int(args.cat_every)),
        )
        return 0
    except Exception as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())

