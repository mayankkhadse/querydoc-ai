import streamlit as st
import os

if "GEMINI_API_KEY" not in os.environ and hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

from qna_generator import extract_text, chunk_text, generate_qna, translate_pairs, export_to_excel

st.set_page_config(page_title="QueryDoc AI", page_icon="🧠", layout="centered")

st.markdown("""
<style>
    .main .block-container {
        padding-top: 3rem;
        max-width: 850px;
    }

    .app-header {
        text-align: center;
        padding: 2rem 1rem 2.5rem 1rem;
        margin-bottom: 1.5rem;
        border-radius: 20px;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        box-shadow: 0 8px 32px rgba(108, 99, 255, 0.15);
    }

    .app-title {
        font-size: 3.2rem;
        font-weight: 800;
        margin: 0;
        background: linear-gradient(90deg, #6C63FF, #B892FF, #6C63FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -1px;
    }

    .app-subtitle {
        color: #a0a0b8;
        font-size: 1.15rem;
        margin-top: 0.6rem;
        font-weight: 400;
    }

    .stButton>button {
        background: linear-gradient(90deg, #6C63FF, #8b7dff);
        color: white;
        font-weight: 600;
        font-size: 1.05rem;
        border: none;
        border-radius: 10px;
        padding: 0.7rem 1.4rem;
        box-shadow: 0 4px 14px rgba(108, 99, 255, 0.35);
        transition: all 0.2s ease;
    }

    .stButton>button:hover {
        box-shadow: 0 6px 20px rgba(108, 99, 255, 0.5);
        transform: translateY(-1px);
    }

    div[data-testid="stFileUploader"] {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="app-header">
    <p class="app-title">🧠 QueryDoc AI</p>
    <p class="app-subtitle">Turn any document into context-aware Question-Answer pairs<br>in English, Hindi &amp; Marathi</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    uploaded_file = st.file_uploader("Upload your document", type=["pdf", "docx", "txt"], label_visibility="collapsed")
with col2:
    n_pairs = st.number_input("QnA per chunk", min_value=3, max_value=10, value=5)

if uploaded_file:
    st.info(f"📄 **{uploaded_file.name}** ready to process")

    if st.button("🚀 Generate QnA", use_container_width=True):
        temp_path = uploaded_file.name
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        progress = st.progress(0, text="Extracting text...")
        text = extract_text(temp_path)

        progress.progress(15, text="Splitting into chunks...")
        chunks = chunk_text(text)
        st.caption(f"Document split into {len(chunks)} chunk(s)")

        en_pairs = []
        for i, chunk in enumerate(chunks):
            pct = 15 + int((i / len(chunks)) * 45)
            progress.progress(pct, text=f"Generating English QnA (chunk {i+1}/{len(chunks)})...")
            en_pairs.extend(generate_qna(chunk, n_pairs=n_pairs))

        progress.progress(65, text="Translating to Hindi...")
        hi_pairs = translate_pairs(en_pairs, "Hindi")

        progress.progress(80, text="Translating to Marathi...")
        mr_pairs = translate_pairs(en_pairs, "Marathi")

        progress.progress(95, text="Building Excel file...")
        output_path = export_to_excel(en_pairs, hi_pairs, mr_pairs)

        progress.progress(100, text="Done!")
        st.success(f"✅ Generated {len(en_pairs)} QnA pairs in all 3 languages")

        tab1, tab2, tab3 = st.tabs(["🇬🇧 English", "🇮🇳 Hindi", "🇮🇳 Marathi"])
        with tab1:
            st.dataframe(en_pairs, use_container_width=True)
        with tab2:
            st.dataframe(hi_pairs, use_container_width=True)
        with tab3:
            st.dataframe(mr_pairs, use_container_width=True)

        with open(output_path, "rb") as f:
            st.download_button(
                "⬇️ Download Multilingual_QnA.xlsx",
                f,
                file_name="Multilingual_QnA.xlsx",
                use_container_width=True
            )

        os.remove(temp_path)
else:
    st.caption("👆 Upload a PDF, DOCX, or TXT file to get started")
