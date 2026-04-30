"""
Smart Medical Sign Display System — v5
=======================================
Single-page layout:
  1. Input section (อัดเสียง / อัปโหลด / พิมพ์ / ตัวอย่าง) — ทั้งหมดในหน้าเดียว
  2. Editable transcript — แก้ไข text ก่อน process
  3. NLP Pipeline trace (simplify → tokenize)
  4. Output: ข้อความต้นฉบับ | ข้อความเข้าใจง่าย | Tokens
  5. ภาษามือ video/emoji player
"""

import streamlit as st
import streamlit.components.v1 as components
import os, re, json, base64, tempfile
# Auto-create placeholder signs if missing
import subprocess, os
if not os.path.exists("signs") or len([f for f in os.listdir("signs") if f.endswith(".mp4")]) < 10:
    subprocess.run(["python", "create_placeholder_signs.py"], check=False)
from pathlib import Path

# ─── Streamlit version check ─────────────────────────────────────────────────
_st_ver = tuple(int(x) for x in st.__version__.split(".")[:2])
AUDIO_INPUT_SUPPORTED = _st_ver >= (1, 34)

# ─── Optional deps ────────────────────────────────────────────────────────────
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from pythainlp.tokenize import word_tokenize
    from pythainlp.corpus.common import thai_stopwords
    PYTHAINLP_AVAILABLE = True
except ImportError:
    PYTHAINLP_AVAILABLE = False

# ─── Import sign_data.py ──────────────────────────────────────────────────────
try:
    from sign_data import SIGN_DICT, SIMPLIFICATION_RULES, CAT_COLOR
    SIGN_DATA_LOADED = True
except ImportError:
    SIGN_DATA_LOADED = False
    CAT_COLOR = {}
    SIGN_DICT = {
        "ไม่":   {"emoji":"🚫","color":"#e74c3c","video":"mai.mp4",   "category":"คำสั่ง"},
        "ห้าม":  {"emoji":"🛑","color":"#e74c3c","video":"ham.mp4",   "category":"คำสั่ง"},
        "กิน":   {"emoji":"🍽️","color":"#2980b9","video":"gin.mp4",   "category":"กิริยา"},
        "ยา":    {"emoji":"💊","color":"#f44336","video":"ya.mp4",    "category":"ยา"},
        "หมอ":   {"emoji":"👨‍⚕️","color":"#0288d1","video":"mor.mp4",  "category":"บุคลากร"},
        "ตรวจ":  {"emoji":"🔬","color":"#2196f3","video":"truat.mp4","category":"การตรวจ"},
        "ปวด":   {"emoji":"🤕","color":"#c62828","video":"puat.mp4",  "category":"อาการ"},
        "น้ำ":   {"emoji":"💧","color":"#039be5","video":"nam.mp4",   "category":"กิริยา"},
        "ก่อน":  {"emoji":"⬅️","color":"#546e7a","video":"kon.mp4",  "category":"วันเวลา"},
        "หลัง":  {"emoji":"⏩","color":"#607d8b","video":"lang.mp4", "category":"วันเวลา"},
    }
    SIMPLIFICATION_RULES = [
        (r"กรุณา\s*",""), (r"โปรด\s*",""),
        (r"รับประทาน","กิน"), (r"งดอาหาร","ไม่กิน"),
        (r"แพทย์","หมอ"), (r"เข้ารับการตรวจ","ตรวจ"),
    ]

# ─── Import pipeline ──────────────────────────────────────────────────────────
try:
    from nlp_pipeline import full_pipeline
    PIPELINE_LOADED = True
except ImportError:
    PIPELINE_LOADED = False

try:
    from intent_data import get_sign_key
    INTENT_LOADED = True
except ImportError:
    INTENT_LOADED = False
    def get_sign_key(word): return None

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
SIGN_DIR = BASE_DIR / "signs"
SIGN_DIR.mkdir(exist_ok=True)

# ─── ffmpeg PATH ──────────────────────────────────────────────────────────────
import glob as _glob
_search_patterns = [
    str(BASE_DIR / "ffmpeg*" / "bin"),
    str(BASE_DIR / "ffmpeg*" / "ffmpeg*" / "bin"),
]
for _pat in _search_patterns:
    _found = sorted(_glob.glob(_pat))
    if _found:
        os.environ["PATH"] = _found[-1] + os.pathsep + os.environ.get("PATH", "")
        break
