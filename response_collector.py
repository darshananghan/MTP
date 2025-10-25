import streamlit as st
import random
import pandas as pd 
import ast 
import time 
from pymongo import MongoClient

# -----------------------------
# Configuration
# -----------------------------
DEFAULT_USER_NAME = "Annotator_Guest" 
TIMER_DURATION_SECONDS = 20 # Minimum timer duration

# MongoDB Configuration
# NOTE: In deployment, the URI should be loaded from Streamlit Secrets (secrets.toml)
# For local testing, replace the placeholder below with your actual URI.
# The database and collection names are defined below.
DB_NAME = "annotation_db"
QUESTION_COLLECTION_NAME = "questions_collection"
RESPONSE_COLLECTION_NAME = "responses_collection"

# -----------------------------
# MongoDB Setup
# -----------------------------

@st.cache_resource
def init_db():
    """Initializes the MongoDB client and returns the database object."""
    try:
        # Load URI from Streamlit Secrets (recommended for deployment)
        MONGO_URI = st.secrets["mongo"]["uri"]
    except KeyError:
        st.error("MongoDB URI not found in Streamlit secrets. Please check your secrets.toml file.")
        st.stop()
        return None

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        st.success("Successfully connected to MongoDB Atlas!")
        return db
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {e}")
        st.stop()
        return None

db = init_db()

# -----------------------------
# Helper functions
# -----------------------------
def get_random_questions(user_name, n=20):
    """
    Fetches n random questions from the MongoDB questions_collection.
    No filtering is applied, allowing multiple annotations per question.
    """
    if db is None:
        return []
        
    try:
        questions_collection = db[QUESTION_COLLECTION_NAME]
        
        # MongoDB Aggregation Pipeline for efficient random sampling
        pipeline = [
            {"$sample": {"size": n}}
        ]
        
        # Fetching data and transforming it for Streamlit's session state structure
        results = list(questions_collection.aggregate(pipeline))
        
        # The function must return a list of tuples: (question_id, question_text, true_label, others_options_str)
        questions_list = []
        for doc in results:
            # We assume 'others_options' is stored as a list in MongoDB
            others_options_str = str(doc.get('others_options', [])) 
            questions_list.append((
                doc.get('question_id', str(doc['_id'])), # Use unique ID as fallback
                doc.get('question_text', 'N/A'),
                doc.get('true_label', 'N/A'),
                others_options_str
            ))

        return questions_list
        
    except Exception as e:
        st.error(f"Error fetching questions from MongoDB: {e}")
        return []

def save_response(user_name, question_id, response):
    """Saves a single user response (the selected label) to the MongoDB responses_collection."""
    if db is None:
        return
        
    try:
        responses_collection = db[RESPONSE_COLLECTION_NAME]
        
        response_doc = {
            "user_name": user_name,
            "question_id": question_id,
            "response": response,
            "timestamp": datetime.now()
        }
        
        responses_collection.insert_one(response_doc)
        
    except Exception as e:
        # Note: In a production app, you would log this instead of showing an error
        print(f"Error saving response to MongoDB: {e}")


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Identify the Demographic", layout="centered")

# --- INITIAL DATA LOAD ---
# The logic to insert questions from CSV is removed from the app flow.
# We trust that the questions collection is populated via the setup steps.
# The session state setup below handles loading the questions for the first time.

# -----------------------------
# Session state setup
# -----------------------------
if "user_name" not in st.session_state:
    st.session_state.user_name = DEFAULT_USER_NAME
if "questions" not in st.session_state or not st.session_state.questions:
    # Load initial batch of questions if session is new or questions list is empty
    st.session_state.questions = get_random_questions(st.session_state.user_name, 20)
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "responses" not in st.session_state:
    st.session_state.responses = {}
if "timer_start_time" not in st.session_state:
    st.session_state.timer_start_time = None
if "assessment_started" not in st.session_state:
    st.session_state.assessment_started = False


def start_new_session():
    """Clears session state and resets for a new session."""
    st.session_state.clear()
    
    st.session_state.user_name = DEFAULT_USER_NAME
    st.session_state.timer_start_time = None
    st.session_state.assessment_started = False 
    st.session_state.questions = get_random_questions(st.session_state.user_name, 20)
    st.session_state.current_idx = 0
    st.session_state.responses = {}
    st.rerun() 

def start_assessment_button_handler():
    """Sets the state to allow question display."""
    st.session_state.assessment_started = True


# --- Core logic to handle the button click and advance question ---
def handle_answer_submission(response_value):
    """Saves the answer and updates the state."""
    if st.session_state.current_idx < len(st.session_state.questions):
        qid = st.session_state.questions[st.session_state.current_idx][0]
        save_response(st.session_state.user_name, qid, response_value)
        st.session_state.responses[qid] = response_value
        st.session_state.current_idx += 1
