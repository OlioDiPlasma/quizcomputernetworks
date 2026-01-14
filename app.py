import streamlit as st
import re
import random
import time

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Simulazione Esame", layout="wide")

# Funzione per leggere le domande
@st.cache_data
def load_questions(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return []

    # Regex per separare le domande
    raw_questions = re.split(r'Question \d+', content)
    parsed_data = []
    
    for raw in raw_questions:
        if not raw.strip(): continue
        q_data = {}
        
        # Testo Domanda
        q_match = re.search(r'Question:\s*(.*?)\s*Option A:', raw, re.DOTALL)
        if not q_match: continue
        q_data['text'] = q_match.group(1).strip()
        
        # Opzioni
        options = {}
        for letter in ['A', 'B', 'C', 'D']:
            pattern = rf'Option {letter}:\s*(.*?)\s*(Option [A-D]:|Correct Answer:)'
            opt_match = re.search(pattern, raw, re.DOTALL)
            if opt_match:
                options[letter] = opt_match.group(1).strip()
        q_data['options'] = options
        
        # Risposta Corretta
        correct_match = re.search(r'Correct Answer:\s*([A-D])', raw)
        if correct_match: q_data['correct'] = correct_match.group(1).strip()
        
        # Motivazione
        motiv_match = re.search(r'Motivation:\s*(.*)', raw, re.DOTALL)
        q_data['motivation'] = motiv_match.group(1).strip() if motiv_match else ""
        
        parsed_data.append(q_data)
    return parsed_data

# --- STATO DELL'APP ---
if 'exam_started' not in st.session_state:
    st.session_state.exam_started = False
if 'selected_questions' not in st.session_state:
    st.session_state.selected_questions = []
if 'start_time' not in st.session_state:
    st.session_state.start_time = 0

# --- INTERFACCIA ---
st.title("🎓 Simulatore Esame")

questions_db = load_questions("domande.txt")

# MENU INIZIALE
if not st.session_state.exam_started:
    st.write(f"Domande nel database: **{len(questions_db)}**")
    st.info("Regole: +1 corretta, -0.33 errata, 0 saltata. Tempo: 60 min.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Test Rapido (10 domande)"):
            st.session_state.selected_questions = random.sample(questions_db, min(10, len(questions_db)))
            st.session_state.exam_started = True
            st.session_state.start_time = time.time()
            st.rerun()
    with col2:
        if st.button("📝 Esame Completo (33 domande)"):
            st.session_state.selected_questions = random.sample(questions_db, min(33, len(questions_db)))
            st.session_state.exam_started = True
            st.session_state.start_time = time.time()
            st.rerun()

# DURANTE L'ESAME
else:
    # Timer
    elapsed = time.time() - st.session_state.start_time
    remaining = 3600 - elapsed
    if remaining > 0:
        mins, secs = divmod(int(remaining), 60)
        st.sidebar.metric("⏳ Tempo Rimanente", f"{mins:02d}:{secs:02d}")
    else:
        st.sidebar.error("TEMPO SCADUTO!")

    with st.form("exam_form"):
        user_answers = {}
        for idx, q in enumerate(st.session_state.selected_questions):
            st.markdown(f"**{idx + 1}.** {q['text']}")
            # Opzioni radio
            opts = ["Non rispondere"] + [f"{k}) {v}" for k, v in q['options'].items()]
            user_answers[idx] = st.radio("Scegli:", opts, key=f"q_{idx}", label_visibility="collapsed")
            st.markdown("---")
        
        submitted = st.form_submit_button("Termina e Correggi")

    # RISULTATI
    if submitted:
        score = 0
        correct = 0
        wrong = 0
        
        st.header("📊 Risultati")
        for idx, q in enumerate(st.session_state.selected_questions):
            ans = user_answers[idx]
            correct_opt = q['correct']
            
            with st.expander(f"Domanda {idx+1}"):
                st.write(q['text'])
                if ans == "Non rispondere":
                    st.warning(f"⚪ Saltata. Risposta giusta: **{correct_opt}**")
                else:
                    letter = ans.split(")")[0]
                    if letter == correct_opt:
                        st.success(f"✅ Corretta! (+1)")
                        score += 1
                        correct += 1
                    else:
                        st.error(f"❌ Errata! (-0.33). Risposta giusta: **{correct_opt}**")
                        score -= 0.33
                        wrong += 1
                st.info(f"💡 Motivazione: {q['motivation']}")

        final = round(score, 2)
        st.metric("Punteggio Finale", f"{final} / {len(st.session_state.selected_questions)}")
        
        if st.button("Ricomincia"):
            st.session_state.exam_started = False
            st.rerun()