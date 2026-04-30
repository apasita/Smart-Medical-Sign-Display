# 🏥 Smart Medical Sign Display System

> **University NLP Project** — Converting Spoken Medical Thai Instructions  
> into Simplified Text and Sign Language Representation

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://smart-medical-sign-display-hmswyi5mwjwux5mmdgyoan.streamlit.app/)
---

## 📋 Table of Contents

1. [Project Overview](#overview)
2. [System Architecture](#architecture)
3. [NLP Pipeline](#pipeline)
4. [Installation](#installation)
5. [Running the App](#running)
6. [File Structure](#files)
7. [Academic Analysis](#academic)
8. [Limitations](#limitations)
9. [Future Extensions](#future)

---

## Project Overview <a name="overview"></a>

This system assists **hearing-impaired patients** in hospitals by converting spoken medical instructions from doctors into:

| Output | Description |
|--------|-------------|
| 📝 Original Thai text | Exact transcription from audio |
| ✅ Simplified Thai text | Plain, easy-to-understand language |
| 🤟 Sign Language representation | Emoji/image sequence for each key word |

**Target Users:** Hearing-impaired patients in Thai hospitals  
**Use Case:** Tablet screen facing the patient at a consultation desk

---

## System Architecture <a name="architecture"></a>

```
┌─────────────────────────────────────────────────────────────┐
│                    System Pipeline                          │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│  Audio   │ Whisper  │  Pre-    │   NLP    │ Sign Mapping   │
│  Input   │  STT     │ process  │ Simplify │ + UI Display   │
│ (.wav)   │          │          │          │                │
└──────────┴──────────┴──────────┴──────────┴────────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Speech Recognition | OpenAI Whisper (base) | Thai audio → raw text |
| Preprocessing | Python regex | Noise removal, normalization |
| Simplification | Rule-based NLP (regex) | Formal→plain Thai |
| Tokenization | PyThaiNLP (newmm) | Word segmentation |
| Sign Mapping | Dictionary lookup | Words → sign icons |
| UI | Streamlit | Tablet-friendly display |

---

## NLP Pipeline <a name="pipeline"></a>

### Stage 1 — Speech-to-Text

```python
model = whisper.load_model("base")
result = model.transcribe(audio_path, language="th")
text = result["text"]
```

Whisper's multilingual model handles Thai speech without any Thai-specific fine-tuning.

### Stage 2 — Text Preprocessing

- Remove punctuation that doesn't carry meaning
- Collapse whitespace
- Normalize Unicode variants

### Stage 3 — Rule-based Simplification

30+ ordered regex substitution rules targeting:

| Rule Category | Example |
|---------------|---------|
| Polite openers | `กรุณา` → *(removed)* |
| Medical verbs | `งดอาหาร` → `ไม่กิน` |
| Medical nouns | `แพทย์` → `หมอ` |
| Dosage patterns | `วันละ 2 ครั้ง` → `2 ครั้งต่อวัน` |

**Why rule-based?**
- ✅ Fully explainable — every transformation is a readable rule
- ✅ No training data required
- ✅ Domain experts (doctors/nurses) can extend rules directly
- ✅ Deterministic output

### Stage 4 — Tokenization

Uses **PyThaiNLP newmm** (New Maximum Matching), a dictionary-based algorithm that:
1. Loads Thai word dictionary
2. Applies forward maximal matching
3. Handles ambiguity with dictionary priority

### Stage 5 — Sign Mapping

Dictionary lookup: `simplified_word → {emoji, label, category}`

Dictionary covers 45+ words across 6 categories:
- Negation/Modifiers
- Actions
- Medical/Body
- Time expressions
- Objects
- Instructions/Safety

---

## Installation <a name="installation"></a>

### Local / Standard Python

```bash
git clone <repo-url>
cd smart_medical_sign
pip install -r requirements.txt
```

## ⬇️ ดาวน์โหลดไฟล์วิดีโอภาษามือ
ดาวน์โหลด signs.zip แล้วแตกไฟล์ไว้ในโฟลเดอร์โปรเจค:
👉 [ดาวน์โหลด signs.zip]([CLick link](https://drive.google.com/file/d/1aVyyFPBJ-XoKGV5bYMKQFPEWtwH4m4D9/view))

### Google Colab

```python
!pip install openai-whisper pythainlp streamlit -q
```

### Requirements

```
streamlit>=1.30.0
openai-whisper>=20231117
pythainlp>=4.0.2
torch>=2.0.0
pydub>=0.25.1
```

---

## Running the App <a name="running"></a>

### Streamlit UI

```bash
streamlit run app.py
```

Open browser at `http://localhost:8501`

### Colab Notebook

1. Open `Smart_Medical_Sign_Colab.ipynb` in Google Colab
2. Run all cells in order
3. For Streamlit in Colab:

```python
!pip install pyngrok -q
from pyngrok import ngrok
ngrok.set_auth_token("YOUR_NGROK_TOKEN")
!streamlit run app.py &
public_url = ngrok.connect(8501)
print(public_url)
```

### Pipeline-only (no UI)

```python
from nlp_pipeline import full_pipeline
result = full_pipeline("กรุณางดอาหารก่อนเข้ารับการตรวจ")
print(result["simplified"])  # ไม่กินก่อนตรวจ
```

---

## File Structure <a name="files"></a>

```
smart_medical_sign/
├── app.py                          # Streamlit UI (main entry point)
├── nlp_pipeline.py                 # NLP logic (importable module)
├── requirements.txt                # Python dependencies
├── sample_dataset.json             # 12 sample medical sentences
├── Smart_Medical_Sign_Colab.ipynb  # Google Colab notebook
├── sign_images/                    # (Optional) real sign images
│   ├── กิน.png
│   ├── ไม่.png
│   └── ...
└── README.md                       # This file
```

---

## Academic Analysis <a name="academic"></a>

### NLP Justification

This project demonstrates four core NLP concepts:

1. **Text Normalization** — removing formal register, standardizing vocabulary
2. **Tokenization** — segmenting Thai text (no spaces between words)
3. **Lexical Simplification** — replacing complex words with simpler synonyms
4. **Information Extraction** — identifying key semantic content for sign mapping

### Evaluation Metrics

| Metric | Method |
|--------|--------|
| Simplification quality | Manual human evaluation (Likert scale 1–5) |
| Sign coverage | `n_matched_tokens / n_total_tokens` |
| STT accuracy | Word Error Rate (WER) vs manual transcription |

### Dataset

12 sample sentences across 6 clinical categories:
- การตรวจ (Examination) — 3 sentences
- ยา (Medication) — 2 sentences
- การพักผ่อน (Rest) — 2 sentences
- การตรวจเลือด (Blood test) — 1 sentence
- การรอ (Waiting) — 1 sentence
- การนัดหมาย (Appointment) — 1 sentence
- การสื่อสาร (Communication) — 1 sentence
- ความปลอดภัย (Safety) — 1 sentence

---

## Limitations <a name="limitations"></a>

1. **Dictionary coverage** — OOV (out-of-vocabulary) words cannot be mapped to signs
2. **Rule-based brittleness** — unusual sentence structures may not match any rule
3. **No sign animation** — current output is emoji only, not real Thai Sign Language (TSL)
4. **STT accuracy** — Whisper may struggle with medical terminology or thick accents
5. **No context awareness** — the same word may need different signs in different contexts
6. **Single-speaker assumption** — pipeline assumes the doctor speaks one instruction at a time

---

## Future Extensions <a name="future"></a>

| Extension | Impact | Complexity |
|-----------|--------|------------|
| Neural simplification (mBART, Thai-BART) | Higher | High |
| Real TSL video clips per word | Higher | Medium |
| Real-time microphone input (WebRTC) | High | Medium |
| LLM-powered simplification (GPT/Claude API) | Higher | Low |
| Expand dictionary to 500+ medical words | High | Low |
| Multi-language support (English, Burmese) | Medium | Medium |
| Patient feedback collection | Medium | Low |
| Text-to-speech output for visually impaired | Medium | Low |

---

## References

- OpenAI Whisper: https://github.com/openai/whisper
- PyThaiNLP: https://github.com/PyThaiNLP/pythainlp
- Thai Sign Language Reference: https://www.nso.go.th
- Streamlit: https://streamlit.io

---

*Smart Medical Sign Display System — University NLP Project — 2024*
