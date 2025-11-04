import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import asyncio
import time

# Arcadis brand colors and custom CSS
arcadis_css = """
<style>
    body {
        background-color: #f4f4f4;
    }
    .stApp {
        font-family: 'Segoe UI', sans-serif;
    }
    h1, h2, h3 {
        color: #ff6a13;
    }
    .css-1v3fvcr {
        background-color: #002c5f !important;
    }
    .stButton>button {
        background-color: #ff6a13;
        color: white;
    }
    .stTextInput>div>input {
        border: 1px solid #002c5f;
    }
</style>
"""

st.set_page_config(page_title="CV Skill Matching Assistant", layout="wide")
st.markdown(arcadis_css, unsafe_allow_html=True)
st.title("CV Skill Matching Assistant")

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Sidebar Smart Assistant
with st.sidebar:
    st.header("🤖 Smart Mock Assistant")
    st.markdown("Ask questions about unmatched CVs or alternative roles.")
    user_query = st.text_area("💬 Your question:")
    submit_query = st.button("Ask Assistant")

# Cache Excel loading
@st.cache_data
def load_skills_excel(file):
    return pd.read_excel(file, sheet_name="Skills Master JIE", engine="openpyxl")

# Cache PDF text extraction
@st.cache_data
def extract_text_from_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text.lower()

# Async CV processing
async def process_cv(cv_file, combined_keywords):
    text = extract_text_from_pdf(cv_file.read())
    matched = [kw for kw in combined_keywords if kw in text]
    return {
        "CV Name": cv_file.name,
        "Match Count": len(matched),
        "Matched Keywords": ", ".join(matched),
        "Raw Text": text,
        "Matched List": matched
    }

# Upload Excel file
excel_file = st.file_uploader("📄 Upload Excel file with job skills", type=["xlsx"])
if excel_file:
    df_skills = load_skills_excel(excel_file)

    if "Unnamed: 1" in df_skills.columns and "Unnamed: 3" in df_skills.columns:
        job_titles = df_skills["Unnamed: 1"].dropna().unique()
        selected_job = st.selectbox("🎯 Select a job title", sorted(job_titles))

        job_skills = df_skills[df_skills["Unnamed: 1"] == selected_job]["Unnamed: 3"].dropna().str.lower().unique()
        st.write(f"✅ Found {len(job_skills)} skills for **{selected_job}**")

        keyword_input = st.text_input("🔍 Enter additional keywords (comma-separated)", "")
        custom_keywords = [kw.strip().lower() for kw in keyword_input.split(",") if kw.strip()]
        combined_keywords = list(set(job_skills).union(custom_keywords))
        st.write(f"🔗 Matching against {len(combined_keywords)} total keywords")

        uploaded_cvs = st.file_uploader("📥 Upload CV PDFs", type=["pdf"], accept_multiple_files=True, label_visibility="visible")
        if uploaded_cvs:
            st.subheader("📊 CV Match Results")
            results = []
            unmatched_cvs = []

            with st.spinner("Processing CVs..."):
                tasks = [process_cv(cv_file, combined_keywords) for cv_file in uploaded_cvs]
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                processed = loop.run_until_complete(asyncio.gather(*tasks))

            for result in processed:
                results.append({
                    "CV Name": result["CV Name"],
                    "Match Count": result["Match Count"],
                    "Matched Keywords": result["Matched Keywords"]
                })
                if result["Match Count"] < max(1, len(combined_keywords) // 4):
                    unmatched_cvs.append((result["CV Name"], result["Raw Text"], result["Matched List"]))

            st.dataframe(pd.DataFrame(results).sort_values(by="Match Count", ascending=False))
            st.session_state.unmatched_cvs = unmatched_cvs
            st.session_state.combined_keywords = combined_keywords

# Assistant logic
if submit_query and user_query and "unmatched_cvs" in st.session_state:
    for name, text, matched in st.session_state.unmatched_cvs:
        suggestions = []
        reasoning = []

        if "excel" in text or "spreadsheet" in text:
            suggestions.append("Data Entry Clerk")
            reasoning.append("Mentions Excel/spreadsheet skills suitable for data entry roles.")
        if "project" in text or "timeline" in text:
            suggestions.append("Project Coordinator")
            reasoning.append("Mentions project-related terms indicating coordination experience.")
        if "customer" in text or "client" in text:
            suggestions.append("Customer Support Representative")
            reasoning.append("Mentions customer/client interactions suitable for support roles.")
        if "python" in text or "sql" in text or "data analysis" in text:
            suggestions.append("Junior Data Analyst")
            reasoning.append("Mentions programming or data analysis skills.")
        if "marketing" in text or "campaign" in text:
            suggestions.append("Marketing Assistant")
            reasoning.append("Mentions marketing-related terms suitable for assistant roles.")
        if "design" in text or "autocad" in text or "revit" in text:
            suggestions.append("Design Technician")
            reasoning.append("Mentions design tools indicating suitability for technical design roles.")
        if not suggestions:
            suggestions.append("General Office Support")
            reasoning.append("No strong keyword matches; general support role may be appropriate.")

        missing_skills = [kw for kw in st.session_state.combined_keywords if kw not in text]

        st.session_state.chat_history.insert(0, {
            "cv_name": name,
            "question": user_query,
            "matched": matched,
            "missing": missing_skills[:10],
            "suggestions": suggestions,
            "reasoning": reasoning
        })

# Display chat history
if st.session_state.chat_history:
    st.sidebar.markdown("### 🧠 Assistant Responses")
    for entry in st.session_state.chat_history:
        st.sidebar.markdown(f"**CV: {entry['cv_name']}**")
        st.sidebar.markdown(f"💬 Question: {entry['question']}")
        st.sidebar.markdown(f"🔍 Matched Keywords: {', '.join(entry['matched']) if entry['matched'] else 'None'}")
        st.sidebar.markdown(f"❌ Missing Skills: {', '.join(entry['missing'])}...")
        st.sidebar.markdown(f"✅ Suggested Roles: {', '.join(entry['suggestions'])}")
        st.sidebar.markdown("📌 Reasoning:")
        for reason in entry["reasoning"]:
            st.sidebar.markdown(f"- {reason}")
        st.sidebar.markdown("---")
