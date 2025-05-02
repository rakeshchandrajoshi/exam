import streamlit as st
import os
import json
from zipfile import ZipFile
import pandas as pd
from langchain_groq import ChatGroq
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph
from io import BytesIO

# Settings
SUBMISSION_DIR = "student_submissions"
EVALUATION_DIR = "evaluation_reports"
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"

os.makedirs(EVALUATION_DIR, exist_ok=True)


# Evaluation function
def evaluate_student_answers(student_data, groq_api_key):
    if "responses" in student_data:
        responses = student_data["responses"]
    else:
        responses = []
        for key in student_data:
            if key.lower().startswith("q"):
                responses.append({
                    "question": f"Question {key[-1]}",
                    "answer": student_data[key]
                })

    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name=MODEL_NAME,
        temperature=0.3
    )

    evaluation_results = []

    for resp in responses:
        question = resp["question"]
        answer = resp["answer"]

        # Construct Prompt directly (no template issue)
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
NO extra text outside JSON.

Now evaluate:
Question: {question}

Student's Answer: {answer}
"""

        try:
            result = llm.invoke(prompt)
            evaluation_json = json.loads(result.content)
            evaluation_results.append(evaluation_json)

        except Exception as e:
            evaluation_results.append({
                "question": question,
                "student_answer": answer,
                "score_out_of_10": 0,
                "feedback": f"Error: {str(e)}"
            })

    return evaluation_results


# Generate PDF report for each student
def generate_pdf_report(student_data, evaluations):
    buffer = BytesIO()

    # Create a PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Get the default stylesheet
    styles = getSampleStyleSheet()

    # Create a list of story elements to add to the document
    story = []

    # Add student info to the PDF
    title = f"Evaluation Report for {student_data['name']}"
    story.append(Paragraph(f'<b>{title}</b>', styles['Title']))

    story.append(Paragraph(f"Roll Number: {student_data['roll_number']}", styles['Normal']))
    story.append(Paragraph(f"Course: {student_data['course']}", styles['Normal']))
    story.append(Paragraph(f"Section: {student_data['section']}", styles['Normal']))
    story.append(Paragraph(f"Submission Time: {student_data['submission_time']}", styles['Normal']))
    story.append(Paragraph(f"Total Score: {student_data['total_score']}/{student_data['max_score']}", styles['Normal']))
    story.append(Paragraph(f"Percentage: {student_data['percentage']}%", styles['Normal']))

    story.append(Paragraph('<b>Evaluations:</b>', styles['Normal']))

    # Add each evaluation to the PDF
    for eval in evaluations:
        question = eval["question"]
        student_answer = eval["student_answer"]
        score = eval["score_out_of_10"]
        feedback = eval["feedback"]

        story.append(Paragraph(f'<b>Question:</b> {question}', styles['Normal']))
        story.append(Paragraph(f'<b>Student\'s Answer:</b> {student_answer}', styles['Normal']))
        story.append(Paragraph(f'<b>Score:</b> {score}/10', styles['Normal']))
        story.append(Paragraph(f'<b>Feedback:</b> {feedback}', styles['Normal']))
        story.append(Paragraph('<br/>', styles['Normal']))  # Add some space between questions

    # Build the PDF
    doc.build(story)

    # Save and return the buffer
    buffer.seek(0)
    return buffer


# Page 1: Evaluation
def evaluation_page():
    st.title("🎯 Evaluator Dashboard - AI Assignment Evaluator")

    st.sidebar.header("🔑 Enter Evaluator Password")
    GROQ_API_KEY = st.sidebar.text_input("Key", type="password")

    st.header("📄 Submissions Available")

    submission_files = [f for f in os.listdir(SUBMISSION_DIR) if f.endswith(".json")]
    st.write(f"Total submissions: **{len(submission_files)}**")

    if len(submission_files) == 0:
        st.warning("⚠️ No student submissions yet.")
        return

    if st.button("🚀 Start Evaluation"):
        if not GROQ_API_KEY:
            st.error("❌ Please enter your Password!")
            return

        leaderboard = []

        for file in submission_files:
            file_path = os.path.join(SUBMISSION_DIR, file)
            with open(file_path, "r") as f:
                student_data = json.load(f)

            evaluations = evaluate_student_answers(student_data, GROQ_API_KEY)

            total_score = sum([e["score_out_of_10"] for e in evaluations])
            max_score = len(evaluations) * 10
            percentage = (total_score / max_score) * 100

            evaluation_report = {
                "name": student_data.get("name", ""),
                "roll_number": student_data.get("roll_number", ""),
                "course": student_data.get("course", ""),
                "section": student_data.get("section", ""),
                "submission_time": student_data.get("submission_time", ""),
                "total_score": total_score,
                "max_score": max_score,
                "percentage": round(percentage, 2),
                "evaluations": evaluations
            }

            save_path = os.path.join(EVALUATION_DIR, f"evaluation_{file}")
            with open(save_path, "w") as f:
                json.dump(evaluation_report, f, indent=4)

            leaderboard.append({
                "Name": student_data.get("name", ""),
                "Roll Number": student_data.get("roll_number", ""),
                "Section": student_data.get("section", ""),
                "Total Score": total_score,
                "Max Score": max_score,
                "Percentage": round(percentage, 2)
            })

        df = pd.DataFrame(leaderboard)
        df = df.sort_values(by="Percentage", ascending=False).reset_index(drop=True)

        st.success("✅ Evaluation Completed!")
        st.subheader("🏆 Leaderboard")
        st.dataframe(df)

        # Allow evaluator to download all reports
        if st.button("⬇️ Download All Evaluation Reports (ZIP)"):
            zip_path = "evaluation_reports.zip"
            with ZipFile(zip_path, 'w') as zipf:
                for root, dirs, files in os.walk(EVALUATION_DIR):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, EVALUATION_DIR))

            with open(zip_path, "rb") as f:
                st.download_button(
                    label="Download ZIP",
                    data=f,
                    file_name="evaluation_reports.zip",
                    mime="application/zip"
                )

            os.remove(zip_path)


# Page 2: Download Reports
def download_page():
    st.title("📥 Download Student Evaluation Reports")

    submission_files = [f for f in os.listdir(SUBMISSION_DIR) if f.endswith(".json")]
    evaluation_files = [f for f in os.listdir(EVALUATION_DIR) if f.endswith(".json")]

    if len(evaluation_files) == 0:
        st.warning("⚠️ No evaluations have been completed yet. Please run the evaluation first.")
        return

    leaderboard = []
    for file in evaluation_files:
        with open(os.path.join(EVALUATION_DIR, file), "r") as f:
            evaluation_data = json.load(f)
            leaderboard.append({
                "Name": evaluation_data.get("name", ""),
                "Roll Number": evaluation_data.get("roll_number", ""),
                "Percentage": evaluation_data.get("percentage", 0)
            })

    df = pd.DataFrame(leaderboard)
    df = df.sort_values(by="Percentage", ascending=False).reset_index(drop=True)

    st.subheader("🏆 Leaderboard")
    st.dataframe(df)

    selected_student = st.selectbox("Select a student to download their report", df["Name"])

    # Find the corresponding evaluation file
    student_evaluation_file = None
    for file in evaluation_files:
        with open(os.path.join(EVALUATION_DIR, file), "r") as f:
            evaluation_data = json.load(f)
            if evaluation_data["name"] == selected_student:
                student_evaluation_file = file
                break

    if student_evaluation_file:
        # Generate and download PDF report
        with open(os.path.join(EVALUATION_DIR, student_evaluation_file), "r") as f:
            evaluation_data = json.load(f)

        pdf_buffer = generate_pdf_report(evaluation_data, evaluation_data["evaluations"])

        st.download_button(
            label="Download Evaluation Report (PDF)",
            data=pdf_buffer,
            file_name=f"evaluation_report_{selected_student}.pdf",
            mime="application/pdf"
        )

    if st.button("⬇️ Download All Evaluation Reports (ZIP)"):
        zip_path = "evaluation_reports.zip"
        with ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(EVALUATION_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, EVALUATION_DIR))

        with open(zip_path, "rb") as f:
            st.download_button(
                label="Download All Reports (ZIP)",
                data=f,
                file_name="evaluation_reports.zip",
                mime="application/zip"
            )

        os.remove(zip_path)


def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select a page", ["Evaluation", "Download Reports"])

    if page == "Evaluation":
        evaluation_page()
    elif page == "Download Reports":
        download_page()


if __name__ == "__main__":
    main()
