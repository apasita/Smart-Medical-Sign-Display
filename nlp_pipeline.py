"""
nlp_pipeline.py  — v7
======================
Compound-aware Thai Medical Tokenizer + Intent Resolution

สิ่งที่เพิ่มจาก v6:
  1. build_merge_table()   — สร้าง lookup (tok_a, tok_b) → compound อัตโนมัติ
                             จาก SIGN_DICT ทุกคำ  ไม่ต้อง hardcode เลย
  2. merge_compounds()     — pass หลัง tokenize: scan 2-gram / 3-gram
                             แล้ว merge ถ้าผลรวมอยู่ใน SIGN_DICT
  3. Custom Tokenizer      — inject SIGN_DICT + INTENT synonyms เข้า PyThaiNLP corpus
                             ก่อน tokenize เพื่อให้ engine รู้จักคำพ้องทั้งหมด
  4. Digit handling        — digit token แยกอัตโนมัติ,
                             เลขนอก dict แตกเป็นหลักๆ
  5. Intent Resolution     — map_to_signs() ผ่าน intent_data ก่อน
                             "รับประทาน" → intent EAT → sign_key "กิน" → SIGN_DICT["กิน"]
"""

import re
from functools import lru_cache

try:
    from pythainlp.tokenize import word_tokenize, Tokenizer
    from pythainlp.corpus.common import thai_stopwords
    from pythainlp.corpus import thai_words
    _PYTHAINLP = True
except ImportError:
    _PYTHAINLP = False

from sign_data import SIGN_DICT, SIMPLIFICATION_RULES
try:
    from intent_data import get_sign_key, INTENT_DICT
    _INTENT_LOADED = True
except ImportError:
    _INTENT_LOADED = False
    def get_sign_key(word): return None

# ─── Preserve set ─────────────────────────────────────────────────────────────
PRESERVE = {
    "ไม่","ห้าม","ต้อง","ก่อน","หลัง","ระวัง","มาก","น้อย","ได้","ควร",
    "นี้","วัน","ที่","เมื่อ",
}

# ══════════════════════════════════════════════════════════════════════════════
# 1.  MERGE TABLE  — auto-built from SIGN_DICT
# ══════════════════════════════════════════════════════════════════════════════
def build_merge_table() -> dict:
    """
    Return dict  {(part_a, part_b): compound, (p_a, p_b, p_c): compound, ...}

    ทุก compound ใน SIGN_DICT จะถูก split ทุก position แล้วเก็บ:
      'เดือนนี้'  → {('เดือน','นี้'): 'เดือนนี้'}
      'ก่อนอาหาร' → {('ก่อน','อาหาร'): 'ก่อนอาหาร'}
      'หายใจเข้า' → {('หายใจ','เข้า'): 'หายใจเข้า',
                     ('หาย','ใจ','เข้า'): 'หายใจเข้า'}

    ถ้า key เดียวกัน map ไปหลาย compound → เลือก compound ที่ยาวที่สุด
    """
    table: dict = {}
    # เรียงจากยาวไปสั้น เพื่อให้ compound ยาวกว่า override สั้นกว่า
    for compound in sorted(SIGN_DICT, key=len, reverse=True):
        n = len(compound)
        # 2-part
        for i in range(1, n):
            l, r = compound[:i], compound[i:]
            if l and r:
                table.setdefault((l, r), compound)
        # 3-part
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                p1, p2, p3 = compound[:i], compound[i:j], compound[j:]
                if p1 and p2 and p3:
                    table.setdefault((p1, p2, p3), compound)
    return table

_MERGE_TABLE = build_merge_table()


