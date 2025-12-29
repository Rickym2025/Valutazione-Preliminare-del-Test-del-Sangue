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
from google.api_core import exceptions
import time

# ==================================================
# CONFIGURAZIONE PAGINA
# ==================================================
st.set_page_config(
    page_title="Valutazione Preliminare Analisi Del Sangue IA",
    page_icon="🩸",
    layout="wide"
)

# ==================================================
# CONFIGURAZIONE MODELLO GEMINI (AGGIORNATO 2025)
# ==================================================
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    if not api_key:
        st.error("Chiave API Gemini vuota trovata nei segreti di Streamlit.")
        st.stop()
    
    # AGGIORNAMENTO 2025: Passaggio a gemini-2.5-flash
    # Se questo dovesse in futuro non funzionare, prova 'gemini-1.5-flash-latest' o 'gemini-pro'
    MODEL_NAME = 'gemini-2.5-flash' 
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

except KeyError:
    st.error("Chiave API Gemini ('GEMINI_API_KEY') non trovata nei segreti.")
    st.info("Imposta la chiave in .streamlit/secrets.toml")
    st.stop()
except Exception as e:
    st.error(f"Errore configurazione API: {e}")
    st.stop()

MAX_RETRIES = 3
RETRY_DELAY = 2

# ==================================================
# FUNZIONI HELPER
# ==================================================

def analizza_referto_medico(contenuto, tipo_contenuto):
    """
    Invia il contenuto a Gemini per un'analisi.
    """
    prompt = """
    Analizza questo referto medico (probabilmente analisi del sangue) in modo DETTAGLIATO e STRUTTURATO, in ITALIANO. 
    
    **OBIETTIVO:** Fornire una lettura chiara per il paziente, evidenziando solo ciò che è rilevante.
    **NON FARE DIAGNOSI MEDICHE.**

    Segui questa struttura rigorosa:

    **📊 1. Riassunto dei Risultati Chiave:**
        *   Elenca SOLO i valori **significativamente** fuori dagli intervalli di riferimento (asteriscati o grassettati nel referto).
        *   Se tutto è nella norma, scrivilo chiaramente.
        *   Riporta valore rilevato e intervallo di riferimento.

    **⚠️ 2. Potenziali Aree di Attenzione:**
        *   Spiega in termini semplici cosa *potrebbero* indicare i valori alterati (es. "ferro basso potrebbe indicare anemia", "glicemia alta riguarda il metabolismo degli zuccheri").
        *   Usa un linguaggio condizionale e cauto.

    **🩺 3. Eventuali Esami Aggiuntivi o Follow-up:**
        *   Includi questa sezione SOLO SE il referto stesso suggerisce ripetizioni o approfondimenti. Altrimenti OMETTI.

    **💡 4. Consigli Generali sullo Stile di Vita:**
        *   Dai 2-3 consigli generici basati sui risultati (es. bere più acqua, ridurre i grassi, attività fisica).
        *   NON prescrivere diete o farmaci.

    **(NON AGGIUNGERE NOTE FINALI O DISCLAIMER AGGIUNTIVI TUOI. L'applicazione ne ha già uno).**
    """

    for tentativo in range(MAX_RETRIES):
        try:
            # Configurazione di sicurezza per evitare blocchi eccessivi su dati medici
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
            ]

            if tipo_contenuto == "immagine":
                risposta = model.generate_content([prompt, contenuto], safety_settings=safety_settings)
            else:  # testo
                input_content = f"{prompt}\n\n--- REFERTO ---\n{contenuto}\n--- FINE REFERTO ---"
                risposta = model.generate_content(input_content, safety_settings=safety_settings)

            if hasattr(risposta, 'text') and risposta.text:
                disclaimer_finale_app = "\n\n---\n**⚠️⚠️ DISCLAIMER FINALE (DA APP) ⚠️⚠️**\n*Ricorda: questa analisi è **AUTOMATICA** e **NON SOSTITUISCE IL MEDICO**. Consulta SEMPRE il tuo medico.*"
                return risposta.text.strip() + disclaimer_finale_app
            
            elif hasattr(risposta, 'prompt_feedback') and risposta.prompt_feedback.block_reason:
                 return f"Errore: L'analisi è stata bloccata dai filtri di sicurezza dell'IA (Motivo: {risposta.prompt_feedback.block_reason}). Prova con un'immagine più nitida."
            
            else:
                st.warning(f"Risposta vuota dall'IA (Tentativo {tentativo + 1}).")
                time.sleep(RETRY_DELAY)

        except exceptions.GoogleAPIError as e:
            if "quota" in str(e).lower() or "429" in str(e):
                 return "Errore: Quota API superata o servizio momentaneamente non disponibile."
            if "not found" in str(e).lower() or "404" in str(e):
                 return f"Errore Modello: Il modello '{MODEL_NAME}' non è disponibile o è stato deprecato. Controlla il codice."
            
            time.sleep(RETRY_DELAY)
        except Exception as e:
             return f"Errore imprevisto: {str(e)}"

    return analisi_fallback(contenuto, tipo_contenuto)


