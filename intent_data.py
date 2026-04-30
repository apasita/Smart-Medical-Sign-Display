"""
intent_data.py  — v1
=======================
Intent-Based Dictionary สำหรับระบบแปลคำพูดแพทย์ → ภาษามือไทย

แนวคิด:
  แทนที่จะ map "คำ → sign" ตรงๆ
  เราใช้ "คำพ้องความหมาย → intent → คำมาตรฐาน → sign"

  "รับประทาน" ┐
  "ทาน"       ├──→ intent: EAT ──→ canonical: "กิน" ──→ 🤟 sign
  "กิน"       ┘

โครงสร้าง INTENT_DICT:
  {
    "INTENT_NAME": {
        "canonical": str,       # คำมาตรฐานที่ใช้ map กับ SIGN_DICT
        "synonyms": list[str],  # คำพ้องความหมายทั้งหมดที่อาจเจอจาก speech
        "sign_key": str,        # key ที่ตรงกับ SIGN_DICT (อาจต่างจาก canonical)
        "category": str,        # action | symptom | modifier | time | place | person | body | question
        "emoji": str,           # emoji แทน intent นี้ (ใช้แสดง UI)
    }
  }

ใช้งาน:
  from intent_data import INTENT_DICT, SYNONYM_MAP, resolve_intent

  intent = resolve_intent("รับประทาน")   # → "EAT"
  canonical = INTENT_DICT["EAT"]["canonical"]  # → "กิน"
"""

# ══════════════════════════════════════════════════════════════════════════════
# INTENT DICTIONARY  — 52 intents, 8 categories
# ══════════════════════════════════════════════════════════════════════════════

