from google import genai
import os
import json
import time
import pdfplumber
import pandas as pd
from docx import Document

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


MODEL_CANDIDATES = [
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3.8-flash",
]

_working_model = {"name": None}


def extract_text(file_path):
    if file_path.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    elif file_path.endswith(".docx"):
        doc = Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)
    elif file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError("Unsupported file type. Sirf .pdf, .docx, ya .txt chalega.")


def chunk_text(text, max_words=800):
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        chunks.append(chunk)
    return chunks


def _call_model(prompt, retries=3):
    """Pehle jo model pehle kaam kar chuka hai wahi try karta hai,
    warna list me se ek-ek karke try karta hai jab tak koi kaam na kare."""
    models_to_try = [_working_model["name"]] if _working_model["name"] else MODEL_CANDIDATES

    last_error = None
    for model_name in models_to_try:
        for attempt in range(retries):
            try:
                interaction = client.interactions.create(model=model_name, input=prompt)
                _working_model["name"] = model_name  # ye model kaam kar gaya, yaad rakho
                return _parse_json(interaction.output_text)
            except Exception as e:
                last_error = e
                if "429" in str(e) or "RateLimit" in str(e):
                    wait = 20 * (attempt + 1)
                    print(f"  Rate limit hit on {model_name}, {wait}s wait...")
                    time.sleep(wait)
                elif "404" in str(e) or "NotFound" in str(e):
                    print(f"  {model_name} available nahi hai, agla model try kar rahe hai...")
                    break  # is model ko chodo, list ka agla model try karo
                else:
                    raise

    raise RuntimeError(f"Koi bhi model kaam nahi kiya. Last error: {last_error}")


def generate_qna(chunk, n_pairs=5):
    prompt = f"""Read the passage below carefully and generate {n_pairs}
context-aware question-answer pairs based only on its content.

Return ONLY a valid JSON array, no extra text, no markdown formatting.
Format: [{{"question": "...", "answer": "..."}}, ...]

Passage:
\"\"\"{chunk}\"\"\"
"""
    return _call_model(prompt)


def translate_pairs(pairs, target_lang):
    prompt = f"""Translate the "question" and "answer" values below into {target_lang}.
Write the translation using {target_lang}'s native script (not English, not transliteration).
Keep the exact same JSON structure with keys "question" and "answer", same number of items, same order.
Return ONLY a valid JSON array, no extra text, no markdown formatting.

{json.dumps(pairs, ensure_ascii=False)}
"""
    return _call_model(prompt)


def _parse_json(raw_text):
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json", "", 1).strip()
    return json.loads(raw_text)


def export_to_excel(en_pairs, hi_pairs, mr_pairs, out_path="Multilingual_QnA.xlsx"):
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        pd.DataFrame(en_pairs).rename(
            columns={"question": "Questions", "answer": "Answers"}
        ).to_excel(writer, sheet_name="English", index=False)
        pd.DataFrame(hi_pairs).rename(
            columns={"question": "Questions", "answer": "Answers"}
        ).to_excel(writer, sheet_name="Hindi", index=False)
        pd.DataFrame(mr_pairs).rename(
            columns={"question": "Questions", "answer": "Answers"}
        ).to_excel(writer, sheet_name="Marathi", index=False)
    return out_path
