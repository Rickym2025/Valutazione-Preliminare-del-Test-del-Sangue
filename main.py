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

# Carica variabili d'ambiente (utile per uso locale con .env)
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
# CONFIGURAZIONE MODELLO GEMINI
# ==================================================
# Nome del modello da utilizzare. 
# 'gemini-1.5-flash' è ottimo per il piano gratuito e supporta immagini.
MODEL_NAME = 'gemini-1.5-flash'

try:
    # Tenta di recuperare la chiave dai Secrets di Streamlit o dall'ambiente
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.error("❌ Chiave API Gemini non trovata.")
        st.info("Assicurati di aver impostato 'GEMINI_API_KEY' nei Secrets di Streamlit o nel file .env")
        st.stop()

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

except Exception as e:
    st.error(f"❌ Errore critico nella configurazione dell'API: {e}")
    st.stop()

# Impostazioni di sicurezza: Rilassiamo i filtri per evitare blocchi su termini medici
# (es. "sangue", "infezione" potrebbero attivare filtri di sicurezza standard)
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]

MAX_RETRIES = 3
RETRY_DELAY = 2

# ==================================================
# FUNZIONI HELPER
# ==================================================

def analizza_referto_medico(contenuto, tipo_contenuto):
    """
    Invia il contenuto a Gemini per un'analisi strutturata.
    """
    prompt = """
    Agisci come un assistente esperto nella lettura di dati biomedici. Analizza questo referto medico (analisi del sangue) in italiano.
    
    **⚠️ REGOLA FONDAMENTALE:** 
    NON FARE DIAGNOSI. Il tuo compito è solo estrarre e spiegare i dati. Se non sei sicuro, dillo.

    Genera un report strutturato ESATTAMENTE in questi 4 punti:

    **📊 1. Valori Fuori Norma:**
    *   Elenca SOLO i valori che sono esplicitamente segnati come "fuori range" (spesso con asterischi * o grassetto).
    *   Indica: Nome Esame | Valore Rilevato | Range di Riferimento.
    *   Se TUTTI i valori sono nella norma, scrivilo chiaramente.

    **⚠️ 2. Spiegazione Semplificata:**
    *   Per ogni valore fuori norma identificato sopra, spiega brevemente in parole semplici a cosa si riferisce quel parametro (es. "L'emoglobina trasporta l'ossigeno...").
    *   Usa un linguaggio condizionale: "Valori alti potrebbero indicare...", "Generalmente associato a...".

    **🩺 3. Note dal Referto:**
    *   Riporta eventuali note o commenti scritti esplicitamente dal laboratorio sul foglio (es. "Campione emolizzato", "Si consiglia ripetizione").

    **💡 4. Consigli Generici (Stile di Vita):**
    *   Fornisci 2-3 consigli molto generali sullo stile di vita basati sui sistemi coinvolti (es. idratazione, sonno, dieta varia).
    *   NON consigliare farmaci o integratori.

    Termina l'analisi.
    """

    for tentativo in range(MAX_RETRIES):
        try:
            if tipo_contenuto == "immagine":
                # Invio Prompt + Oggetto Immagine
                risposta = model.generate_content([prompt, contenuto], safety_settings=SAFETY_SETTINGS)
            else: 
                # Invio Prompt + Testo PDF
                input_content = f"{prompt}\n\n--- INIZIO REFERTO ---\n{contenuto}\n--- FINE REFERTO ---"
                risposta = model.generate_content(input_content, safety_settings=SAFETY_SETTINGS)

            if hasattr(risposta, 'text') and risposta.text:
                disclaimer_app = "\n\n---\n**⚠️ DISCLAIMER APP:** *Questa analisi è generata dall'Intelligenza Artificiale. Potrebbe contenere errori o 'allucinazioni'. Non sostituisce il parere del tuo medico.*"
                return risposta.text.strip() + disclaimer_app
            
            # Gestione caso in cui l'AI blocca la risposta
            elif hasattr(risposta, 'prompt_feedback') and risposta.prompt_feedback.block_reason:
                 return f"⚠️ Analisi bloccata dai filtri di sicurezza (Motivo: {risposta.prompt_feedback.block_reason}). Prova a ritagliare l'immagine solo sui dati numerici."
            
            else:
                st.warning(f"Risposta vuota dall'IA (Tentativo {tentativo + 1}). Riprovo...")
                time.sleep(RETRY_DELAY)

        except exceptions.GoogleAPIError as e:
            # Gestione errori specifici API
            err_msg = str(e).lower()
            if "quota" in err_msg or "429" in err_msg:
                 return "❌ Errore: Quota API gratuita superata per oggi. Riprova più tardi."
            if "not found" in err_msg or "404" in err_msg:
                 return f"❌ Errore Modello: Il modello '{MODEL_NAME}' non sembra disponibile. Controlla la configurazione."
            
            st.warning(f"Errore API momentaneo: {e}. Riprovo...")
            time.sleep(RETRY_DELAY)
            
        except Exception as e:
             return f"❌ Errore imprevisto: {str(e)}"

    return "⚠️ Impossibile completare l'analisi dopo vari tentativi. Il servizio potrebbe essere momentaneamente non disponibile."


