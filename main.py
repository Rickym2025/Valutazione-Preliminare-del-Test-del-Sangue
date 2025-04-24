import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
import tempfile
import os
from google.api_core import exceptions
from dotenv import load_dotenv
import time

# Carica le variabili d'ambiente
load_dotenv()

# Configura il modello Gemini AI
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("Chiave API Gemini non trovata. Per favore, imposta la variabile d'ambiente GEMINI_API_KEY.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

MAX_RETRIES = 3
RETRY_DELAY = 2  # secondi

def analizza_referto_medico(contenuto, tipo_contenuto):
    prompt = "Analizza questo referto medico in modo conciso. Fornisci i principali risultati, diagnosi e raccomandazioni:"
    
    for tentativo in range(MAX_RETRIES):
        try:
            if tipo_contenuto == "immagine":
                risposta = model.generate_content([prompt, contenuto])
            else:  # testo
                risposta = model.generate_content(f"{prompt}\n\n{contenuto}")
            
            # Aggiungi suggerimenti generali
            suggerimenti = "\n\nSuggerimenti:\n- Verifica la diagnosi con uno specialista.\n- Assicurati di seguire le raccomandazioni riportate nel referto."
            return risposta.text + suggerimenti
        except exceptions.GoogleAPIError as e:
            if tentativo < MAX_RETRIES - 1:
                st.warning(f"Si è verificato un errore. Nuovo tentativo tra {RETRY_DELAY} secondi... (Tentativo {tentativo + 1}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY)
            else:
                st.error(f"Impossibile analizzare il referto dopo {MAX_RETRIES} tentativi. Errore: {str(e)}")
                return analisi_fallback(contenuto, tipo_contenuto)

def analisi_fallback(contenuto, tipo_contenuto):
    st.warning("Utilizzo del metodo di analisi di fallback a causa di problemi con l'API.")
    if tipo_contenuto == "immagine":
        analisi = "Impossibile analizzare l'immagine a causa di problemi con l'API. Prova di nuovo più tardi o consulta un professionista medico per un'interpretazione accurata."
    else:  # testo
        numero_parole = len(contenuto.split())
        analisi = f"""
        Analisi di fallback:
        1. Tipo di documento: Referto medico basato su testo
        2. Numero di parole: Circa {numero_parole} parole
        3. Contenuto: Il documento sembra contenere informazioni mediche, ma l'analisi dettagliata non è disponibile a causa di problemi tecnici.
        4. Raccomandazione: Rivedi il documento manualmente o consulta un professionista sanitario per un'interpretazione accurata.
        5. Nota: Questa è un'analisi semplificata a causa dell'indisponibilità temporanea del servizio AI. Per un'analisi completa, prova di nuovo più tardi.
        """
    
    # Aggiungi suggerimenti di fallback
    suggerimenti = "\n\nSuggerimenti di fallback:\n- In caso di dubbio, consulta il tuo medico.\n- Se non sei sicuro della diagnosi, chiedi una seconda opinione."
    return analisi + suggerimenti

def estrai_testo_da_pdf(pdf_file):
    lettore_pdf = PyPDF2.PdfReader(pdf_file)
    testo = ""
    for pagina in lettore_pdf.pages:
        testo += pagina.extract_text()
    return testo

def main():
    st.title("Analizzatore di Referti Medici Basato su IA")
    st.write("Carica un referto medico (immagine o PDF) per l'analisi")

    tipo_file = st.radio("Seleziona il tipo di file:", ("Immagine", "PDF"))

    if tipo_file == "Immagine":
        file_caricato = st.file_uploader("Scegli un'immagine del referto medico", type=["jpg", "jpeg", "png"])
        if file_caricato is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                tmp_file.write(file_caricato.getvalue())
                percorso_tmp_file = tmp_file.name

            immagine = Image.open(percorso_tmp_file)
            st.image(immagine, caption="Referto Medico Caricato", use_container_width=True)

            if st.button("Analizza il Referto dell'Immagine"):
                with st.spinner("Analizzando il referto medico..."):
                    analisi = analizza_referto_medico(immagine, "immagine")
                    st.subheader("Risultati dell'Analisi:")
                    st.write(analisi)

            os.unlink(percorso_tmp_file)

    else:  # PDF
        file_caricato = st.file_uploader("Scegli un referto medico in formato PDF", type=["pdf"])
        if file_caricato is not None:
            st.write("PDF caricato con successo")

            if st.button("Analizza il Referto del PDF"):
                with st.spinner("Analizzando il referto medico..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(file_caricato.getvalue())
                        percorso_tmp_file = tmp_file.name

                    with open(percorso_tmp_file, 'rb') as pdf_file:
                        testo_pdf = estrai_testo_da_pdf(pdf_file)

                    analisi = analizza_referto_medico(testo_pdf, "testo")
                    st.subheader("Risultati dell'Analisi:")
                    st.write(analisi)

                    os.unlink(percorso_tmp_file)

if __name__ == "__main__":
    main()