# ══════════════════════════════════════════════════════════════════════════════
# 2.  CUSTOM TOKENIZER  (PyThaiNLP + SIGN_DICT words)
# ══════════════════════════════════════════════════════════════════════════════
@lru_cache(maxsize=1)
def _get_custom_tokenizer():
    """
    Tokenizer ที่รู้จักคำใน SIGN_DICT ทั้งหมด
    cache ไว้เพื่อสร้างครั้งเดียว (~200ms)
    """
    if not _PYTHAINLP:
        return None
    try:
        # เพิ่ม synonym จาก INTENT_DICT เข้า vocab ด้วย
        # เพื่อให้ tokenizer รู้จักคำอย่าง "รับประทาน" แทนที่จะแตกผิด
        synonym_vocab = set()
        if _INTENT_LOADED:
            for info in INTENT_DICT.values():
                synonym_vocab.update(info.get("synonyms", []))
        custom_vocab = set(thai_words()) | set(SIGN_DICT.keys()) | synonym_vocab
        return Tokenizer(custom_vocab, engine="newmm")
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 3.  MERGE PASS
# ══════════════════════════════════════════════════════════════════════════════
def merge_compounds(tokens: list) -> list:
    """
    Greedy left-to-right merge:
      ① ลอง 3-gram ก่อน
      ② ถ้าไม่ได้ ลอง 2-gram
      ③ ถ้าไม่ได้ เก็บ token ปัจจุบัน แล้วเลื่อนไป

    Merge เฉพาะ compound ที่อยู่ใน SIGN_DICT เท่านั้น

    ตัวอย่าง:
      ['เดือน','นี้']          → ['เดือนนี้']
      ['ปวด','หัว']            → ['ปวดหัว']
      ['ก่อน','อาหาร']         → ['ก่อนอาหาร']
      ['วัด','ความ','ดัน']     → ['วัดความดัน']
      ['หาย','ใจ','เข้า']      → ['หายใจเข้า']
    """
    result = []
    i = 0
    while i < len(tokens):
        # try 3-gram
        if i + 2 < len(tokens):
            tri = (tokens[i], tokens[i+1], tokens[i+2])
            if tri in _MERGE_TABLE and _MERGE_TABLE[tri] in SIGN_DICT:
                result.append(_MERGE_TABLE[tri])
                i += 3
                continue
        # try 2-gram
        if i + 1 < len(tokens):
            bi = (tokens[i], tokens[i+1])
            if bi in _MERGE_TABLE and _MERGE_TABLE[bi] in SIGN_DICT:
                result.append(_MERGE_TABLE[bi])
                i += 2
                continue
        result.append(tokens[i])
        i += 1
    return result


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE STAGES
# ══════════════════════════════════════════════════════════════════════════════

def preprocess_text(text: str) -> str:
    text = re.sub(r'["""\'\'\'()\[\]{}<>]', "", text)
    text = re.sub(r"ๆ", "", text)
    return re.sub(r"\s+", " ", text).strip()


def simplify_text(text: str) -> str:
    result = text
    for pattern, replacement in SIMPLIFICATION_RULES:
        result = re.sub(pattern, replacement, result)
    return re.sub(r"\s+", " ", result).strip()


def tokenize_text(text: str) -> list:
    """
    ① แยกตัวเลขเป็น token อิสระ
    ② tokenize ด้วย custom tokenizer (รู้จัก SIGN_DICT)
    ③ กรอง stopword  (คง PRESERVE ไว้)
    ④ merge_compounds()
    """
    # ① digit isolation
    spaced = re.sub(r'(\d+)', r' \1 ', text)
    spaced = re.sub(r'\s+', ' ', spaced).strip()

    if _PYTHAINLP:
        stops = thai_stopwords()
        tokenizer = _get_custom_tokenizer()
        raw = (tokenizer.word_tokenize(spaced)
               if tokenizer
               else word_tokenize(spaced, engine="newmm", keep_whitespace=False))

        filtered = []
        for t in raw:
            t = t.strip()
            if not t:
                continue
            if t.isdigit():
                filtered.append(t)
            elif t not in stops or t in PRESERVE:
                filtered.append(t)

        return merge_compounds(filtered)

    # fallback
    return merge_compounds(_fallback_tokenize(spaced))


def _fallback_tokenize(text: str) -> list:
    """Digit-aware longest-match fallback"""
    tokens = []
    sorted_keys = sorted(SIGN_DICT.keys(), key=len, reverse=True)
    parts = re.split(r'(\d+)', text)
    for part in parts:
        if part.isdigit():
            tokens.append(part)
            continue
        remaining = part
        while remaining:
            matched = False
            for key in sorted_keys:
                if remaining.startswith(key):
                    tokens.append(key)
                    remaining = remaining[len(key):]
                    matched = True
                    break
            if not matched:
                tokens.append(remaining[0])
                remaining = remaining[1:]
    return [t for t in tokens if t.strip()]


