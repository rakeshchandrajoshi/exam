import streamlit as st
import os
import json
from datetime import datetime
from zipfile import ZipFile
from io import BytesIO
import tempfile
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph
from langchain_groq import ChatGroq

# Configuration
PASSWORD = "Amity@123"
SUBMISSION_DIR = "student_submissions"
QUESTION_DIR = "question_paper"
EVALUATION_DIR = "evaluation_reports"
MODEL_NAME = "llama-3.3-70b-versatile""

os.makedirs(SUBMISSION_DIR, exist_ok=True)
os.makedirs(QUESTION_DIR, exist_ok=True)
os.makedirs(EVALUATION_DIR, exist_ok=True)

# -----------------------------
# Student Submission Page
# -----------------------------
def student_submission_page():
    st.title("📚 Student Assignment Submission Portal")
    st.header("📝 Enter Your Details")

    name = st.text_input("Name")
    roll_number = st.text_input("Roll Number")
    course = st.text_input("Course")
    section = st.text_input("Section")

    question_file = os.path.join(QUESTION_DIR, "question_paper.json")
    questions = []
    if os.path.exists(question_file):
        with open(question_file, "r") as f:
            questions = json.load(f)

    if not questions:
        st.warning("⚠️ The evaluator hasn't set a question paper yet.")
        return

    st.header("✍️ Answer the Following Questions")
    responses = []
    for idx, q in enumerate(questions):
        ans = st.text_area(f"Question {idx + 1}: {q}", height=100, key=f"question_{idx}")
        responses.append({"question": q, "answer": ans})

    if st.button("Submit Assignment"):
        if name and roll_number and course and section:
            data = {
                "name": name,
                "roll_number": roll_number,
                "course": course,
                "section": section,
                "submission_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "responses": responses
            }
            file_path = os.path.join(SUBMISSION_DIR, f"{roll_number}_{name.replace(' ', '_')}.json")
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)
            st.success("✅ Submission Successful!")
        else:
            st.warning("⚠️ Please fill all your details before submitting.")

# -----------------------------
# Set Question Paper (Protected)
# -----------------------------
def evaluator_question_paper_page():
    password_input = st.text_input("Enter Password", type="password")
    if password_input == PASSWORD:
        st.title("📑 Set Question Paper")
        question_file = os.path.join(QUESTION_DIR, "question_paper.json")

        questions = []
        if os.path.exists(question_file):
            with open(question_file, "r") as f:
                questions = json.load(f)

        st.header("📝 Add Up to 5 Questions")
        inputs = [st.text_area(f"Question {i + 1}", height=100, value=questions[i] if len(questions) > i else "", key=f"q{i}") for i in range(5)]
        new_questions = [q.strip() for q in inputs if q.strip() != ""]

        if st.button("Save Question Paper"):
            if new_questions:
                with open(question_file, "w") as f:
                    json.dump(new_questions, f, indent=4)
                st.success("✅ Question Paper Saved!")
            else:
                st.warning("⚠️ Please enter at least one question.")
    else:
        st.error("❌ Incorrect password.")

# -----------------------------
# AI Evaluation
# -----------------------------
import re

def evaluate_student_answers(student_data, groq_api_key):
    from langchain_groq import ChatGroq

    responses = student_data.get("responses", [])
    llm = ChatGroq(groq_api_key=groq_api_key, model_name=MODEL_NAME, temperature=0.3)
    evaluation_results = []

    for resp in responses:
        prompt = f"""
You are a strict evaluator for student assignments.

RULES:
1. Give a score out of 10.
2. Provide a short feedback (2-3 lines).
3. STRICT FORMAT ONLY JSON:
{{
  "question": "Original question",
  "student_answer": "Student's answer",
  "score_out_of_10": number,
  "feedback": "short feedback"
}}

Now evaluate:
Question: {resp['question']}
Student's Answer: {resp['answer']}
"""

        try:
            result = llm.invoke(prompt)
            content = result.content.strip()

            st.write("📤 LLM Raw Response:")
            st.code(content)

            # Extract only the JSON part
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if not json_match:
                raise ValueError("❌ No valid JSON found in LLM response.")

            evaluation_json = json.loads(json_match.group())

            # Validate keys
            required_keys = ["question", "student_answer", "score_out_of_10", "feedback"]
            if not all(key in evaluation_json for key in required_keys):
                raise ValueError("❌ Missing expected keys in LLM response.")

            evaluation_results.append(evaluation_json)

        except Exception as e:
            evaluation_results.append({
                "question": resp['question'],
                "student_answer": resp['answer'],
                "score_out_of_10": 0,
                "feedback": f"❌ Error parsing LLM response: {str(e)}"
            })

    return evaluation_results