def estrai_testo_da_pdf(pdf_file_path):
    """Estrae testo da un PDF temporaneo."""
    testo_completo = ""
    try:
        with open(pdf_file_path, 'rb') as file:
            lettore_pdf = PyPDF2.PdfReader(file)
            
            # Gestione PDF criptati (tentativo base)
            if lettore_pdf.is_encrypted:
                try:
                    lettore_pdf.decrypt('')
                except:
                    st.error("Il PDF è protetto da password e non può essere letto.")
                    return None

            for pagina in lettore_pdf.pages:
                txt = pagina.extract_text()
                if txt:
                    testo_completo += txt + "\n"
            
            if not testo_completo.strip():
                st.warning("⚠️ Il PDF sembra vuoto o è una scansione (immagine dentro PDF). Per le scansioni, converti in JPG o usa un PDF testuale.")
                return None
            
            return testo_completo
    except Exception as e:
        st.error(f"Errore nella lettura del PDF: {e}")
        return None

# ==================================================
# MAIN LOOP
# ==================================================
def main():
    # Gestione stato sessione per non perdere i dati al ricaricamento
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'processed_file_id' not in st.session_state:
        st.session_state.processed_file_id = None

    # --- Header ---
    st.title("⚕️ Valutazione Preliminare Sangue IA")
    st.markdown("Carica il tuo referto per una lettura assistita dall'Intelligenza Artificiale.")
    st.info("ℹ️ **Modello in uso:** Gemini 1.5 Flash (Veloce & Gratuito)")

    # --- Disclaimer Principale ---
    st.warning("""
    **🛑 DISCLAIMER MEDICO**
    Questa applicazione NON è un medico. L'IA può commettere errori di lettura o interpretazione.
    **Non prendere decisioni mediche basate su questi risultati.** Mostra sempre il referto originale al tuo medico.
    """)

    # --- Selezione Tipo File ---
    col1, col2 = st.columns([1, 2])
    with col1:
        tipo_file = st.radio("Seleziona formato:", ("Immagine (JPG/PNG)", "Documento PDF"))

    # --- Upload File ---
    file_caricato = None
    if tipo_file == "Immagine (JPG/PNG)":
        file_caricato = st.file_uploader("Carica foto del referto", type=["jpg", "jpeg", "png"])
    else:
        file_caricato = st.file_uploader("Carica file PDF", type=["pdf"])

    # --- Logica di Elaborazione ---
    if file_caricato is not None:
        # Creiamo un ID unico per il file per evitare di ri-analizzare lo stesso file se l'utente clicca altro
        current_file_id = f"{file_caricato.name}_{file_caricato.size}"

        if current_file_id != st.session_state.processed_file_id:
            # Nuovo file rilevato: resetto e analizzo
            st.session_state.analysis_result = None
            st.session_state.processed_file_id = current_file_id
            
            analisi_output = None
            
            with st.spinner("⏳ Analisi IA in corso... attendere..."):
                
                # CASO 1: IMMAGINE
                if tipo_file == "Immagine (JPG/PNG)":
                    try:
                        image = Image.open(file_caricato)
                        st.image(image, caption="Referto Caricato", use_container_width=True)
                        analisi_output = analizza_referto_medico(image, "immagine")
                    except Exception as e:
                        st.error(f"Errore apertura immagine: {e}")

                # CASO 2: PDF
                elif tipo_file == "Documento PDF":
                    try:
                        # Salvataggio temporaneo necessario per PyPDF2
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(file_caricato.getvalue())
                            tmp_path = tmp_file.name
                        
                        testo_pdf = estrai_testo_da_pdf(tmp_path)
                        
                        # Pulizia file temporaneo
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)

                        if testo_pdf:
                            analisi_output = analizza_referto_medico(testo_pdf, "testo")
                        else:
                            analisi_output = "❌ Impossibile estrarre testo dal PDF. Assicurati che non sia una scansione (immagine)."
                            
                    except Exception as e:
                        st.error(f"Errore gestione PDF: {e}")

            # Salvo il risultato in sessione
            st.session_state.analysis_result = analisi_output

        # --- Visualizzazione Risultati ---
        if st.session_state.analysis_result:
            st.markdown("---")
            st.subheader("✅ Risultato Analisi")
            st.markdown(st.session_state.analysis_result)
            
            # Bottone per resettare
            if st.button("Carica un altro referto"):
                st.session_state.analysis_result = None
                st.session_state.processed_file_id = None
                st.rerun()

if __name__ == "__main__":
    main()