# -------------------------------------------------------------------


# -----------------------------
# Main Application Flow
# -----------------------------

# -----------------------------
# Instructions and Timer Section (Conditional Display)
# -----------------------------

if not st.session_state.assessment_started:
    
    st.title("🧠 Identify the Demographic")
    st.markdown("---")
    
    if st.session_state.timer_start_time is None:
        st.session_state.timer_start_time = time.time()
        
    elapsed_time = time.time() - st.session_state.timer_start_time
    time_remaining = max(0, TIMER_DURATION_SECONDS - int(elapsed_time))
    timer_expired = time_remaining == 0
    
    st.subheader("Task Instructions (Read Carefully!)")
    
    timer_placeholder = st.empty() 
    
    if not timer_expired:
        timer_placeholder.warning(f"⏰ Please take a moment to read the instructions. Assessment is enabled in: **{time_remaining} seconds**")
    else:
        timer_placeholder.success("✅ Instructions read time complete. You may now start the assessment.")

    st.markdown("""
    All the statements are regarding **Person A**. Your task is to assign a demographic to Person A based on the statement. 
    
    **Please note that sentences regarding Person A can be from different demographics. Demographics can include:** **Gender, Religion, Region, Caste, Age, Socio-economic status, Race, and Disability.**

    ### The Options
    You will be given **3 options** for each statement:
    * **Two Demographic Labels**: These represent the two possible demographics that Person A could belong to (e.g., 'Male' and 'Female', or 'Asian' and 'Caucasian').
    * **Don't know/Neutral**: Choose this if you feel that the statement is **unknown/ambiguous** or if you **do not wish to assign a demographic** based on the statement.
    
    ### Guidelines
    * **Choose based on your opinion**: Select the label that best represents the demographic you infer from the statement.
    * **Use Don't know/Neutral when unsure**: If you are confused, feel the statement is ambiguous, or cannot confidently assign one of the two demographic labels, select **Don't know/Neutral**.
    * **Search if needed**: If you are unfamiliar with a word or the context of the sentence, feel free to use a **Google search** to clarify your understanding before making a selection.
    
    """)
    st.markdown("---")
    
    st.button(
        "Start Assessment", 
        type="primary", 
        disabled=not timer_expired, 
        on_click=start_assessment_button_handler
    )

    if not timer_expired:
        time.sleep(1)
        st.rerun()

# -----------------------------
# Assessment Running
# -----------------------------
else: 
    
    idx = st.session_state.current_idx
    questions = st.session_state.questions

    if not questions:
        st.warning("No questions are available in the database. Please check the 'questions_collection' in your MongoDB.")

    elif idx < len(questions):
        st.sidebar.markdown(f"**Current Session:** `{st.session_state.user_name}`")
        
        qid, qtext, true_label, others_options_str = questions[idx]

        # --- DYNAMIC OPTION GENERATION (Adapted for MongoDB list structure) ---
        try:
            # We assume others_options_str is a string representation of a Python list 
            # (e.g., "['LabelC', 'LabelD']") coming from the document fetch.
            other_options_list = ast.literal_eval(others_options_str)
        except:
            other_options_list = [s.strip() for s in others_options_str.strip('[]{}').split(',')]

        if other_options_list and len(other_options_list) > 0:
            false_label = random.choice(other_options_list)
        else:
            false_label = "Other Category" 

        option_labels = [true_label, false_label, "Don't know/Neutral"]
        random.shuffle(option_labels)
        
        # ---------------------------------
        
        st.markdown(f"## Question {idx+1} of {len(questions)}")
        st.progress((idx+1)/len(questions))
        
        with st.container(border=True):
            st.subheader(qtext)
            st.markdown("---")
            st.markdown('<p style="font-size: 16px;"><b>Select the demographic label for Person A:</b></p>', unsafe_allow_html=True) 

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.button(option_labels[0], use_container_width=True, on_click=handle_answer_submission, args=(option_labels[0],), type="secondary")
        with col2:
            st.button(option_labels[1], use_container_width=True, on_click=handle_answer_submission, args=(option_labels[1],), type="secondary")
        with col3:
            st.button(option_labels[2], use_container_width=True, on_click=handle_answer_submission, args=(option_labels[2],), type="secondary")


    else:
        # --- Completion Screen ---
        st.balloons()
        st.success("🎉 Assessment Complete!")
        
        st.markdown("Your responses are **invaluable** to us and to the community. **Cheers to you for helping us build Responsible and Safe AI systems!** 🤝")
        st.markdown("---")
        
        st.write("Thank you for completing this batch of questions.")
        st.button("Start New Session (Re-load)", on_click=start_new_session, type="primary")