INTENT_DICT: dict = {

    # ─── 🍽️ การกิน / ดื่ม ────────────────────────────────────────────────────
    "EAT": {
        "canonical": "กิน",
        "synonyms": ["รับประทาน", "ทาน", "กิน", "บริโภค", "กลืน",
                     "รับประทานอาหาร", "ทานอาหาร", "กินข้าว"],
        "sign_key": "กิน",
        "category": "action",
        "emoji": "🍽️",
    },
    "DRINK": {
        "canonical": "ดื่ม",
        "synonyms": ["ดื่ม", "ดื่มน้ำ", "รับประทานน้ำ", "กินน้ำ"],
        "sign_key": "ดื่ม",
        "category": "action",
        "emoji": "💧",
    },
    "FAST": {
        "canonical": "งดกิน",
        "synonyms": ["งดอาหาร", "ห้ามกิน", "อดอาหาร", "อดน้ำ", "งดน้ำ",
                     "ไม่กิน", "ไม่ดื่ม", "ห้ามดื่ม", "ห้ามรับประทาน",
                     "งดรับประทาน", "งดทาน"],
        "sign_key": "ไม่กิน",
        "category": "action",
        "emoji": "🚫",
    },
    "MEDICINE": {
        "canonical": "ยา",
        "synonyms": ["ยา", "ยาเม็ด", "ยาน้ำ", "ยาฉีด", "ยาพ่น",
                     "ยาแคปซูล", "ยาครีม", "ยาทา"],
        "sign_key": "ยา",
        "category": "action",
        "emoji": "💊",
    },

    # ─── 🤕 อาการ / ความเจ็บปวด ──────────────────────────────────────────────
    "PAIN": {
        "canonical": "เจ็บ",
        "synonyms": ["ปวด", "เจ็บ", "เจ็บปวด", "รู้สึกปวด",
                     "มีอาการปวด", "เจ็บมาก", "ปวดมาก"],
        "sign_key": "ปวด",
        "category": "symptom",
        "emoji": "😣",
    },
    "FEVER": {
        "canonical": "ไข้",
        "synonyms": ["ไข้", "ตัวร้อน", "มีไข้", "เป็นไข้",
                     "ร้อนตัว", "ตัวร้อนมาก"],
        "sign_key": "ไข้",
        "category": "symptom",
        "emoji": "🤒",
    },
    "NAUSEA": {
        "canonical": "คลื่นไส้",
        "synonyms": ["คลื่นไส้", "คลื่นเหียน", "ไม่สบายท้อง",
                     "อยากอาเจียน", "คลื่นไส้อาเจียน"],
        "sign_key": "คลื่นไส้",
        "category": "symptom",
        "emoji": "🤢",
    },
    "VOMIT": {
        "canonical": "อาเจียน",
        "synonyms": ["อาเจียน", "อ้วก", "สำรอก", "ขย้อน", "อาเจียนออกมา"],
        "sign_key": "อาเจียน",
        "category": "symptom",
        "emoji": "🤮",
    },
    "DIZZY": {
        "canonical": "เวียนหัว",
        "synonyms": ["เวียนหัว", "หัวหมุน", "มึนหัว", "วิงเวียน",
                     "ทรงตัวไม่อยู่", "มึนงง"],
        "sign_key": "เวียนหัว",
        "category": "symptom",
        "emoji": "😵",
    },
    "COUGH": {
        "canonical": "ไอ",
        "synonyms": ["ไอ", "ไอมาก", "ไอแห้ง", "ไอมีเสมหะ",
                     "ไอเรื้อรัง", "ไอบ่อย"],
        "sign_key": "ไอ",
        "category": "symptom",
        "emoji": "🤧",
    },
    "BLEED": {
        "canonical": "เลือดออก",
        "synonyms": ["เลือดออก", "มีเลือด", "เลือดไหล", "เลือดซึม",
                     "มีเลือดออก"],
        "sign_key": "เลือดออก",
        "category": "symptom",
        "emoji": "🩸",
    },
    "SWELLING": {
        "canonical": "บวม",
        "synonyms": ["บวม", "อักเสบ", "บวมแดง", "บวมช้ำ",
                     "บวมขึ้น", "มีการอักเสบ"],
        "sign_key": "บวม",
        "category": "symptom",
        "emoji": "🫧",
    },
    "ITCH": {
        "canonical": "คัน",
        "synonyms": ["คัน", "ระคายเคือง", "แสบ", "คันมาก",
                     "แสบคัน", "ผื่นคัน"],
        "sign_key": "คัน",
        "category": "symptom",
        "emoji": "😖",
    },
    "BREATHE": {
        "canonical": "หายใจ",
        "synonyms": ["หายใจ", "หอบ", "หายใจไม่ออก", "หายใจลำบาก",
                     "แน่นหน้าอก", "หายใจเหนื่อย", "เหนื่อยหอบ"],
        "sign_key": "หายใจ",
        "category": "symptom",
        "emoji": "😮‍💨",
    },

    # ─── 🏥 การตรวจ / รักษา ──────────────────────────────────────────────────
    "EXAMINE": {
        "canonical": "ตรวจ",
        "synonyms": ["ตรวจ", "วินิจฉัย", "ตรวจร่างกาย", "ตรวจสุขภาพ",
                     "รับการตรวจ", "เข้ารับการตรวจ"],
        "sign_key": "ตรวจ",
        "category": "action",
        "emoji": "🔍",
    },
    "BLOOD_TEST": {
        "canonical": "เจาะเลือด",
        "synonyms": ["เจาะเลือด", "ตรวจเลือด", "เก็บตัวอย่างเลือด",
                     "ตรวจเลือดออก", "เจาะเลือดตรวจ"],
        "sign_key": "เจาะเลือด",
        "category": "action",
        "emoji": "🩸",
    },
    "SURGERY": {
        "canonical": "ผ่าตัด",
        "synonyms": ["ผ่าตัด", "ทำการผ่าตัด", "รับการผ่าตัด",
                     "เข้าผ่าตัด"],
        "sign_key": "ผ่าตัด",
        "category": "action",
        "emoji": "🔪",
    },
    "XRAY": {
        "canonical": "เอกซเรย์",
        "synonyms": ["เอกซเรย์", "ฉายแสง", "ถ่ายภาพรังสี", "สแกน",
                     "CT", "MRI", "อัลตราซาวด์", "ตรวจภาพ"],
        "sign_key": "เอกซเรย์",
        "category": "action",
        "emoji": "🩻",
    },
    "MEASURE_BP": {
        "canonical": "วัดความดัน",
        "synonyms": ["วัดความดัน", "เช็คความดัน", "ตรวจความดัน",
                     "วัดความดันโลหิต", "ตรวจวัดความดัน"],
        "sign_key": "วัดความดัน",
        "category": "action",
        "emoji": "🩺",
    },
    "INJECT": {
        "canonical": "ฉีดยา",
        "synonyms": ["ฉีดยา", "ให้ยา", "น้ำเกลือ", "ฉีดวัคซีน",
                     "ให้น้ำเกลือ", "ฉีดยาเข้าเส้น"],
        "sign_key": "ฉีดยา",
        "category": "action",
        "emoji": "💉",
    },
    "REST": {
        "canonical": "นอนพัก",
        "synonyms": ["นอนพัก", "พักผ่อน", "นอนหลับ", "นอน",
                     "นอนพักผ่อน", "พักกาย", "นอนให้เพียงพอ"],
        "sign_key": "นอน",
        "category": "action",
        "emoji": "😴",
    },
    "WAIT": {
        "canonical": "รอ",
        "synonyms": ["รอ", "นั่งรอ", "รอก่อน", "รอสักครู่",
                     "กรุณารอ", "โปรดรอ", "รอที่นั่ง"],
        "sign_key": "รอ",
        "category": "action",
        "emoji": "⏳",
    },
    "COME_BACK": {
        "canonical": "นัด",
        "synonyms": ["นัด", "นัดหมาย", "นัดตรวจ", "มาใหม่",
                     "กลับมา", "นัดพบ", "นัดครั้งถัดไป"],
        "sign_key": "นัด",
        "category": "action",
        "emoji": "📅",
    },
    "PAY": {
        "canonical": "ชำระเงิน",
        "synonyms": ["ชำระเงิน", "จ่ายเงิน", "ชำระค่ารักษา",
                     "เก็บเงิน", "จ่ายค่าบริการ", "ชำระค่าบริการ"],
        "sign_key": "ชำระเงิน",
        "category": "action",
        "emoji": "💳",
    },
    "WALK": {
        "canonical": "เดิน",
        "synonyms": ["เดิน", "เดินได้", "ลุกเดิน", "ออกกำลังกาย",
                     "ขยับร่างกาย"],
        "sign_key": "เดิน",
        "category": "action",
        "emoji": "🚶",
    },
    "TELL": {
        "canonical": "บอก",
        "synonyms": ["บอก", "แจ้ง", "บอกให้ทราบ", "แจ้งให้ทราบ",
                     "โปรดแจ้ง", "กรุณาแจ้ง"],
        "sign_key": "บอก",
        "category": "action",
        "emoji": "📢",
    },
    "UNDERSTAND": {
        "canonical": "เข้าใจ",
        "synonyms": ["เข้าใจ", "ไม่เข้าใจ", "เข้าใจไหม", "เข้าใจมั้ย",
                     "ทำความเข้าใจ"],
        "sign_key": "เข้าใจ",
        "category": "action",
        "emoji": "💡",
    },
    "RECEIVE_MED": {
        "canonical": "รับยา",
        "synonyms": ["รับยา", "ไปรับยา", "รับยาที่ห้องยา",
                     "รับยาที่เภสัช", "ไปรับยาได้เลย"],
        "sign_key": "รับยา",
        "category": "action",
        "emoji": "💊",
    },

    # ─── 🧍 ส่วนของร่างกาย ───────────────────────────────────────────────────
    "HEAD": {
        "canonical": "หัว",
        "synonyms": ["หัว", "ศีรษะ", "ขมับ", "หน้าผาก", "กะโหลก"],
        "sign_key": "หัว",
        "category": "body",
        "emoji": "🗣️",
    },
    "CHEST": {
        "canonical": "หน้าอก",
        "synonyms": ["หน้าอก", "ทรวงอก", "อก", "ซี่โครง", "แน่นอก"],
        "sign_key": "หน้าอก",
        "category": "body",
        "emoji": "🫁",
    },
    "STOMACH": {
        "canonical": "ท้อง",
        "synonyms": ["ท้อง", "กระเพาะ", "ช่องท้อง", "ลำไส้",
                     "กระเพาะอาหาร", "ท้องน้อย"],
        "sign_key": "ท้อง",
        "category": "body",
        "emoji": "🫃",
    },
    "BACK": {
        "canonical": "หลัง",
        "synonyms": ["หลัง", "บั้นหลัง", "กระดูกสันหลัง",
                     "เอว", "บั้นเอว"],
        "sign_key": "หลัง",
        "category": "body",
        "emoji": "🦴",
    },
    "ARM": {
        "canonical": "แขน",
        "synonyms": ["แขน", "ข้อมือ", "ข้อศอก", "ไหล่", "นิ้วมือ"],
        "sign_key": "แขน",
        "category": "body",
        "emoji": "💪",
    },
    "LEG": {
        "canonical": "ขา",
        "synonyms": ["ขา", "เท้า", "เข่า", "ต้นขา", "ข้อเท้า",
                     "นิ้วเท้า", "หน้าแข้ง"],
        "sign_key": "ขา",
        "category": "body",
        "emoji": "🦵",
    },
    "BLOOD": {
        "canonical": "เลือด",
        "synonyms": ["เลือด", "ตัวอย่างเลือด", "หมู่เลือด",
                     "ตรวจเลือด"],
        "sign_key": "เลือด",
        "category": "body",
        "emoji": "🩸",
    },
    "HEART": {
        "canonical": "หัวใจ",
        "synonyms": ["หัวใจ", "ใจสั่น", "หัวใจเต้นแรง",
                     "หัวใจวาย", "กล้ามเนื้อหัวใจ"],
        "sign_key": "หัวใจ",
        "category": "body",
        "emoji": "❤️",
    },

    # ─── ⏰ เวลา ───────────────────────────────────────────────────────────────
    "MORNING": {
        "canonical": "เช้า",
        "synonyms": ["เช้า", "ตอนเช้า", "เช้าตรู่", "หลังตื่นนอน",
                     "เช้าๆ"],
        "sign_key": "เช้า",
        "category": "time",
        "emoji": "🌅",
    },
    "EVENING": {
        "canonical": "เย็น",
        "synonyms": ["เย็น", "ตอนเย็น", "บ่าย", "หลังเลิกงาน",
                     "ช่วงเย็น"],
        "sign_key": "เย็น",
        "category": "time",
        "emoji": "🌆",
    },
    "NIGHT": {
        "canonical": "กลางคืน",
        "synonyms": ["กลางคืน", "คืน", "ก่อนนอน", "ตอนกลางคืน",
                     "เที่ยงคืน", "ดึก"],
        "sign_key": "คืน",
        "category": "time",
        "emoji": "🌙",
    },
    "BEFORE": {
        "canonical": "ก่อน",
        "synonyms": ["ก่อน", "ก่อนอาหาร", "ก่อนนอน", "ก่อนตรวจ",
                     "ก่อนกิน"],
        "sign_key": "ก่อน",
        "category": "time",
        "emoji": "⬅️",
    },
    "AFTER": {
        "canonical": "หลัง",
        "synonyms": ["หลัง", "หลังอาหาร", "หลังตรวจ", "หลังผ่าตัด",
                     "หลังกิน", "หลังรับยา"],
        "sign_key": "หลัง",
        "category": "time",
        "emoji": "➡️",
    },
    "DAILY": {
        "canonical": "ทุกวัน",
        "synonyms": ["ทุกวัน", "วันละ", "ทุกๆวัน", "ต่อวัน",
                     "ต่อวันละ"],
        "sign_key": "ทุกวัน",
        "category": "time",
        "emoji": "📆",
    },
    "TOMORROW": {
        "canonical": "พรุ่งนี้",
        "synonyms": ["พรุ่งนี้", "วันพรุ่งนี้", "วันถัดไป",
                     "วันหน้า"],
        "sign_key": "พรุ่งนี้",
        "category": "time",
        "emoji": "📅",
    },
    "TODAY": {
        "canonical": "วันนี้",
        "synonyms": ["วันนี้", "เดี๋ยวนี้", "ตอนนี้", "ขณะนี้"],
        "sign_key": "วันนี้",
        "category": "time",
        "emoji": "📅",
    },

    # ─── 📍 สถานที่ ────────────────────────────────────────────────────────────
    "EXAM_ROOM": {
        "canonical": "ห้องตรวจ",
        "synonyms": ["ห้องตรวจ", "ห้องหมอ", "คลินิก",
                     "ห้องตรวจโรค", "ห้องตรวจผู้ป่วย"],
        "sign_key": "ห้องตรวจ",
        "category": "place",
        "emoji": "🏥",
    },
    "ER": {
        "canonical": "ห้องฉุกเฉิน",
        "synonyms": ["ห้องฉุกเฉิน", "ER", "อุบัติเหตุฉุกเฉิน",
                     "ห้องอุบัติเหตุ", "แผนกฉุกเฉิน"],
        "sign_key": "ห้องฉุกเฉิน",
        "category": "place",
        "emoji": "🚨",
    },
    "PHARMACY": {
        "canonical": "ห้องยา",
        "synonyms": ["ร้านยา", "ห้องยา", "แผนกเภสัช", "รับยา",
                     "ห้องรับยา"],
        "sign_key": "ห้องยา",
        "category": "place",
        "emoji": "💊",
    },
    "TOILET": {
        "canonical": "ห้องน้ำ",
        "synonyms": ["ห้องน้ำ", "ส้วม", "โถส้วม", "ห้องสุขา"],
        "sign_key": "ห้องน้ำ",
        "category": "place",
        "emoji": "🚻",
    },
    "FLOOR": {
        "canonical": "ชั้น",
        "synonyms": ["ชั้น", "ชั้นที่", "ชั้น 1", "ชั้น 2",
                     "ชั้น 3", "ชั้น 4", "ชั้น 5"],
        "sign_key": "ชั้น",
        "category": "place",
        "emoji": "🏢",
    },
    "COUNTER": {
        "canonical": "ช่อง",
        "synonyms": ["ช่อง", "เคาน์เตอร์", "ช่องที่", "ช่องรับยา",
                     "ช่องชำระเงิน"],
        "sign_key": "ช่อง",
        "category": "place",
        "emoji": "🪟",
    },

    # ─── 👨‍⚕️ บุคคล ──────────────────────────────────────────────────────────
    "DOCTOR": {
        "canonical": "หมอ",
        "synonyms": ["หมอ", "แพทย์", "นายแพทย์", "คุณหมอ",
                     "แพทยศาสตร์"],
        "sign_key": "หมอ",
        "category": "person",
        "emoji": "👨‍⚕️",
    },
    "NURSE": {
        "canonical": "พยาบาล",
        "synonyms": ["พยาบาล", "เจ้าหน้าที่", "พยาบาลวิชาชีพ",
                     "นางพยาบาล", "พยาบาลห้องตรวจ"],
        "sign_key": "พยาบาล",
        "category": "person",
        "emoji": "👩‍⚕️",
    },
    "PHARMACIST": {
        "canonical": "เภสัช",
        "synonyms": ["เภสัช", "เภสัชกร", "คนจ่ายยา",
                     "เจ้าหน้าที่ห้องยา"],
        "sign_key": "เภสัช",
        "category": "person",
        "emoji": "🧑‍🔬",
    },
    "PATIENT": {
        "canonical": "คนไข้",
        "synonyms": ["คนไข้", "ผู้ป่วย", "คุณ", "ท่าน"],
        "sign_key": "คนไข้",
        "category": "person",
        "emoji": "🧑",
    },

    # ─── 🚦 Modifier / คำสั่ง ────────────────────────────────────────────────
    "MUST": {
        "canonical": "ต้อง",
        "synonyms": ["ต้อง", "จำเป็นต้อง", "ควรต้อง", "บังคับ",
                     "จะต้อง"],
        "sign_key": "ต้อง",
        "category": "modifier",
        "emoji": "✅",
    },
    "FORBID": {
        "canonical": "ห้าม",
        "synonyms": ["ห้าม", "ไม่ให้", "ห้ามทำ", "อย่า", "งด",
                     "ห้ามเด็ดขาด"],
        "sign_key": "ห้าม",
        "category": "modifier",
        "emoji": "🚫",
    },
    "SHOULD": {
        "canonical": "ควร",
        "synonyms": ["ควร", "ควรจะ", "น่าจะ", "แนะนำให้",
                     "ควรจะต้อง"],
        "sign_key": "ควร",
        "category": "modifier",
        "emoji": "💬",
    },
    "NOT": {
        "canonical": "ไม่",
        "synonyms": ["ไม่", "ไม่ใช่", "ไม่ได้", "ไม่มี",
                     "ไม่เป็น"],
        "sign_key": "ไม่",
        "category": "modifier",
        "emoji": "❌",
    },
    "CAUTION": {
        "canonical": "ระวัง",
        "synonyms": ["ระวัง", "ระมัดระวัง", "โปรดระวัง",
                     "ระวังด้วย", "ระวังนะ"],
        "sign_key": "ระวัง",
        "category": "modifier",
        "emoji": "⚠️",
    },
    "MORE": {
        "canonical": "มาก",
        "synonyms": ["มาก", "เยอะ", "มากขึ้น", "เพิ่ม",
                     "มากๆ"],
        "sign_key": "มาก",
        "category": "modifier",
        "emoji": "⬆️",
    },
    "LESS": {
        "canonical": "น้อย",
        "synonyms": ["น้อย", "ลด", "น้อยลง", "ลดลง",
                     "น้อยๆ"],
        "sign_key": "น้อย",
        "category": "modifier",
        "emoji": "⬇️",
    },
    "URGENT": {
        "canonical": "ด่วน",
        "synonyms": ["ด่วน", "รีบ", "ฉุกเฉิน", "เร่งด่วน",
                     "รีบด่วน", "ต้องรีบ"],
        "sign_key": "ด่วน",
        "category": "modifier",
        "emoji": "🚨",
    },

    # ─── ❓ คำถาม ─────────────────────────────────────────────────────────────
    "ASK_WHERE": {
        "canonical": "ที่ไหน",
        "synonyms": ["ที่ไหน", "ตรงไหน", "แห่งไหน", "ด้านไหน",
                     "อยู่ที่ไหน"],
        "sign_key": "ที่ไหน",
        "category": "question",
        "emoji": "📍",
    },
    "ASK_WHEN": {
        "canonical": "เมื่อไร",
        "synonyms": ["เมื่อไร", "กี่โมง", "วันไหน", "เวลาไหน",
                     "ช่วงไหน"],
        "sign_key": "เมื่อไร",
        "category": "question",
        "emoji": "🕐",
    },
    "ASK_HOW": {
        "canonical": "อย่างไร",
        "synonyms": ["อย่างไร", "ยังไง", "วิธีไหน", "แบบไหน",
                     "ทำอย่างไร"],
        "sign_key": "อย่างไร",
        "category": "question",
        "emoji": "❓",
    },
    "ASK_PAIN_LOC": {
        "canonical": "ปวดตรงไหน",
        "synonyms": ["ปวดตรงไหน", "เจ็บตรงไหน", "เจ็บจุดไหน",
                     "ปวดที่ไหน", "เจ็บที่ไหน"],
        "sign_key": "ปวดตรงไหน",
        "category": "question",
        "emoji": "😣",
    },
    "ASK_ALLERGY": {
        "canonical": "แพ้ยา",
        "synonyms": ["แพ้ยา", "แพ้อะไร", "มีอาการแพ้ไหม",
                     "ประวัติแพ้ยา", "แพ้ยาอะไร"],
        "sign_key": "แพ้ยา",
        "category": "question",
        "emoji": "⚠️",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# SYNONYM MAP  — auto-built reverse lookup: synonym → intent_name
# ══════════════════════════════════════════════════════════════════════════════

def _build_synonym_map() -> dict:
    """
    สร้าง reverse lookup: คำพ้อง → ชื่อ intent
    ถ้าคำซ้ำกันหลาย intent → เลือก intent แรกที่เจอ (ตามลำดับใน INTENT_DICT)
    """
    mapping: dict = {}
    for intent_name, info in INTENT_DICT.items():
        for syn in info["synonyms"]:
            mapping.setdefault(syn, intent_name)
        # canonical ก็ map ด้วย
        mapping.setdefault(info["canonical"], intent_name)
    return mapping

SYNONYM_MAP: dict = _build_synonym_map()


# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def resolve_intent(word: str) -> str | None:
    """
    รับคำ → คืน intent name (หรือ None ถ้าไม่พบ)

    ตัวอย่าง:
      resolve_intent("รับประทาน")  → "EAT"
      resolve_intent("ตัวร้อน")   → "FEVER"
      resolve_intent("เอกซเรย์")  → "XRAY"
      resolve_intent("xyz")       → None
    """
    return SYNONYM_MAP.get(word)


def get_canonical(word: str) -> str | None:
    """
    รับคำ → คืนคำมาตรฐาน (หรือ None)

    ตัวอย่าง:
      get_canonical("รับประทาน")  → "กิน"
      get_canonical("ตัวร้อน")   → "ไข้"
    """
    intent = resolve_intent(word)
    if intent:
        return INTENT_DICT[intent]["canonical"]
    return None


def get_sign_key(word: str) -> str | None:
    """
    รับคำ → คืน sign_key สำหรับ lookup ใน SIGN_DICT

    ตัวอย่าง:
      get_sign_key("รับประทาน")  → "กิน"
      get_sign_key("อ้วก")      → "อาเจียน"
    """
    intent = resolve_intent(word)
    if intent:
        return INTENT_DICT[intent]["sign_key"]
    return None


def normalize_tokens(tokens: list[str]) -> list[str]:
    """
    แปลง tokens list ให้เป็น canonical form ทั้งหมด

    ตัวอย่าง:
      normalize_tokens(["รับประทาน","ยา","ก่อน","อาหาร"])
      → ["กิน", "ยา", "ก่อน", "อาหาร"]
    """
    return [get_canonical(t) or t for t in tokens]


def get_intents_by_category(category: str) -> dict:
    """
    คืน subset ของ INTENT_DICT ที่อยู่ใน category ที่กำหนด

    ตัวอย่าง:
      get_intents_by_category("symptom")
    """
    return {k: v for k, v in INTENT_DICT.items() if v["category"] == category}


def summary() -> None:
    """พิมพ์สรุปจำนวน intent และ synonym"""
    from collections import Counter
    cats = Counter(v["category"] for v in INTENT_DICT.values())
    n_syns = sum(len(v["synonyms"]) for v in INTENT_DICT.values())
    print(f"Intent Dictionary Summary")
    print(f"  Total intents : {len(INTENT_DICT)}")
    print(f"  Total synonyms: {n_syns}")
    print(f"  Synonym map   : {len(SYNONYM_MAP)} entries")
    print()
    for cat, count in sorted(cats.items()):
        print(f"  {cat:12s}: {count} intents")


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    summary()
    print()

    tests = [
        ("รับประทาน",  "กิน",       "EAT"),
        ("ทาน",        "กิน",       "EAT"),
        ("ตัวร้อน",    "ไข้",       "FEVER"),
        ("อ้วก",       "อาเจียน",   "VOMIT"),
        ("แพทย์",      "หมอ",       "DOCTOR"),
        ("นั่งรอ",     "รอ",        "WAIT"),
        ("งดอาหาร",    "งดกิน",     "FAST"),
        ("เจ็บตรงไหน", "ปวดตรงไหน", "ASK_PAIN_LOC"),
        ("CT",         "เอกซเรย์",  "XRAY"),
        ("xxx",        None,         None),
    ]

    print(f"{'Input':20s} {'Canonical':15s} {'Intent':20s} {'OK'}")
    print("─" * 62)
    for word, exp_canonical, exp_intent in tests:
        got_intent    = resolve_intent(word)
        got_canonical = get_canonical(word)
        ok = "✅" if got_intent == exp_intent and got_canonical == exp_canonical else "❌"
        print(f"{word:20s} {str(got_canonical):15s} {str(got_intent):20s} {ok}")