def generate_pdf_report(student_data, evaluations):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>Evaluation Report for {student_data['name']}</b>", styles['Title']))
    for field in ["roll_number", "course", "section", "submission_time", "total_score", "max_score", "percentage"]:
        story.append(Paragraph(f"{field.replace('_', ' ').capitalize()}: {student_data.get(field)}", styles['Normal']))
    story.append(Paragraph('<b>Evaluations:</b>', styles['Normal']))

    for eval in evaluations:
        story.append(Paragraph(f"<b>Question:</b> {eval['question']}", styles['Normal']))
        story.append(Paragraph(f"<b>Student's Answer:</b> {eval['student_answer']}", styles['Normal']))
        story.append(Paragraph(f"<b>Score:</b> {eval['score_out_of_10']}/10", styles['Normal']))
        story.append(Paragraph(f"<b>Feedback:</b> {eval['feedback']}", styles['Normal']))
        story.append(Paragraph('<br/>', styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer

# -----------------------------
# Evaluation Page
# -----------------------------
def evaluation_page():
    st.title("🎯 AI Evaluator Dashboard")
    groq_key = st.text_input("Enter Evaluator Password", type="password")

    submission_files = [f for f in os.listdir(SUBMISSION_DIR) if f.endswith(".json")]
    if not submission_files:
        st.warning("⚠️ No student submissions found.")
        return

    if st.button("🚀 Start Evaluation"):
        if not groq_key:
            st.error("❌ Please enter your Groq API Key!")
            return

        leaderboard = []

        for file in submission_files:
            with open(os.path.join(SUBMISSION_DIR, file), "r") as f:
                student_data = json.load(f)

            evaluations = evaluate_student_answers(student_data, groq_key)
            total_score = sum([e["score_out_of_10"] for e in evaluations])
            max_score = len(evaluations) * 10
            percentage = (total_score / max_score) * 100

            student_data.update({
                "total_score": total_score,
                "max_score": max_score,
                "percentage": round(percentage, 2),
                "evaluations": evaluations
            })

            with open(os.path.join(EVALUATION_DIR, f"evaluation_{file}"), "w") as f:
                json.dump(student_data, f, indent=4)

            leaderboard.append({
                "Name": student_data["name"],
                "Roll Number": student_data["roll_number"],
                "Section": student_data["section"],
                "Total Score": total_score,
                "Max Score": max_score,
                "Percentage": round(percentage, 2)
            })

        df = pd.DataFrame(leaderboard).sort_values(by="Percentage", ascending=False).reset_index(drop=True)
        st.success("✅ Evaluation Complete!")
        st.dataframe(df)

        if st.button("⬇️ Download All Evaluation Reports (ZIP)"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                with ZipFile(tmp_zip.name, 'w') as zipf:
                    for root, _, files in os.walk(EVALUATION_DIR):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(file_path, EVALUATION_DIR))
                with open(tmp_zip.name, "rb") as f:
                    st.download_button("Download ZIP", f, file_name="evaluation_reports.zip", mime="application/zip")

# -----------------------------
# Download Reports (Protected)
# -----------------------------
def download_page():
    st.title("📥 Download Student Reports")
    password_input = st.text_input("Enter Evaluator Password", type="password")
    if password_input != PASSWORD:
        st.error("❌ Incorrect password.")
        return

    evaluation_files = [f for f in os.listdir(EVALUATION_DIR) if f.endswith(".json")]
    if not evaluation_files:
        st.warning("⚠️ No evaluation reports found.")
        return

    leaderboard = []
    for file in evaluation_files:
        with open(os.path.join(EVALUATION_DIR, file), "r") as f:
            data = json.load(f)
            leaderboard.append({
                "Name": data["name"],
                "Roll Number": data["roll_number"],
                "Percentage": data["percentage"]
            })

    df = pd.DataFrame(leaderboard).sort_values(by="Percentage", ascending=False).reset_index(drop=True)
    st.dataframe(df)

    selected_name = st.selectbox("Select student", df["Name"])
    for file in evaluation_files:
        with open(os.path.join(EVALUATION_DIR, file), "r") as f:
            data = json.load(f)
            if data["name"] == selected_name:
                pdf = generate_pdf_report(data, data["evaluations"])
                st.download_button("Download PDF Report", pdf, file_name=f"report_{selected_name}.pdf", mime="application/pdf")
                break

    if st.button("⬇️ Download All Evaluation Reports (ZIP)"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
            with ZipFile(tmp_zip.name, 'w') as zipf:
                for root, _, files in os.walk(EVALUATION_DIR):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, EVALUATION_DIR))
            with open(tmp_zip.name, "rb") as f:
                st.download_button("Download ZIP", f, file_name="evaluation_reports.zip", mime="application/zip")

# -----------------------------
# Main Navigation
# -----------------------------
def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", [
        "Student Submission",
        "Evaluator: Set Question Paper",
        "Evaluation",
        "Download Reports"
    ])

    if page == "Student Submission":
        student_submission_page()
    elif page == "Evaluator: Set Question Paper":
        evaluator_question_paper_page()
    elif page == "Evaluation":
        evaluation_page()
    elif page == "Download Reports":
        download_page()

if __name__ == "__main__":
    main()

