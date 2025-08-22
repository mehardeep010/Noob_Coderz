"""
FunnyPDF Web Viewer — upload a PDF, pick tweak level (mild/spicy/chaotic),
preview original vs. funny side‑by‑side, and download the result.

How to run:
1) pip install flask pdfplumber fpdf pillow requests
2) Save this file as app.py and run:  python app.py
3) Open http://127.0.0.1:5000

Notes:
- Uses your existing humor pipeline (embedded below). If you already have it in a
  separate module, you can delete the embedded section and import instead.
- Uses PDF.js via CDN to render PDFs in-browser; downloads also available.
- Works fully offline after first load of the PDF.js CDN (or replace with local files).
"""
from __future__ import annotations

import io
import os
import re
import uuid
import random
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Tuple

from flask import (
    Flask, request, redirect, url_for, render_template_string,
    send_from_directory, abort, flash
)

# ===============
#  EMBEDDED: Minimal humor pipeline from your script
#  (kept intact; trimmed comments)
# ===============
import pdfplumber
from fpdf import FPDF
from PIL import Image
import requests

random.seed(42)

FUNNY_MAP = {
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


def extract_text(path: str) -> str:
    chunks = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            t = p.extract_text() or ""
            chunks.append(t)
    return "\n".join(chunks)


def apply_word_fun(text: str, intensity: float) -> str:
    for pat, repl in FUNNY_MAP.items():
        def subfun(m):
            return repl if random.random() < intensity else m.group(0)
        text = re.sub(pat, subfun, text, flags=re.IGNORECASE)
    return text


def sprinkle_emojis(text: str, intensity: float) -> str:
    if intensity <= 0:
        return text
    out_lines = []
    for line in text.splitlines():
        if not line.strip():
            out_lines.append(line)
            continue
        count = int(random.random() < intensity) + int(random.random() < intensity/2)
        if count:
            picks = " ".join(random.choice(EMOJIS) for _ in range(count))
            line = f"{line} {picks}"
        out_lines.append(line)
    return "\n".join(out_lines)


def add_fake_citations(text: str, intensity: float) -> str:
    if intensity <= 0:
        return text
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


# AI rewrite left in but off by default; works if OPENAI_API_KEY is set

def ai_rewrite(text: str, style: str) -> str:
    ai = os.getenv("AI_MODE", "none")
    if ai != "openai":
        return text
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        return text
    paras = [p for p in text.split("\n\n") if p.strip()]
    out_paras = []
    for p in paras:
        seg = p.strip()[:1200]
        try:
            import json, urllib.request
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                method="POST",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
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
        except Exception:
            out_paras.append(p)
    return "\n\n".join(out_paras)


class FunnyPDF(FPDF):
    def header(self):
        self.set_font("DejaVu", "B", 10)
        self.cell(0, 8, "Chaotic PDF Reader – Fun Edition", align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", size=8)
        self.cell(0, 10, f"Page {self.page_no()}  •  generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")

def fetch_random_cat() -> Image.Image:
    url = "https://cataas.com/cat"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return Image.new("RGB", (10, 10), (255, 255, 255))


def render_pdf(text, out_path, insert_cats=True, cat_every=4):
    pdf = FunnyPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # Register Unicode font
    font_path = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.add_font("DejaVu", "B", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)

    pdf.add_page()

    paragraphs = [p for p in text.split("\n\n")]
    pcount = 0

    for p in paragraphs:
        pcount += 1
        p = p.replace("\t", " ")
        p = re.sub(r"\s+", " ", p)
        pdf.multi_cell(0, 6, p)
        pdf.ln(2)

        if insert_cats and cat_every and pcount % cat_every == 0:
            try:
                img = fetch_random_cat()
                max_w = 120
                w, h = img.size
                scale = max_w / w
                new_w, new_h = int(w * scale), int(h * scale)
                img = img.resize((new_w, new_h))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                buf.seek(0)
                x = (210 - (new_w * 0.264583)) / 2
                pdf.image(buf, x=x, w=new_w * 0.264583)
                pdf.ln(5)
            except Exception:
                pass

    pdf.output(out_path)


def build_pipeline(raw_text: str, style_key: str, enable_emoji: bool = True, ai_mode: str = "none") -> str:
    intensity = STYLES.get(style_key, 0.2)
    t = raw_text
    t = apply_word_fun(t, intensity)
    os.environ["AI_MODE"] = ai_mode
    if ai_mode == "openai":
        t = ai_rewrite(t, style_key)
    if enable_emoji:
        t = sprinkle_emojis(t, intensity)
    t = add_fake_citations(t, intensity)
    return t

# ===============
#  Flask app
# ===============
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-please-change")
BASE_DIR = Path(tempfile.gettempdir()) / "funnypdf_web"
BASE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED = {"pdf"}


def _session_dir() -> Path:
    sid = uuid.uuid4().hex
    d = BASE_DIR / sid
    d.mkdir(parents=True, exist_ok=True)
    return d


def allowed_file(name: str) -> bool:
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED


INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>FunnyPDF — Tweak your PDF</title>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root { --bg:#0b1020; --card:#121936; --muted:#9fb0ff; --text:#e9edff; --accent:#7c8cff; }
    *{box-sizing:border-box}
    body{margin:0;font-family:Poppins,system-ui,Segoe UI,Roboto,Arial;background:linear-gradient(120deg,#0b1020,#0f1733);color:var(--text)}
    header{padding:24px 20px;text-align:center}
    h1{margin:0;font-size:clamp(20px,3.6vw,34px)}
    .wrapper{max-width:1200px;margin:0 auto;padding:0 16px 40px}
    form{background:var(--card);border:1px solid #26326a;border-radius:18px;padding:18px;display:grid;gap:12px;grid-template-columns:1fr}
    .row{display:flex;flex-wrap:wrap;gap:12px;align-items:center}
    .row > *{flex:1}
    .controls{display:flex;flex-wrap:wrap;gap:12px}
    label{font-weight:600;font-size:14px}
    input[type=file], select, input[type=number]{width:100%;padding:10px;border-radius:12px;border:1px solid #2b3672;background:#0f1530;color:var(--text)}
    .check{display:flex;align-items:center;gap:8px}
    button{padding:12px 16px;border:0;border-radius:12px;background:var(--accent);color:#0c1230;font-weight:700;cursor:pointer}
    .grid{display:grid;grid-template-columns:1fr;gap:16px;margin-top:18px}
    @media(min-width:1000px){.grid{grid-template-columns:1fr 1fr}}
    .card{background:var(--card);border:1px solid #26326a;border-radius:18px;padding:10px}
    .card h3{margin:8px 10px}
    iframe{width:100%;height:70vh;border:0;border-radius:12px;background:#000}
    .muted{color:var(--muted);font-size:12px}
  </style>
</head>
<body>
  <header>
    <h1>FunnyPDF — Chaotic PDF Tweaker</h1>
    <p class="muted">Upload a PDF · pick a vibe · preview original vs. funny</p>
  </header>
  <div class="wrapper">
    <form action="{{ url_for('process') }}" method="post" enctype="multipart/form-data">
      <div class="row">
        <div>
          <label>Upload PDF</label>
          <input type="file" name="pdf" accept="application/pdf" required />
        </div>
      </div>
      <div class="controls">
        <div>
          <label>Style</label>
          <select name="style">
            <option value="mild">mild</option>
            <option value="spicy">spicy</option>
            <option value="chaotic">chaotic</option>
          </select>
        </div>
        <div>
          <label>Cat every N paragraphs</label>
          <input type="number" name="cat_every" min="1" value="4" />
        </div>
        <label class="check"><input type="checkbox" name="emoji" checked /> sprinkle emojis</label>
        <label class="check"><input type="checkbox" name="cats" checked /> insert cats</label>
        <label class="check"><input type="checkbox" name="ai" /> AI rewrite (needs OPENAI_API_KEY)</label>
      </div>
      <div class="row">
        <button type="submit">Make it funny ✨</button>
      </div>
    </form>

    {% if orig_url and funny_url %}
    <marquee behavior="scroll" direction="left" scrollamount="20" style="color:red; font-size: 36px; font-weight: bold; margin: 20px 0;">
      YOU HAVE BEEN FOOLED!!! BWAHAHAHAHAH
    </marquee>
    <div class="grid">
      <div class="card">
        <h3>Original</h3>
        <iframe src="https://mozilla.github.io/pdf.js/web/viewer.html?file={{ orig_url | urlencode }}"></iframe>
        <div class="row" style="padding:10px"><a href="{{ orig_url }}" download><button>Download original</button></a></div>
      </div>
      <div class="card">
        <h3>Funny version ({{ style }})</h3>
        <iframe src="https://mozilla.github.io/pdf.js/web/viewer.html?file={{ funny_url | urlencode }}"></iframe>
        <div class="row" style="padding:10px"><a href="{{ funny_url }}" download><button>Download funny</button></a></div>
      </div>
    </div>
    {% endif %}

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul>
          {% for m in messages %}
            <li class="muted">{{ m }}</li>
          {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
  </div>
</body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(INDEX_HTML, orig_url=None, funny_url=None, style=None)


@app.post("/process")
def process():
    f = request.files.get("pdf")
    if not f or f.filename == "":
        flash("Please choose a PDF file.")
        return redirect(url_for("index"))
    if not allowed_file(f.filename):
        flash("Only .pdf files are allowed.")
        return redirect(url_for("index"))

    style = request.form.get("style", "mild")
    emoji = bool(request.form.get("emoji"))
    cats = bool(request.form.get("cats"))
    ai = "openai" if request.form.get("ai") else "none"
    try:
        cat_every = max(1, int(request.form.get("cat_every", "4")))
    except ValueError:
        cat_every = 4

    session_dir = _session_dir()
    orig_path = session_dir / "original.pdf"
    funny_path = session_dir / "funny.pdf"
    f.save(orig_path)

    # Build
    try:
        raw = extract_text(str(orig_path))
        if not raw.strip():
            flash("No extractable text found. (Scanned PDFs need OCR.)")
            # Still show original, but skip funny
            return render_template_string(
                INDEX_HTML,
                orig_url=url_for("serve_file", sid=session_dir.name, name="original.pdf"),
                funny_url=None,
                style=style,
            )
        funny_text = build_pipeline(raw, style_key=style, enable_emoji=emoji, ai_mode=ai)
        render_pdf(funny_text, str(funny_path), insert_cats=cats, cat_every=cat_every)
    except Exception as e:
        flash(f"Error while processing: {e}")
        return redirect(url_for("index"))

    return render_template_string(
        INDEX_HTML,
        orig_url=url_for("serve_file", sid=session_dir.name, name="original.pdf"),
        funny_url=url_for("serve_file", sid=session_dir.name, name="funny.pdf"),
        style=style,
    )


@app.get("/f/<sid>/<path:name>")
def serve_file(sid: str, name: str):
    d = BASE_DIR / sid
    if not d.exists():
        abort(404)
    # Security: restrict to our session dir and prevent path traversal
    safe = (d / name).resolve()
    if not str(safe).startswith(str(d.resolve())):
        abort(403)
    return send_from_directory(d, name, as_attachment=False, mimetype="application/pdf")


# alias for templates
serve_file.methods = ["GET"]


if __name__ == "__main__":
    app.run(debug=True)
