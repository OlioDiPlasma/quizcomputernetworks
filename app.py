import streamlit as st
import re
import random
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Network Exam Simulation", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stRadio p {font-size: 16px;}
    div[data-testid="column"] {
        padding: 15px;
        border-radius: 10px;
    }
    .question-header {
        font-weight: bold;
        color: #31333F;
        font-size: 1.1em;
        margin-bottom: 10px;
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

    parts = re.split(r'Question (\d+)', content)
    parsed_data = []
    
    for i in range(1, len(parts), 2):
        q_id = parts[i].strip()
        raw = parts[i+1]
        
        if not raw.strip(): continue
        q_data = {}
        q_data['id'] = q_id
        
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
if 'end_time' not in st.session_state:
    st.session_state.end_time = 0
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}

# --- INTERFACE ---
st.title("🎓 Computer Network Exam Simulator 3.0")

questions_db = load_questions("domande.txt")

# --- 1. START MENU ---
if not st.session_state.exam_started:
    st.write(f"Questions in database: **{len(questions_db)}**")
    st.info("Rules: +1 correct, -0.33 wrong, 0 skipped. Time limit: 60 min.")
    
    col1, col2 = st.columns(2)
    def start_exam(n):
        st.session_state.selected_questions = random.sample(questions_db, min(n, len(questions_db)))
        st.session_state.exam_started = True
        st.session_state.submitted = False
        # Set End Time (Current time + 60 minutes)
        st.session_state.end_time = time.time() + 3600
        st.rerun()

    with col1:
        if st.button("🚀 Quick Test (10 questions)"):
            start_exam(10)
    with col2:
        if st.button("📝 Full Exam (33 questions)"):
            start_exam(33)

# --- 2. EXAM INTERFACE ---
elif not st.session_state.submitted:
    
    # --- ROBUST LIVE TIMER ---
    # Calcoliamo il timestamp finale
    end_timestamp = st.session_state.end_time
    
    # Inseriamo il timer nella sidebar con un controllo di sicurezza in JS
    st.sidebar.markdown(f"""
        <div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="margin:0; color: #333;">⏳ Time Remaining</h3>
            <div id="countdown" style="font-size: 24px; font-weight: bold; color: #ff4b4b;">--:--</div>
        </div>
        <script>
        // Passiamo il valore da Python a JS
        var endTime = {end_timestamp}; 

        var timerInterval = setInterval(function() {{
            var element = document.getElementById("countdown");
            
            // SE IL DIV NON ESISTE ANCORA, NON FARE NULLA E ASPETTA IL PROSSIMO GIRO
            if (!element) return;
            
            var now = new Date().getTime() / 1000;
            var distance = endTime - now;
            
            if (distance < 0) {{
                element.innerHTML = "EXPIRED";
                clearInterval(timerInterval);
                return;
            }}
            
            var minutes = Math.floor(distance / 60);
            var seconds = Math.floor(distance % 60);
            
            minutes = minutes < 10 ? "0" + minutes : minutes;
            seconds = seconds < 10 ? "0" + seconds : seconds;
            
            element.innerHTML = minutes + ":" + seconds;
        }}, 1000);
        </script>
        """, unsafe_allow_html=True)

    with st.form("exam_form"):
        st.write("### Answer the questions below:")
        
        current_answers = {}
        for idx, q in enumerate(st.session_state.selected_questions):
            st.markdown(f"**{idx + 1}.** <span style='color:gray; font-size:0.9em'>(ID: {q['id']})</span> &nbsp; {q['text']}", unsafe_allow_html=True)
            opts = ["No answer"] + [f"{k}) {v}" for k, v in q['options'].items()]
            current_answers[idx] = st.radio(f"Choice {idx}", opts, key=f"q_{idx}", label_visibility="collapsed")
            st.markdown("---")
        
        submitted_btn = st.form_submit_button("Submit and Grade")
        
        if submitted_btn:
            st.session_state.submitted = True
            st.session_state.user_answers = current_answers 
            st.rerun()

# --- 3. RESULTS INTERFACE ---
else:
    st.header("📊 Exam Results")
    
    score = 0
    correct_count = 0
    wrong_count = 0
    skipped_count = 0
    
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
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Final Score", f"{final_score} / {len(st.session_state.selected_questions)}")
    m2.metric("Correct", correct_count, delta_color="normal")
    m3.metric("Wrong", wrong_count, delta_color="inverse")
    m4.metric("Skipped", skipped_count, delta_color="off")
    
    st.divider()
    
    for idx, q in enumerate(st.session_state.selected_questions):
        col_left, col_right = st.columns([1, 1], gap="large")
        ans = st.session_state.user_answers.get(idx, "No answer")
        correct_opt = q['correct']
        
        with col_left:
            st.subheader(f"Q{idx+1} (ID: {q['id']})")
            st.info(q['text'])
            opts = ["No answer"] + [f"{k}) {v}" for k, v in q['options'].items()]
            try:
                sel_index = opts.index(ans)
            except ValueError:
                sel_index = 0
            st.radio(f"Res {idx}", opts, index=sel_index, disabled=True, key=f"res_radio_{idx}", label_visibility="collapsed")

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

            with st.expander("📖 Read Explanation / Motivation", expanded=True):
                st.markdown(f"_{q['motivation']}_")
        
        st.divider()

    if st.button("🔄 Restart Exam", type="primary"):
        st.session_state.exam_started = False
        st.session_state.submitted = False
        st.session_state.user_answers = {}
        st.rerun()