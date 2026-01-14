import streamlit as st
import re
import random
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Network Exam Simulation", layout="wide")

# --- CUSTOM CSS FOR BETTER LAYOUT ---
# This forces the columns to have a distinct look
st.markdown("""
<style>
    .stRadio p {font-size: 16px;}
    div[data-testid="column"] {
        padding: 15px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- PARSING FUNCTION ---
@st.cache_data
def load_questions(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        st.error("Error: File 'domande.txt' not found!")
        return []

    raw_questions = re.split(r'Question \d+', content)
    parsed_data = []
    
    for raw in raw_questions:
        if not raw.strip(): continue
        q_data = {}
        
        q_match = re.search(r'Question:\s*(.*?)\s*Option A:', raw, re.DOTALL)
        if not q_match: continue
        q_data['text'] = q_match.group(1).strip()
        
        options = {}
        for letter in ['A', 'B', 'C', 'D']:
            pattern = rf'Option {letter}:\s*(.*?)\s*(Option [A-D]:|Correct Answer:)'
            opt_match = re.search(pattern, raw, re.DOTALL)
            if opt_match:
                options[letter] = opt_match.group(1).strip()
        q_data['options'] = options
        
        correct_match = re.search(r'Correct Answer:\s*([A-D])', raw)
        if correct_match: q_data['correct'] = correct_match.group(1).strip()
        
        motiv_match = re.search(r'Motivation:\s*(.*)', raw, re.DOTALL)
        q_data['motivation'] = motiv_match.group(1).strip() if motiv_match else "No motivation available."
        
        parsed_data.append(q_data)
    return parsed_data

# --- APP STATE ---
if 'exam_started' not in st.session_state:
    st.session_state.exam_started = False
if 'selected_questions' not in st.session_state:
    st.session_state.selected_questions = []
if 'start_time' not in st.session_state:
    st.session_state.start_time = 0
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}

# --- INTERFACE ---
st.title("🎓 Network Exam Simulator")

questions_db = load_questions("domande.txt")

# --- 1. START MENU ---
if not st.session_state.exam_started:
    st.write(f"Questions in database: **{len(questions_db)}**")
    st.info("Rules: +1 correct, -0.33 wrong, 0 skipped. Time limit: 60 min.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Quick Test (10 questions)"):
            st.session_state.selected_questions = random.sample(questions_db, min(10, len(questions_db)))
            st.session_state.exam_started = True
            st.session_state.submitted = False
            st.session_state.start_time = time.time()
            st.rerun()
    with col2:
        if st.button("📝 Full Exam (33 questions)"):
            st.session_state.selected_questions = random.sample(questions_db, min(33, len(questions_db)))
            st.session_state.exam_started = True
            st.session_state.submitted = False
            st.session_state.start_time = time.time()
            st.rerun()

# --- 2. EXAM INTERFACE ---
elif not st.session_state.submitted:
    # Timer
    elapsed = time.time() - st.session_state.start_time
    remaining = 3600 - elapsed
    if remaining > 0:
        mins, secs = divmod(int(remaining), 60)
        st.sidebar.metric("⏳ Time Remaining", f"{mins:02d}:{secs:02d}")
    else:
        st.sidebar.error("TIME'S UP!")

    with st.form("exam_form"):
        st.write("### Answer the questions below:")
        
        # Temporary dictionary to capture form inputs
        current_answers = {}
        
        for idx, q in enumerate(st.session_state.selected_questions):
            st.markdown(f"**{idx + 1}.** {q['text']}")
            
            opts = ["No answer"] + [f"{k}) {v}" for k, v in q['options'].items()]
            # We use key=f"q_{idx}" to store the state
            current_answers[idx] = st.radio("Choose:", opts, key=f"q_{idx}", label_visibility="collapsed")
            st.markdown("---")
        
        submitted_btn = st.form_submit_button("Submit and Grade")
        
        if submitted_btn:
            st.session_state.submitted = True
            # Save answers to session state so we can access them outside the form
            st.session_state.user_answers = current_answers 
            st.rerun()

# --- 3. RESULTS INTERFACE (SIDE BY SIDE) ---
else:
    st.header("📊 Exam Results")
    
    score = 0
    correct_count = 0
    wrong_count = 0
    skipped_count = 0
    
    # Logic to calculate score first
    for idx, q in enumerate(st.session_state.selected_questions):
        ans = st.session_state.user_answers.get(idx, "No answer")
        correct_opt = q['correct']
        
        if ans == "No answer":
            skipped_count += 1
        else:
            letter = ans.split(")")[0]
            if letter == correct_opt:
                score += 1
                correct_count += 1
            else:
                score -= 0.33
                wrong_count += 1

    final_score = round(score, 2)
    
    # Display Score Metrics at the top
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Final Score", f"{final_score} / {len(st.session_state.selected_questions)}")
    m2.metric("Correct", correct_count, delta_color="normal")
    m3.metric("Wrong", wrong_count, delta_color="inverse")
    m4.metric("Skipped", skipped_count, delta_color="off")
    
    st.divider()
    
    # --- DETAILED REVIEW LOOP ---
    for idx, q in enumerate(st.session_state.selected_questions):
        # Create two columns: Left (Question/Options) | Right (Feedback)
        col_left, col_right = st.columns([1, 1], gap="large")
        
        ans = st.session_state.user_answers.get(idx, "No answer")
        correct_opt = q['correct']
        
        # --- LEFT COLUMN: The Question ---
        with col_left:
            st.subheader(f"Q{idx+1}")
            st.info(q['text'])  # Display question text in a box
            
            # Show options again (Disabled, so user can't change them now)
            opts = ["No answer"] + [f"{k}) {v}" for k, v in q['options'].items()]
            
            # Find index of user selection to show it selected
            try:
                sel_index = opts.index(ans)
            except ValueError:
                sel_index = 0
                
            st.radio("Your Answer:", opts, index=sel_index, disabled=True, key=f"res_radio_{idx}")

        # --- RIGHT COLUMN: The Correction ---
        with col_right:
            st.write("### Feedback")
            
            if ans == "No answer":
                st.warning(f"⚪ **Skipped**")
                st.write(f"Correct Answer: **Option {correct_opt}**")
            else:
                letter = ans.split(")")[0]
                if letter == correct_opt:
                    st.success(f"✅ **Correct!** (+1 pt)")
                else:
                    st.error(f"❌ **Wrong!** (-0.33 pt)")
                    st.write(f"You chose **{letter}**, but the correct answer was **{correct_opt}**.")

            # Motivation Box
            with st.expander("📖 Read Explanation / Motivation", expanded=True):
                st.markdown(f"_{q['motivation']}_")
        
        st.divider() # Line separator between questions

    # Restart Button
    if st.button("🔄 Restart Exam", type="primary"):
        st.session_state.exam_started = False
        st.session_state.submitted = False
        st.session_state.user_answers = {}
        st.rerun()