def analisi_fallback(contenuto, tipo_contenuto):
    st.warning("⚠️ Analisi IA dettagliata fallita. Modalità fallback.")
    return """
    **Analisi di Fallback**
    
    Il sistema non è riuscito a elaborare il referto con l'intelligenza artificiale avanzata in questo momento.
    
    *   **Consiglio:** Verifica che l'immagine sia leggibile o che il PDF contenga testo selezionabile.
    *   **Azione:** Porta questo referto al tuo medico curante per una lettura corretta.
    """

def estrai_testo_da_pdf(pdf_file_path):
    testo_completo = ""
    try:
        with open(pdf_file_path, 'rb') as file:
            lettore_pdf = PyPDF2.PdfReader(file)
            if lettore_pdf.is_encrypted:
                 try:
                     lettore_pdf.decrypt('')
                 except:
                     return None
            for pagina in lettore_pdf.pages:
                t = pagina.extract_text()
                if t: testo_completo += t + "\n"
            return testo_completo if testo_completo.strip() else None
    except Exception as e:
        st.error(f"Errore PDF: {e}")
        return None

# ==================================================
# MAIN
# ==================================================
def main():
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'processed_file_id' not in st.session_state:
        st.session_state.processed_file_id = None

    # HEADER
    st.title("⚕️ Analisi Preliminare Sangue IA (2025 Updated)")
    st.markdown("Carica il referto (Immagine o PDF) per una valutazione strutturata.")
    
    st.warning("""
    **ATTENZIONE:** Questo strumento usa l'IA per leggere i dati, ma **NON È UN MEDICO**. 
    Errori di lettura sono possibili (allucinazioni). **Consulta sempre il medico.**
    """)

    # SELEZIONE
    tipo_file = st.radio("Formato:", ("Immagine (JPG, PNG)", "Documento PDF"), horizontal=True)

    # UPLOAD
    file_caricato = None
    if tipo_file == "Immagine (JPG, PNG)":
        file_caricato = st.file_uploader("Carica Immagine", type=["jpg", "jpeg", "png"])
    else:
        file_caricato = st.file_uploader("Carica PDF", type=["pdf"])

    # LOGICA ANALISI
    if file_caricato is not None:
        current_file_id = f"{file_caricato.name}_{file_caricato.size}"

        # Se è un nuovo file, analizza
        if current_file_id != st.session_state.processed_file_id:
            st.session_state.analysis_result = None
            st.session_state.processed_file_id = current_file_id
            
            analisi_output = None
            
            with st.spinner("⏳ Analisi in corso con Gemini 2.5..."):
                if tipo_file == "Immagine (JPG, PNG)":
                    try:
                        img = Image.open(file_caricato)
                        st.image(img, caption="Referto", use_container_width=True)
                        analisi_output = analizza_referto_medico(img, "immagine")
                    except Exception as e:
                        st.error(f"Errore immagine: {e}")
                
                elif tipo_file == "Documento PDF":
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                            tmp.write(file_caricato.getvalue())
                            path = tmp.name
                        
                        text = estrai_testo_da_pdf(path)
                        if text:
                            analisi_output = analizza_referto_medico(text, "testo")
                        else:
                            st.error("Nessun testo trovato nel PDF (potrebbe essere una scansione immagine).")
                        
                        os.unlink(path)
                    except Exception as e:
                        st.error(f"Errore PDF: {e}")

            st.session_state.analysis_result = analisi_output

        # MOSTRA RISULTATO (Se presente in session state)
        if st.session_state.analysis_result:
            st.markdown("---")
            st.subheader("✅ Risultato Analisi")
            st.markdown(st.session_state.analysis_result)

if __name__ == "__main__":
    main()