else:
    _hc = r"C:\Users\apasitapasukree\PycharmProjects\FinalProject_NLP\ffmpeg-8.1-essentials_build\bin"
    if os.path.isdir(_hc):
        os.environ["PATH"] = _hc + os.pathsep + os.environ.get("PATH", "")

# ══════════════════════════════════════════════════════════════════════════════
# NLP HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _local_preprocess(text):
    text = re.sub(r'["""\'\'\'()\[\]{}<>]', "", text)
    text = re.sub(r"ๆ", "", text)
    return re.sub(r"\s+", " ", text).strip()

def _local_simplify(text):
    result = text
    for pattern, replacement in SIMPLIFICATION_RULES:
        result = re.sub(pattern, replacement, result)
    return re.sub(r"\s+", " ", result).strip()

def _local_tokenize(text):
    if PYTHAINLP_AVAILABLE:
        keep = {"ไม่","ห้าม","ต้อง","ก่อน","หลัง","ระวัง","มาก","น้อย","ได้","ควร"}
        stops = thai_stopwords()
        toks = word_tokenize(text, engine="newmm", keep_whitespace=False)
        return [x for x in toks if x.strip() and (x not in stops or x in keep)]
    result, keys = [], sorted(SIGN_DICT.keys(), key=len, reverse=True)
    while text:
        matched = False
        for k in keys:
            if text.startswith(k):
                result.append(k); text = text[len(k):]; matched = True; break
        if not matched:
            result.append(text[0]); text = text[1:]
    return [x for x in result if x.strip()]

def _local_map_signs(tokens):
    out = []
    for tok in tokens:
        sign_key = get_sign_key(tok) or tok
        if sign_key in SIGN_DICT:
            info = SIGN_DICT[sign_key]
            vid_path = SIGN_DIR / info["video"]
            out.append({**info, "token": tok, "label": sign_key,
                        "found": True, "has_video": vid_path.exists()})
        else:
            out.append({"token": tok, "emoji": "❓", "color": "#95a5a6",
                        "video": None, "found": False, "has_video": False, "category": "unknown"})
    return out

def run_pipeline(text):
    if PIPELINE_LOADED:
        result = full_pipeline(text)
        for s in result["signs"]:
            s["has_video"] = (SIGN_DIR / s["video"]).exists() if s.get("video") else False
        return result
    pre  = _local_preprocess(text)
    simp = _local_simplify(pre)
    toks = _local_tokenize(simp)
    signs = _local_map_signs(toks)
    n_found = sum(1 for s in signs if s["found"])
    return {"original": text, "preprocessed": pre, "simplified": simp,
            "tokens": toks, "signs": signs, "n_signs": len(signs),
            "n_found": n_found, "coverage": n_found / max(len(signs), 1)}

# ─── Whisper STT ──────────────────────────────────────────────────────────────
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("large")

MEDICAL_PROMPT = (
    "รับประทานยา กินยา ดื่มน้ำ งดอาหาร นอนพัก ตรวจเลือด เจาะเลือด "
    "ห้ามกิน ไม่ได้กิน ก่อนอาหาร หลังอาหาร วันละสองครั้ง "
    "พยาบาล แพทย์ โรงพยาบาล แผล ปวด เจ็บ ยาเม็ด หายใจ"
)

def do_whisper(tmp_path):
    if WHISPER_AVAILABLE:
        model = load_whisper_model()
        res = model.transcribe(
            tmp_path, language="th", initial_prompt=MEDICAL_PROMPT,
            temperature=0.0, best_of=1, beam_size=5, condition_on_previous_text=False,
        )
        return res["text"].strip()
    return "กรุณางดอาหารก่อนเข้ารับการตรวจ"

def video_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & STYLES
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Medical Sign Display", page_icon="🏥", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&family=Kanit:wght@500;700&display=swap');
* { font-family: 'Sarabun', sans-serif; }

