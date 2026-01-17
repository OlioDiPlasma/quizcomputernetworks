import streamlit as st
import re
import random

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
    .last-result-box {
        padding: 15px;
        background-color: #f0f2f6;
        border-left: 5px solid #4CAF50;
        border-radius: 5px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- PARSING FUNCTIONS ---
@st.cache_data
def load_questions(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return []

    parts = re.split(r'Question (\d+)', content)
    parsed_data = []
    
    for i in range(1, len(parts), 2):
        q_id = parts[i].strip()
        raw = parts[i+1]
        
        if not raw.strip(): continue
        q_data = {}
        q_data['id'] = q_id
        
        # Regex per catturare il testo della domanda
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

@st.cache_data
def load_categories(filename):
    categories = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return {}

    current_cat = "Uncategorized"
    
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.endswith(':'):
            current_cat = line[:-1].strip()
            if current_cat not in categories:
                categories[current_cat] = []
        else:
            ids = re.findall(r'\d+', line)
            if ids:
                if current_cat not in categories:
                    categories[current_cat] = []
                categories[current_cat].extend(ids)
                
    return categories

# --- APP STATE ---
if 'exam_started' not in st.session_state:
    st.session_state.exam_started = False
if 'selected_questions' not in st.session_state:
    st.session_state.selected_questions = []
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'seen_ids' not in st.session_state:
    st.session_state.seen_ids = set()
if 'last_result' not in st.session_state:
    st.session_state.last_result = None
if 'current_exam_label' not in st.session_state:
    st.session_state.current_exam_label = ""

# --- INTERFACE ---
st.title("🎓 Computer Networks Exam Simulator")

# CARICAMENTO DATI
questions_db = load_questions("domande.txt")
extra_db = load_questions("domextra.txt")
categories_db = load_categories("categorie.txt")

# --- 1. START MENU ---
if not st.session_state.exam_started:
    
    # --- MOSTRA ULTIMO RISULTATO ---
    if st.session_state.last_result:
        res = st.session_state.last_result
        st.markdown(f"""
        <div class="last-result-box">
            <h4>🏆 Last Exam Session</h4>
            <p><b>Score:</b> {res['score']} / {res['total']}</p>
            <p><b>Context:</b> {res['label']}</p>
        </div>
        """, unsafe_allow_html=True)

    # --- CONFIGURATION SECTION ---
    st.markdown("### ⚙️ Exam Configuration")
    
    col_config1, col_config2 = st.columns([1, 2])
    
    with col_config1:
        mode = st.radio("Select Mode:", [
            "Random (All Questions)", 
            "By Category", 
            "Sequential (Chunks of 33)", 
            "Extra Questions (Separate Pool)"
        ])
        
        st.markdown("---")
        # CHECKBOX PER ATTIVARE/DISATTIVARE LO SHUFFLE
        shuffle_enabled = st.checkbox("🔀 Shuffle Answers", value=False, help="Randomize the order of options (A, B, C, D) to prevent memorizing positions.")
    
    selected_pool = []
    current_label = "Random Mode" 
    
    with col_config2:
        # --- A. LOGICA PER CATEGORIE ---
        if mode == "By Category" and categories_db:
            selected_cats = st.multiselect("Select Categories:", list(categories_db.keys()))
            if selected_cats:
                allowed_ids = set()
                for cat in selected_cats:
                    allowed_ids.update(categories_db[cat])
                selected_pool = [q for q in questions_db if q['id'] in allowed_ids]
                current_label = f"Category: {len(selected_cats)} selected"
            else:
                st.warning("Please select at least one category.")
                current_label = "No Category Selected"

        # --- B. LOGICA SEQUENTIAL (CHUNKS) ---
        elif mode == "Sequential (Chunks of 33)":
            chunk_size = 33
            total_qs = len(questions_db)
            if total_qs > 0:
                num_chunks = (total_qs + chunk_size - 1) // chunk_size 
                chunk_options = [f"Part {i+1} ({i*chunk_size+1}-{min((i+1)*chunk_size, total_qs)})" for i in range(num_chunks)]
                selected_chunk_label = st.selectbox("Select Exam Part:", chunk_options)
                
                chunk_idx = chunk_options.index(selected_chunk_label)
                start_slice = chunk_idx * chunk_size
                end_slice = start_slice + chunk_size
                selected_pool = questions_db[start_slice:end_slice]
                current_label = f"Sequential: {selected_chunk_label}"
            else:
                st.error("Main database is empty.")

        # --- C. LOGICA EXTRA QUESTIONS ---
        elif mode == "Extra Questions (Separate Pool)":
            selected_pool = []
            if extra_db:
                for q in extra_db:
                    q_copy = q.copy() 
                    q_copy['id'] = f"{q['id']}E"
                    selected_pool.append(q_copy)
                current_label = "Extra Questions (Random Mode)"
            else:
                st.warning("File 'domextra.txt' not found or empty.")

        # --- D. LOGICA RANDOM CLASSICA ---
        else:
            selected_pool = questions_db
            current_label = "Random Mode (All Topics)"

    # --- MEMORY STATS ---
    if len(selected_pool) > 0:
        pool_ids = set(q['id'] for q in selected_pool)
        seen_in_pool = len(pool_ids.intersection(st.session_state.seen_ids))
        remaining = len(selected_pool) - seen_in_pool
        
        st.caption(f"📊 Stats for selection: Total **{len(selected_pool)}** | Seen: **{seen_in_pool}** | Unseen: **{remaining}**")
        
        if seen_in_pool > 0:
            if st.button("🧹 Reset Memory (Forget seen questions)"):
                st.session_state.seen_ids = set()
                st.rerun()

    st.divider()
    st.write("Rules: +1 correct, -0.33 wrong, 0 skipped.")
    
    # --- ACTION BUTTONS ---
    col1, col2 = st.columns(2)
    disable_start = len(selected_pool) == 0

    def start_exam(n, pool, label_text, do_shuffle):
        if len(pool) == 0:
            st.error("No questions available!")
            return
        
        if n > len(pool):
            st.toast(f"⚠️ Pool has only {len(pool)} questions. Exam reduced to {len(pool)}.")
            n = len(pool)
        
        st.session_state.current_exam_label = label_text

        # 1. Separa le domande (Seen vs Unseen)
        unseen_qs = [q for q in pool if q['id'] not in st.session_state.seen_ids]
        seen_qs = [q for q in pool if q['id'] in st.session_state.seen_ids]
        
        selection_raw = []
        
        # 2. Logica di riempimento (Priorità alle Unseen)
        if len(unseen_qs) >= n:
            selection_raw = random.sample(unseen_qs, n)
        else:
            selection_raw = unseen_qs[:]
            needed = n - len(unseen_qs)
            if needed > 0:
                selection_raw += random.sample(seen_qs, needed)
                st.toast(f"⚠️ Only {len(unseen_qs)} new questions available. Added {needed} older ones.")
        
        # 3. Mescolamento Opzioni (Opzionale) e Tagging
        final_selection = []
        for q in selection_raw:
            q_copy = q.copy()
            
            # --- SHUFFLE LOGIC ---
            if do_shuffle:
                original_opts = q['options']
                correct_key = q['correct'] 
                correct_text = original_opts.get(correct_key)
                
                opt_texts = list(original_opts.values())
                random.shuffle(opt_texts)
                
                new_options = {}
                new_correct_key = correct_key 
                mapping_keys = ['A', 'B', 'C', 'D']
                
                for i, text in enumerate(opt_texts):
                    if i < len(mapping_keys):
                        key = mapping_keys[i]
                        new_options[key] = text
                        if text == correct_text:
                            new_correct_key = key
                
                q_copy['options'] = new_options
                q_copy['correct'] = new_correct_key
            # ---------------------

            if q['id'] in st.session_state.seen_ids:
                q_copy['status_tag'] = "OLD"
            else:
                q_copy['status_tag'] = "NEW"
            final_selection.append(q_copy)

        # 4. Aggiorna la memoria globale
        for q in final_selection:
            st.session_state.seen_ids.add(q['id'])

        st.session_state.selected_questions = final_selection
        st.session_state.exam_started = True
        st.session_state.submitted = False
        st.rerun()

    with col1:
        if st.button("🚀 Quick Test (10 questions)", disabled=disable_start, type="primary"):
            start_exam(10, selected_pool, current_label, shuffle_enabled)
    with col2:
        if st.button("📝 Full Exam (33 questions)", disabled=disable_start):
            start_exam(33, selected_pool, current_label, shuffle_enabled)

# --- 2. EXAM INTERFACE ---
elif not st.session_state.submitted:
    with st.form("exam_form"):
        st.write(f"### Exam in progress: {st.session_state.current_exam_label}")
        
        current_answers = {}
        for idx, q in enumerate(st.session_state.selected_questions):
            
            if q.get('status_tag') == "NEW":
                badge = "<span style='background-color:#d4edda; color:#155724; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold;'>✨ NEW</span>"
            else:
                badge = "<span style='background-color:#fff3cd; color:#856404; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold;'>♻️ REVISION</span>"
            
            st.markdown(f"**{idx + 1}.** {badge} <span style='color:gray; font-size:0.9em'>(ID: {q['id']})</span> &nbsp; {q['text']}", unsafe_allow_html=True)
            
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
    max_score = len(st.session_state.selected_questions)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Final Score", f"{final_score} / {max_score}")
    m2.metric("Correct", correct_count, delta_color="normal")
    m3.metric("Wrong", wrong_count, delta_color="inverse")
    m4.metric("Skipped", skipped_count, delta_color="off")
    
    st.divider()
    
    for idx, q in enumerate(st.session_state.selected_questions):
        col_left, col_right = st.columns([1, 1], gap="large")
        ans = st.session_state.user_answers.get(idx, "No answer")
        correct_opt = q['correct']
        
        with col_left:
            if q.get('status_tag') == "NEW":
                badge = "<span style='background-color:#d4edda; color:#155724; padding: 2px 6px; border-radius: 4px; font-size: 0.7em;'>NEW</span>"
            else:
                badge = "<span style='background-color:#fff3cd; color:#856404; padding: 2px 6px; border-radius: 4px; font-size: 0.7em;'>REV</span>"

            st.markdown(f"### Q{idx+1} {badge} <span style='font-size:0.8em; color:gray'>(ID: {q['id']})</span>", unsafe_allow_html=True)
            
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
        # --- SALVATAGGIO DATI PRIMA DEL RESET ---
        st.session_state.last_result = {
            "score": final_score,
            "total": max_score,
            "label": st.session_state.current_exam_label
        }
        # ----------------------------------------
        
        st.session_state.exam_started = False
        st.session_state.submitted = False
        st.session_state.user_answers = {}
        st.session_state.selected_questions = []
        st.rerun()