def map_to_signs(tokens: list) -> list:
    out = []
    for token in tokens:
        # ① resolve ผ่าน intent ก่อน: "รับประทาน" → sign_key "กิน"
        # ② fallback เป็น token เดิมถ้าไม่พบใน intent_data
        sign_key = get_sign_key(token) or token

        if sign_key in SIGN_DICT:
            out.append({
                "token":    token,               # คำดั้งเดิมจาก speech (แสดงใน UI)
                "emoji":    SIGN_DICT[sign_key]["emoji"],
                "label":    sign_key,            # คำมาตรฐานที่ map กับ sign
                "color":    SIGN_DICT[sign_key]["color"],
                "video":    SIGN_DICT[sign_key]["video"],
                "category": SIGN_DICT[sign_key]["category"],
                "found":    True,
            })
        elif token.isdigit():
            # แตกเลขที่ไม่มีใน dict เป็นหลักๆ
            for digit in token:
                if digit in SIGN_DICT:
                    out.append({
                        "token":    digit,
                        "emoji":    SIGN_DICT[digit]["emoji"],
                        "label":    digit,
                        "color":    SIGN_DICT[digit]["color"],
                        "video":    SIGN_DICT[digit]["video"],
                        "category": SIGN_DICT[digit]["category"],
                        "found":    True,
                    })
                else:
                    out.append({"token": digit, "emoji": "❓", "label": digit,
                                "color": "#95a5a6", "video": None,
                                "category": "unknown", "found": False})
        else:
            out.append({"token": token, "emoji": "❓", "label": token,
                        "color": "#95a5a6", "video": None,
                        "category": "unknown", "found": False})
    return out


def full_pipeline(text: str) -> dict:
    preprocessed = preprocess_text(text)
    simplified   = simplify_text(preprocessed)
    tokens       = tokenize_text(simplified)
    signs        = map_to_signs(tokens)
    n_found      = sum(1 for s in signs if s["found"])
    coverage     = n_found / max(len(signs), 1)
    return {
        "original":     text,
        "preprocessed": preprocessed,
        "simplified":   simplified,
        "tokens":       tokens,
        "signs":        signs,
        "n_signs":      len(signs),
        "n_found":      n_found,
        "coverage":     coverage,
    }


# ─── self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Merge table entries: {len(_MERGE_TABLE)}")
    print()

    compound_tests = [
        ("เดือนนี้",   ["เดือนนี้"]),
        ("วันนี้",     ["วันนี้"]),
        ("พรุ่งนี้",   ["พรุ่งนี้"]),
        ("ก่อนอาหาร",  ["ก่อนอาหาร"]),
        ("หลังอาหาร",  ["หลังอาหาร"]),
        ("ปวดหัว",     ["ปวดหัว"]),
        ("ปวดท้อง",    ["ปวดท้อง"]),
        ("วัดความดัน", ["วัดความดัน"]),
        ("หายใจเข้า",  ["หายใจเข้า"]),
        ("ห้องฉุกเฉิน",["ห้องฉุกเฉิน"]),
        ("ไม่เข้าใจ",  ["ไม่เข้าใจ"]),
    ]
    print("── Compound tokenize ──────────────────────────")
    for text, expected in compound_tests:
        got = tokenize_text(text)
        ok  = "✅" if got == expected else "⚠️ "
        print(f"{ok} {text:18s} → {got}")

    print()
    print("── Full pipeline ──────────────────────────────")
    pipeline_tests = [
        "กินยาก่อนอาหาร 30 นาที",
        "กรุณางดอาหารก่อนเข้ารับการตรวจเดือนนี้",
        "แพทย์จะมาตรวจในตอนเช้าพรุ่งนี้",
        "รับยาที่ช่อง 9 ชั้น 2",
        "ชำระเงินช่อง 8",
        "วัดความดันก่อนอาหารเช้า",
        "ห้องฉุกเฉินชั้น 3",
        "รับประทานยาวันละ 2 ครั้ง หลังอาหาร",
    ]
    for text in pipeline_tests:
        r = full_pipeline(text)
        signs_ok = " ".join(f"{s['emoji']}{s['token']}" for s in r["signs"] if s["found"])
        print(f"\n📝 {r['original']}")
        print(f"   simplify : {r['simplified']}")
        print(f"   tokens   : {r['tokens']}")
        print(f"   signs    : {signs_ok}")
        print(f"   coverage : {r['coverage']*100:.0f}% ({r['n_found']}/{len(r['signs'])})")