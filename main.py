# -*- coding: utf-8 -*-

# ==================================================
# IMPORT NECESSARI
# ==================================================
import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
import tempfile
import os
import time
from google.api_core import exceptions
from dotenv import load_dotenv

load_dotenv()

# ==================================================
# CONFIGURAZIONE PAGINA
# ==================================================
st.set_page_config(
    page_title="Valutazione Preliminare Analisi Del Sangue IA",
    page_icon="🩸",
    layout="wide"
)

# ==================================================
# CONFIGURAZIONE MODELLO (AGGIORNATO GEMINI 2.5)
# ==================================================
MODEL_NAME = 'gemini-2.5-flash' # <--- AGGIORNATO QUI

try:
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ Chiave API Gemini non trovata.")
        st.stop()

    genai.configure(api_key=api_key)
    # Nessuna configurazione complessa qui, la passiamo dopo nella funzione
except Exception as e:
    st.error(f"❌ Errore configurazione: {e}")
    st.stop()

# Impostazioni di sicurezza RILASSATE per termini medici
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]

MAX_RETRIES = 2

# ==================================================
# FUNZIONI HELPER
# ==================================================

def analizza_referto_medico(contenuto, tipo_contenuto):
    prompt = """
    Agisci come un assistente esperto nella lettura di dati biomedici. Analizza questo referto medico (analisi del sangue) in italiano.
    
    **⚠️ REGOLA FONDAMENTALE:** 
    NON FARE DIAGNOSI. Il tuo compito è solo estrarre e spiegare i dati.

    Genera un report strutturato ESATTAMENTE in questi 4 punti:

    **📊 1. Valori Fuori Norma:**
    *   Elenca SOLO i valori che sono esplicitamente segnati come "fuori range" (spesso con asterischi * o grassetto).
    *   Indica: Nome Esame | Valore Rilevato | Range di Riferimento.
    *   Se TUTTI i valori sono nella norma, scrivilo chiaramente.

    **⚠️ 2. Spiegazione Semplificata:**
    *   Per ogni valore fuori norma identificato sopra, spiega brevemente in parole semplici a cosa si riferisce.
    *   Usa un linguaggio condizionale: "Valori alti potrebbero indicare...", "Generalmente associato a...".

    **🩺 3. Note dal Referto:**
    *   Riporta eventuali note scritte dal laboratorio.

    **💡 4. Consigli Generici (Stile di Vita):**
    *   Fornisci 2-3 consigli molto generali sullo stile di vita (idratazione, sonno, dieta).
    *   NON consigliare farmaci.
    """

    for tentativo in range(MAX_RETRIES):
        try:
            # Creiamo il modello fresco ad ogni chiamata
            model = genai.GenerativeModel(MODEL_NAME)

            if tipo_contenuto == "immagine":
                risposta = model.generate_content([prompt, contenuto], safety_settings=SAFETY_SETTINGS)
            else: 
                input_content = f"{prompt}\n\n--- REFERTO ---\n{contenuto}"
                risposta = model.generate_content(input_content, safety_settings=SAFETY_SETTINGS)

            if hasattr(risposta, 'text') and risposta.text:
                disclaimer_app = "\n\n---\n**⚠️ DISCLAIMER:** *Analisi automatica IA (Gemini 2.5). Non sostituisce il medico.*"
                return risposta.text.strip() + disclaimer_app
            
            elif hasattr(risposta, 'prompt_feedback') and risposta.prompt_feedback.block_reason:
                 return f"⚠️ Analisi bloccata dai filtri di sicurezza: {risposta.prompt_feedback.block_reason}"
            
            time.sleep(1)

        except exceptions.GoogleAPIError as e:
            if "not found" in str(e).lower() or "404" in str(e):
                 return f"❌ Errore Modello: {MODEL_NAME} non trovato."
            time.sleep(1)
        except Exception as e:
             return f"❌ Errore imprevisto: {str(e)}"

    return "⚠️ Servizio momentaneamente non disponibile."

def estrai_testo_da_pdf(pdf_file_path):
    testo_completo = ""
    try:
        with open(pdf_file_path, 'rb') as file:
            lettore_pdf = PyPDF2.PdfReader(file)
            if lettore_pdf.is_encrypted:
                try: lettore_pdf.decrypt('')
                except: return None
            for pagina in lettore_pdf.pages:
                txt = pagina.extract_text()
                if txt: testo_completo += txt + "\n"
            return testo_completo if testo_completo.strip() else None
    except: return None

# ==================================================
# MAIN LOOP
# ==================================================
def main():
    if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None
    if 'processed_file_id' not in st.session_state: st.session_state.processed_file_id = None

    st.title("⚕️ Analisi Sangue IA (Gemini 2.5)")
    st.markdown("Carica il tuo referto per una lettura assistita.")
    st.warning("**DISCLAIMER:** L'IA può commettere errori. Consulta sempre il medico.")

    tipo_file = st.radio("Formato:", ("Immagine (JPG/PNG)", "Documento PDF"))
    
    file_caricato = None
    if tipo_file == "Immagine (JPG/PNG)":
        file_caricato = st.file_uploader("Carica foto", type=["jpg", "jpeg", "png"])
    else:
        file_caricato = st.file_uploader("Carica PDF", type=["pdf"])

    if file_caricato is not None:
        current_file_id = f"{file_caricato.name}_{file_caricato.size}"

        if current_file_id != st.session_state.processed_file_id:
            st.session_state.analysis_result = None
            st.session_state.processed_file_id = current_file_id
            
            analisi_output = None
            with st.spinner("⏳ Analisi Gemini 2.5 in corso..."):
                if tipo_file == "Immagine (JPG/PNG)":
                    try:
                        image = Image.open(file_caricato)
                        st.image(image, caption="Anteprima", use_container_width=True)
                        analisi_output = analizza_referto_medico(image, "immagine")
                    except Exception as e: st.error(f"Errore: {e}")

                elif tipo_file == "Documento PDF":
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                            tmp.write(file_caricato.getvalue())
                            path = tmp.name
                        testo = estrai_testo_da_pdf(path)
                        os.unlink(path)
                        if testo: analisi_output = analizza_referto_medico(testo, "testo")
                        else: analisi_output = "❌ PDF vuoto o illeggibile."
                    except Exception as e: st.error(f"Errore: {e}")

            st.session_state.analysis_result = analisi_output

        if st.session_state.analysis_result:
            st.markdown("---")
            st.subheader("✅ Risultato Analisi")
            st.markdown(st.session_state.analysis_result)

if __name__ == "__main__":
    main()