.main-title {
  font-family:'Kanit',sans-serif; font-size:2rem; font-weight:700;
  color:#1a5276; text-align:center; margin-bottom:.2rem;
}
.subtitle { text-align:center; color:#5d6d7e; font-size:.95rem; margin-bottom:1.2rem }

/* Step section headers */
.step-header {
  display:flex; align-items:center; gap:.6rem;
  font-family:'Kanit',sans-serif; font-size:1.1rem; font-weight:700;
  color:#1a5276; margin:1.4rem 0 .5rem;
  border-bottom:2px solid #d6eaf8; padding-bottom:.4rem;
}
.step-badge {
  background:#1a5276; color:#fff; border-radius:50%;
  width:28px; height:28px; display:flex; align-items:center;
  justify-content:center; font-size:.85rem; font-weight:700; flex-shrink:0;
}

/* Input mode buttons */
.mode-btn-row { display:flex; gap:8px; margin-bottom:1rem; flex-wrap:wrap; }

/* Cards */
.card { background:#fff; border-radius:16px; padding:1.2rem 1.4rem;
  box-shadow:0 2px 10px rgba(0,0,0,.07); margin-bottom:.8rem }
.card-blue   { border-left:5px solid #1a5276 }
.card-green  { border-left:5px solid #196f3d }
.card-purple { border-left:5px solid #7d3c98 }
.stitle { font-family:'Kanit',sans-serif; font-weight:700; font-size:.85rem;
  text-transform:uppercase; letter-spacing:.08em; color:#1a5276; margin-bottom:.5rem }
.thai-orig { font-size:1.55rem; color:#1c2833; line-height:1.7 }
.thai-simp { font-size:1.85rem; font-weight:700; color:#196f3d; line-height:1.7 }

/* Token pills */
.tok-pill {
  background:#eaf4fb; color:#1a5276; border-radius:20px;
  padding:3px 12px; margin:2px; font-size:.88rem; font-weight:700; display:inline-block;
}

/* Editable transcript box */
.transcript-hint {
  font-size:.82rem; color:#7f8c8d; margin-bottom:.3rem;
}

/* Sign cards row */
.sign-row { display:flex; flex-wrap:wrap; gap:10px; margin-top:.4rem }
.scard {
  border-radius:12px; padding:10px 14px; text-align:center; min-width:70px;
  cursor:pointer; border:2px solid transparent; transition:transform .15s;
}
.scard:hover { transform:scale(1.08) }
.semoji { font-size:2rem; display:block; margin-bottom:4px }
.slabel { font-size:.82rem; font-weight:700; color:#1a5276 }

/* Pipeline trace */
.pipe-trace {
  font-size:.92rem; line-height:2.2; background:#fafafa;
  border-radius:10px; padding:.8rem 1rem;
}

/* Connector arrow between steps */
.step-arrow {
  text-align:center; color:#aab7b8; font-size:1.4rem; margin:-.2rem 0;
}

/* Input section card */
.input-section {
  background:#f8fbff; border-radius:16px; padding:1.2rem 1.4rem;
  border:1.5px solid #d6eaf8; margin-bottom:.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("result", None),
    ("raw_transcript", ""),        # text จาก whisper / upload / พิมพ์
    ("edit_transcript", ""),       # text ที่แก้ไขแล้ว (ก่อน run_pipeline)
    ("show_edit", False),          # แสดง text area แก้ไขหรือเปล่า
    ("input_mode", "rec"),         # rec / upload / text / example
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏥 Medical Sign v5")
    st.divider()

    show_pipeline = st.checkbox("แสดง NLP Pipeline", True)
    show_tokens   = st.checkbox("แสดง Token", True)
    show_unknown  = st.checkbox("แสดงคำไม่รู้จัก", True)

    st.divider()

    n_words  = len(SIGN_DICT)
    n_rules  = len(SIMPLIFICATION_RULES)
    n_videos = sum(1 for info in SIGN_DICT.values() if (SIGN_DIR / info["video"]).exists())
    n_cats   = len(set(v.get("category","") for v in SIGN_DICT.values()))

    st.info(f"พจนานุกรม: **{n_words} คำ** ({n_cats} หมวด)")
    st.info(f"กฎ NLP: **{n_rules} กฎ**")
    st.info(f"วิดีโอพร้อม: **{n_videos}/{n_words}**")

    for label, ok, msg_ok, msg_fail in [
        ("sign_data.py", SIGN_DATA_LOADED, "✅ sign_data.py โหลดสำเร็จ", "⚠️ ไม่พบ sign_data.py — ใช้ fallback"),
        ("nlp_pipeline.py", PIPELINE_LOADED, "✅ nlp_pipeline.py โหลดสำเร็จ", "⚠️ ไม่พบ nlp_pipeline.py — ใช้ fallback"),
        ("intent_data.py", INTENT_LOADED, "✅ intent_data.py โหลดสำเร็จ", "⚠️ ไม่พบ intent_data.py — synonym ไม่ทำงาน"),
        ("Whisper", WHISPER_AVAILABLE, "✅ Whisper พร้อม", "⚠️ Whisper ไม่ได้ติดตั้ง"),
        ("PyThaiNLP", PYTHAINLP_AVAILABLE, "✅ PyThaiNLP พร้อม", "⚠️ PyThaiNLP fallback"),
    ]:
        (st.success if ok else st.warning)(msg_ok if ok else msg_fail)

    st.divider()
    st.markdown("**หมวดหมู่คำศัพท์**")
    cat_count = {}
    for info in SIGN_DICT.values():
        c = info.get("category","อื่นๆ")
        cat_count[c] = cat_count.get(c,0) + 1
    for cat, cnt in sorted(cat_count.items(), key=lambda x:-x[1]):
        color = CAT_COLOR.get(cat, "#95a5a6")
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:2px 6px;border-radius:6px;margin-bottom:3px;'
            f'background:{color}22;border-left:3px solid {color}">'
            f'<span style="font-size:.8rem">{cat}</span>'
            f'<span style="font-size:.8rem;font-weight:700;color:{color}">{cnt}</span>'
            f'</div>', unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="main-title">🏥 Smart Medical Sign Display</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">แปลงคำพูดแพทย์ → ข้อความ → ภาษามือ สำหรับผู้พิการทางการได้ยิน</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# ──────────────────────── STEP 1: INPUT ──────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="step-header">'
    '<div class="step-badge">1</div>'
    '<span>รับเสียง / ข้อความ</span>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Mode selector ─────────────────────────────────────────────────────────────
mode_labels = {
    "rec":     "🎙️ อัดเสียง",
    "upload":  "📁 อัปโหลดไฟล์",
    "text":    "⌨️ พิมพ์ข้อความ",
    "example": "📋 ตัวอย่าง",
}
cols_mode = st.columns(len(mode_labels))
for col, (mode, label) in zip(cols_mode, mode_labels.items()):
    with col:
        active = st.session_state.input_mode == mode
        btn_type = "primary" if active else "secondary"
        if st.button(label, key=f"mode_{mode}", type=btn_type, use_container_width=True):
            st.session_state.input_mode = mode

st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

# ── Input panel (single-page, no tabs) ───────────────────────────────────────
mode = st.session_state.input_mode

# ─── MODE: อัดเสียง ──────────────────────────────────────────────────────────
if mode == "rec":
    with st.container(border=True):
        st.markdown("##### 🎙️ อัดเสียงในหน้าเว็บ")
        st.caption("1) กดปุ่มไมค์ด้านล่าง → 2) พูดคำสั่งแพทย์ → 3) กดหยุด → 4) กด **ถอดเสียง ▶**")

        recorded_audio = st.audio_input("🎙️ อัดเสียงที่นี่", key="recorder_widget")

        col_btn, col_status = st.columns([1, 3])
        with col_btn:
            transcribe_clicked = st.button(
                "🔊 ถอดเสียง ▶", key="btn_transcribe", type="primary", use_container_width=True
            )
        with col_status:
            status_box = st.empty()

        if transcribe_clicked:
            if recorded_audio is None:
                status_box.warning("⚠️ ยังไม่มีข้อมูลเสียง — กรุณากดปุ่มไมค์อัดเสียงก่อน")
            else:
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        f.write(recorded_audio.read())
                        tmp_path = f.name
                    try:
                        if WHISPER_AVAILABLE:
                            with st.spinner("🎙️ Whisper กำลังถอดเสียง..."):
                                text = do_whisper(tmp_path)
                            status_box.success(f"✅ ถอดเสียงสำเร็จ")
                        else:
                            text = "กรุณางดอาหารก่อนเข้ารับการตรวจ"
                            status_box.warning("⚠️ Whisper ไม่ได้ติดตั้ง — แสดงตัวอย่างแทน")
                        st.session_state.raw_transcript  = text
                        st.session_state.edit_transcript = text
                        st.session_state.show_edit       = True
                        st.session_state.result          = None   # reset output
                    finally:
                        try: os.unlink(tmp_path)
                        except OSError: pass
                except Exception as e:
                    status_box.error(f"❌ เกิดข้อผิดพลาด: {e}")

# ─── MODE: อัปโหลดไฟล์ ───────────────────────────────────────────────────────
elif mode == "upload":
    with st.container(border=True):
        st.markdown("##### 📁 อัปโหลดไฟล์เสียง")
        audio_file = st.file_uploader("อัปโหลดไฟล์เสียง", type=["wav","mp3","m4a","webm","ogg"])
        if audio_file:
            st.audio(audio_file)
            if st.button("🔊 ถอดเสียง", key="btn_up", type="primary"):
                suffix = Path(audio_file.name).suffix or ".wav"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                    f.write(audio_file.read())
                    tmp_path = f.name
                try:
                    with st.spinner("กำลังถอดเสียง..."):
                        text = do_whisper(tmp_path)
                    if not WHISPER_AVAILABLE:
                        st.info("⚠️ Whisper ไม่ได้ติดตั้ง — ใช้ข้อความตัวอย่าง")
                    st.session_state.raw_transcript  = text
                    st.session_state.edit_transcript = text
                    st.session_state.show_edit       = True
                    st.session_state.result          = None
                finally:
                    try: os.unlink(tmp_path)
                    except OSError: pass

# ─── MODE: พิมพ์ข้อความ ──────────────────────────────────────────────────────
elif mode == "text":
    with st.container(border=True):
        st.markdown("##### ⌨️ พิมพ์ข้อความ")
        txt = st.text_area(
            "พิมพ์ข้อความภาษาไทย",
            placeholder="เช่น: กรุณางดอาหารก่อนเข้ารับการตรวจ",
            height=90, key="manual_text",
        )
        if st.button("✅ ใช้ข้อความนี้", key="btn_txt", type="primary") and txt.strip():
            st.session_state.raw_transcript  = txt.strip()
            st.session_state.edit_transcript = txt.strip()
            st.session_state.show_edit       = True
            st.session_state.result          = None

# ─── MODE: ตัวอย่าง ──────────────────────────────────────────────────────────
elif mode == "example":
    with st.container(border=True):
        st.markdown("##### 📋 เลือกประโยคตัวอย่าง")
        _sample_path = BASE_DIR / "sample_dataset.json"
        if _sample_path.exists():
            try:
                with open(_sample_path, encoding="utf-8") as _f:
                    _samples = json.load(_f)
                EXAMPLES = [item["original"] for item in _samples if "original" in item]
            except Exception:
                EXAMPLES = []
        else:
            EXAMPLES = []

        if not EXAMPLES:
            EXAMPLES = [
                "กรุณางดอาหารก่อนเข้ารับการตรวจ",
                "รับประทานยาเม็ดวันละ 2 ครั้ง หลังอาหาร",
                "กรุณานอนพักผ่อนและงดออกกำลังกาย",
                "โปรดแจ้งให้ทราบหากมีอาการปวด",
                "ต้องดื่มน้ำมากหลังการตรวจ",
                "ห้ามรับประทานอาหารก่อนเจาะเลือด",
                "กรุณานั่งรอเจ้าหน้าที่พยาบาล",
                "แพทย์จะมาตรวจในตอนเช้าพรุ่งนี้",
            ]

        c1, c2 = st.columns(2)
        for i, ex in enumerate(EXAMPLES):
            with (c1 if i % 2 == 0 else c2):
                if st.button(f"💬 {ex}", key=f"ex{i}", use_container_width=True):
                    st.session_state.raw_transcript  = ex
                    st.session_state.edit_transcript = ex
                    st.session_state.show_edit       = True
                    st.session_state.result          = None

# ══════════════════════════════════════════════════════════════════════════════
# ──────────────────────── STEP 2: TRANSCRIPT EDIT ────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.show_edit and st.session_state.edit_transcript:

    st.markdown('<div class="step-arrow">▼</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="step-header">'
        '<div class="step-badge">2</div>'
        '<span>ตรวจสอบ / แก้ไขข้อความ</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(
            '<p class="transcript-hint">📝 ตรวจสอบข้อความที่ได้จากเสียง หากมีข้อผิดพลาดสามารถแก้ไขได้ก่อนประมวลผล</p>',
            unsafe_allow_html=True,
        )

        edited = st.text_area(
            "ข้อความ (แก้ไขได้)",
            value=st.session_state.edit_transcript,
            height=80,
            key="transcript_edit_box",
            label_visibility="collapsed",
        )
        # sync back
        st.session_state.edit_transcript = edited

        col_proc, col_reset = st.columns([2, 1])
        with col_proc:
            if st.button("🔍 ประมวลผล → ภาษามือ", key="btn_process", type="primary",
                         use_container_width=True, disabled=not edited.strip()):
                with st.spinner("กำลังประมวลผล NLP..."):
                    st.session_state.result = run_pipeline(edited.strip())
        with col_reset:
            if st.button("↩️ ล้างข้อความ", key="btn_clear_transcript", use_container_width=True):
                st.session_state.raw_transcript  = ""
                st.session_state.edit_transcript = ""
                st.session_state.show_edit       = False
                st.session_state.result          = None
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ──────────────────────── STEP 3: OUTPUT ─────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
result = st.session_state.result

if result:
    st.markdown('<div class="step-arrow">▼</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="step-header">'
        '<div class="step-badge">3</div>'
        '<span>ผลลัพธ์ — แสดงผลสำหรับผู้ป่วย</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── NLP Pipeline trace ────────────────────────────────────────────────────
    if show_pipeline:
        with st.expander("🔍 ขั้นตอน NLP Pipeline", expanded=True):
            pills = "".join(
                f'<span style="background:#fef9e7;border-radius:8px;padding:1px 8px;'
                f'margin:2px;display:inline-block">{t}</span>'
                for t in result["tokens"]
            )
            st.markdown(f"""
<div class="pipe-trace">
  <b style="color:#7d3c98">① Input</b> → {result['original']}<br>
  <b style="color:#1a5276">② Simplify</b> → <b style="color:#196f3d">{result['simplified']}</b><br>
  <b style="color:#e67e22">③ Tokenize</b> → {pills}<br>
  <b style="color:#2980b9">④ Sign Match</b> →
    {sum(1 for s in result['signs'] if s['found'])}/{len(result['signs'])} คำ
    ({result['coverage']*100:.0f}%)
</div>""", unsafe_allow_html=True)

    # ── Text cards ────────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div class="card card-blue">'
            f'<div class="stitle">📝 ข้อความต้นฉบับ</div>'
            f'<div class="thai-orig">{result["original"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="card card-green">'
            f'<div class="stitle" style="color:#196f3d">✅ ข้อความที่เข้าใจง่าย</div>'
            f'<div class="thai-simp">{result["simplified"]}</div></div>',
            unsafe_allow_html=True,
        )

    # ── Token pills ───────────────────────────────────────────────────────────
    if show_tokens:
        pills = "".join(
            f'<span class="tok-pill">{t}</span>'
            for t in result["tokens"]
        )
        st.markdown(
            f'<div class="card card-purple">'
            f'<div class="stitle" style="color:#7d3c98">✂️ Token (Tokenization)</div>'
            f'<div style="margin-top:.3rem">{pills}</div></div>',
            unsafe_allow_html=True,
        )

    # ── Sign Language Section ─────────────────────────────────────────────────
    st.markdown('<div class="step-arrow">▼</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="step-header">'
        '<div class="step-badge">4</div>'
        '<span>🤟 ล่ามภาษามือ</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    signs = result["signs"] if show_unknown else [s for s in result["signs"] if s["found"]]

    if signs:
        # Word cards row
        cards_html = '<div class="sign-row">'
        for i, s in enumerate(signs):
            bg = "#eaf4fb" if s["found"] else "#f5f5f5"
            bc = "#aed6f1" if s["found"] else "#ddd"
            hv = "🎬" if s.get("has_video") else ""
            cards_html += (
                f'<div class="scard" id="sc{i}" onclick="selectCard({i})" '
                f'style="background:{bg};border-color:{bc}">'
                f'<span class="semoji">{s["emoji"]}</span>'
                f'<span class="slabel">{s["token"]}</span>'
                f'<span style="font-size:.6rem;color:#999;display:block">{hv}</span></div>'
            )
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)

        # Build payload for video player
        sign_payload = []
        for s in signs:
            vp = SIGN_DIR / (s.get("video") or "x")
            if s.get("has_video") and vp.exists():
                sign_payload.append({
                    "token": s["token"], "type": "video",
                    "b64": video_b64(vp), "emoji": s["emoji"],
                    "color": s.get("color", "#1a5276"),
                })
            else:
                sign_payload.append({
                    "token": s["token"], "type": "emoji",
                    "b64": "", "emoji": s["emoji"],
                    "color": s.get("color", "#1a5276"),
                })

        # Video player
        player_html = f"""
<div style="font-family:'Sarabun',sans-serif">
<div id="player" style="background:#0d1117;border-radius:16px;padding:1.4rem 1.2rem;
     text-align:center;border:2px solid #21262d">

  <div id="stepLbl" style="font-size:.9rem;color:#8b949e;letter-spacing:.06em;margin-bottom:.5rem">
    กดเล่นเพื่อดูภาษามือทีละท่า
  </div>
  <div id="wordLbl" style="font-size:2.6rem;font-weight:700;color:#e6edf3;margin-bottom:.6rem">─</div>

  <video id="vidEl" playsinline muted
    style="display:none;max-height:440px;width:auto;max-width:96%;border-radius:14px;margin-bottom:.6rem">
  </video>
  <div id="emojiEl" style="font-size:10rem;line-height:1;display:block;margin-bottom:.6rem">🤟</div>

  <div style="background:#21262d;border-radius:4px;height:5px;margin:.6rem 8px">
    <div id="prog" style="background:#58a6ff;height:5px;border-radius:4px;
         width:0%;transition:width .35s ease"></div>
  </div>

  <div id="pillRow" style="display:flex;flex-wrap:wrap;gap:5px;justify-content:center;margin:.5rem 0 .8rem"></div>

  <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap">
    <button onclick="doPrev()"
      style="background:#21262d;color:#c9d1d9;border:1px solid #30363d;
             border-radius:8px;padding:7px 16px;cursor:pointer;font-family:'Sarabun',sans-serif">
      ⏮ ก่อนหน้า
    </button>
    <button id="btnPlay" onclick="togglePlay()"
      style="background:#1f6feb;color:#fff;border:none;border-radius:8px;
             padding:8px 26px;font-size:.95rem;cursor:pointer;min-width:140px;
             font-family:'Sarabun',sans-serif;font-weight:600">
      ▶ เล่นทั้งหมด
    </button>
    <button onclick="doNext()"
      style="background:#21262d;color:#c9d1d9;border:1px solid #30363d;
             border-radius:8px;padding:7px 16px;cursor:pointer;font-family:'Sarabun',sans-serif">
      ถัดไป ⏭
    </button>
    <button onclick="doReplay()"
      style="background:#21262d;color:#c9d1d9;border:1px solid #30363d;
             border-radius:8px;padding:7px 16px;cursor:pointer;font-family:'Sarabun',sans-serif">
      🔁 ซ้ำ
    </button>
  </div>
</div>

<script>
var SIGNS = {json.dumps(sign_payload, ensure_ascii=False)};
var cur = 0, playing = false, autoT = null;

(function buildPills(){{
  var row = document.getElementById('pillRow');
  SIGNS.forEach(function(s,i){{
    var p = document.createElement('span');
    p.id = 'pill' + i;
    p.textContent = s.token;
    p.style.cssText = 'padding:4px 11px;border-radius:20px;font-size:.78rem;font-weight:700;'
      + 'border:1px solid #30363d;color:#8b949e;background:#161b22;cursor:pointer;transition:all .2s';
    p.onclick = function(){{ stopAuto(); show(i); }};
    row.appendChild(p);
  }});
}})();

function updatePills(i){{
  SIGNS.forEach(function(_,j){{
    var p = document.getElementById('pill'+j);
    if (!p) return;
    if (j === i)     {{ p.style.background=SIGNS[i].color; p.style.color='#fff'; p.style.borderColor=SIGNS[i].color; }}
    else if (j < i)  {{ p.style.background='#196f3d'; p.style.color='#fff'; p.style.borderColor='#3fb950'; }}
    else             {{ p.style.background='#161b22'; p.style.color='#8b949e'; p.style.borderColor='#30363d'; }}
  }});
}}

function show(i){{
  if (i < 0 || i >= SIGNS.length) return;
  cur = i;
  var s = SIGNS[i];
  document.getElementById('stepLbl').textContent = 'ท่าที่ ' + (i+1) + ' / ' + SIGNS.length;
  document.getElementById('wordLbl').textContent = s.token;
  document.getElementById('player').style.borderColor = s.color;
  document.getElementById('prog').style.width = ((i+1)/SIGNS.length*100) + '%';
  updatePills(i);
  var vid = document.getElementById('vidEl');
  var em  = document.getElementById('emojiEl');
  if (s.type === 'video' && s.b64) {{
    vid.src = 'data:video/mp4;base64,' + s.b64;
    vid.style.display = 'inline-block'; em.style.display = 'none';
    vid.load(); vid.play().catch(function(){{}});
  }} else {{
    em.textContent = s.emoji; em.style.display = 'block'; vid.style.display = 'none';
    vid.pause(); vid.src = '';
  }}
}}

function doNext()  {{ stopAuto(); if(cur < SIGNS.length-1) show(cur+1); }}
function doPrev()  {{ stopAuto(); if(cur > 0) show(cur-1); }}
function doReplay(){{ stopAuto(); show(cur); }}
function selectCard(i) {{ stopAuto(); show(i); }}

function stopAuto(){{
  playing = false; clearTimeout(autoT);
  document.getElementById('btnPlay').textContent = '▶ เล่นทั้งหมด';
  var vid = document.getElementById('vidEl');
  vid.pause();
}}

function togglePlay(){{
  if (playing) {{ stopAuto(); return; }}
  playing = true;
  document.getElementById('btnPlay').textContent = '⏸ หยุด';
  autoAdvance(0);
}}

function autoAdvance(i){{
  if (!playing) return;
  show(i);
  var s = SIGNS[i];
  if (s.type === 'video' && s.b64) {{
    var vid = document.getElementById('vidEl');
    function onEnd(){{
      vid.removeEventListener('ended', onEnd);
      if (!playing) return;
      if (i+1 < SIGNS.length) setTimeout(function(){{ autoAdvance(i+1); }}, 300);
      else stopAuto();
    }}
    vid.addEventListener('ended', onEnd);
  }} else {{
    autoT = setTimeout(function(){{
      if (!playing) return;
      if (i+1 < SIGNS.length) autoAdvance(i+1); else stopAuto();
    }}, 1700);
  }}
}}

show(0);
</script>
</div>
"""
        components.html(player_html, height=780, scrolling=False)

        # Coverage bar
        cov = result["coverage"]
        cc  = "#196f3d" if cov > 0.7 else "#d35400" if cov > 0.4 else "#922b21"
        st.markdown(
            f'<div style="text-align:right;font-size:.82rem;color:{cc}">📊 Sign coverage: '
            f'<b>{cov*100:.0f}%</b> '
            f'({sum(1 for s in result["signs"] if s["found"])}/{len(result["signs"])} คำ)</div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# DICTIONARY VIEWER
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
with st.expander(f"📖 พจนานุกรมภาษามือทั้งหมด ({len(SIGN_DICT)} คำ)"):
    by_cat: dict = {}
    for word, info in SIGN_DICT.items():
        cat = info.get("category","อื่นๆ")
        by_cat.setdefault(cat, []).append((word, info))

    for cat, items in sorted(by_cat.items()):
        color = CAT_COLOR.get(cat, "#95a5a6")
        st.markdown(
            f'<div style="margin:8px 0 4px;padding:4px 10px;border-radius:6px;'
            f'background:{color}22;border-left:4px solid {color};font-weight:700;'
            f'font-size:.85rem;color:{color}">{cat} ({len(items)} คำ)</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(8)
        for i, (word, info) in enumerate(items):
            badge = "🎬" if (SIGN_DIR / info["video"]).exists() else "—"
            with cols[i % 8]:
                st.markdown(
                    f'<div style="background:#eaf4fb;border-radius:10px;padding:7px;'
                    f'text-align:center;margin-bottom:6px;border:1px solid #aed6f1">'
                    f'<div style="font-size:1.3rem">{info["emoji"]}</div>'
                    f'<div style="font-size:.72rem;font-weight:700;color:#1a5276">{word}</div>'
                    f'<div style="font-size:.58rem;color:#7f8c8d">{badge}</div></div>',
                    unsafe_allow_html=True,
                )

st.markdown(
    '<div style="text-align:center;color:#aab7b8;font-size:.75rem">'
    f'Smart Medical Sign Display v5 · Whisper STT · PyThaiNLP · '
    f'{len(SIGN_DICT)} signs · {len(SIMPLIFICATION_RULES)} NLP rules</div>',
    unsafe_allow_html=True,
)