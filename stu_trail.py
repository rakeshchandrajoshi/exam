import streamlit as st
import json
import os
from datetime import datetime

# Directory to save student submissions and question paper
SUBMISSION_DIR = "student_submissions"
QUESTION_DIR = "question_paper"
os.makedirs(SUBMISSION_DIR, exist_ok=True)
os.makedirs(QUESTION_DIR, exist_ok=True)

# Password for accessing the Evaluator's question setting page
PASSWORD = "Amity@123"

# Function for the student submission portal
def student_submission_page():
    st.title("📚 Student Assignment Submission Portal")

    st.header("📝 Enter Your Details")
    name = st.text_input("Name")
    roll_number = st.text_input("Roll Number")
    course = st.text_input("Course")
    section = st.text_input("Section")

    # Load the current question paper if available
    question_file = os.path.join(QUESTION_DIR, "question_paper.json")
    if os.path.exists(question_file):
        with open(question_file, "r") as f:
            questions = json.load(f)
    else:
        questions = []

    if not questions:
        st.warning("⚠️ The evaluator hasn't set a question paper yet. Please ask the evaluator to set it.")

    st.header("✍️ Answer the Following Questions")

    responses = []
    for idx, q in enumerate(questions):
        ans = st.text_area(f"Question {idx + 1}: {q}", height=100, key=f"question_{idx}")  # Use unique key
        responses.append({
            "question": q,
            "answer": ans
        })

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


# Function for the evaluator to set the question paper with password protection
def evaluator_question_paper_page():
    # Ask for the evaluator's password
    password_input = st.text_input("Enter Password", type="password")

    # Check if the password is correct
    if password_input == PASSWORD:
        st.title("📑 Set Your Question Paper")

        # Load the current question paper if exists
        question_file = os.path.join(QUESTION_DIR, "question_paper.json")
        if os.path.exists(question_file):
            with open(question_file, "r") as f:
                questions = json.load(f)
        else:
            questions = []

        st.header("📝 Add Up to 5 Questions")

        # Display space for 5 questions
        question_1 = st.text_area("Question 1", height=100, value=questions[0] if len(questions) > 0 else "", key="question_1")
        question_2 = st.text_area("Question 2", height=100, value=questions[1] if len(questions) > 1 else "", key="question_2")
        question_3 = st.text_area("Question 3", height=100, value=questions[2] if len(questions) > 2 else "", key="question_3")
        question_4 = st.text_area("Question 4", height=100, value=questions[3] if len(questions) > 3 else "", key="question_4")
        question_5 = st.text_area("Question 5", height=100, value=questions[4] if len(questions) > 4 else "", key="question_5")

        # Collect questions
        new_questions = [question_1, question_2, question_3, question_4, question_5]

        if st.button("Save Question Paper"):
            # Save the non-empty questions to the file
            new_questions = [q for q in new_questions if q.strip() != ""]  # Remove empty questions
            if len(new_questions) > 0:
                with open(question_file, "w") as f:
                    json.dump(new_questions, f, indent=4)
                st.success("✅ Question Paper Saved!")
            else:
                st.warning("⚠️ Please enter at least one question.")

        # Display the current questions in the paper
        if new_questions:
            st.subheader("Current Questions in the Paper")
            for i, q in enumerate(new_questions, 1):
                st.write(f"{i}. {q}")

    else:
        st.error("❌ Incorrect password. Please try again.")


# Main function for the Streamlit app with navigation
def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select a page", ["Student Submission", "Evaluator: Set Question Paper"])

    if page == "Student Submission":
        student_submission_page()
    elif page == "Evaluator: Set Question Paper":
        evaluator_question_paper_page()


if __name__ == "__main__":
    main()
