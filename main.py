import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
import tempfile
import os
from google.api_core import exceptions
import time
# Non è più necessario dotenv per Streamlit Sharing se si usano st.secrets
# from dotenv import load_dotenv

# Commento: Non è più necessario caricare da .env in questo modo su Streamlit Sharing
# Carica le variabili d'ambiente
# load_dotenv()

# --- Configurazione del modello Gemini AI usando st.secrets ---
try:
    # Recupera la chiave API dai segreti gestiti da Streamlit
    api_key = st.secrets["GEMINI_API_KEY"]
    if not api_key:
        st.error("Chiave API Gemini vuota trovata nei segreti di Streamlit. Assicurati che sia impostata correttamente.")
        st.stop()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

except KeyError:
    # Errore se la chiave non è definita nei segreti di Streamlit
    st.error("Chiave API Gemini ('GEMINI_API_KEY') non trovata nei segreti di Streamlit.")
    st.error("Vai su 'Manage app' (in basso a destra), poi 'Settings' -> 'Secrets' e aggiungi la tua chiave API: \nGEMINI_API_KEY = \"LA_TUA_CHIAVE_API\"")
    st.stop()
except Exception as e:
    # Cattura altri possibili errori durante la configurazione
    st.error(f"Si è verificato un errore durante la configurazione dell'API Gemini: {e}")
    st.stop()
# --- Fine Configurazione ---

MAX_RETRIES = 3
RETRY_DELAY = 2 # secondi

def analizza_referto_medico(contenuto, tipo_contenuto):
    """
    Invia il contenuto (immagine o testo) al modello Gemini per l'analisi.
    Gestisce i tentativi in caso di errore API.
    """
    prompt = "Analizza questo referto medico in modo conciso. Fornisci i principali risultati, diagnosi e raccomandazioni:"
    for tentativo in range(MAX_RETRIES):
        try:
            if tipo_contenuto == "immagine":
                # Assicurati che 'contenuto' sia un oggetto PIL.Image per Gemini
                risposta = model.generate_content([prompt, contenuto])
            else:  # testo
                risposta = model.generate_content(f"{prompt}\n\n{contenuto}")

            # Aggiungi suggerimenti generali
            suggerimenti = "\n\n---\n*Disclaimer: Questa è un'analisi generata da IA. Consulta sempre un medico per una diagnosi definitiva e un consiglio professionale.*\n*Suggerimenti generali:*\n- Verifica la diagnosi con uno specialista.\n- Segui attentamente le raccomandazioni riportate nel referto originale."
            return risposta.text + suggerimenti

        except exceptions.GoogleAPIError as e:
            st.warning(f"Errore API Google durante l'analisi (Tentativo {tentativo + 1}/{MAX_RETRIES}): {e}")
            if "quota" in str(e).lower():
                 st.error("Hai superato la quota API di Gemini. Controlla il tuo account Google Cloud o riprova più tardi.")
                 return "Errore: Quota API superata."
            if tentativo < MAX_RETRIES - 1:
                st.info(f"Nuovo tentativo tra {RETRY_DELAY} secondi...")
                time.sleep(RETRY_DELAY)
            else:
                st.error(f"Impossibile analizzare il referto dopo {MAX_RETRIES} tentativi a causa di errori API.")
                return analisi_fallback(contenuto, tipo_contenuto) # Usa il fallback solo dopo tutti i tentativi falliti
        except Exception as e:
             st.error(f"Si è verificato un errore imprevisto durante l'analisi: {str(e)}")
             return "Errore imprevisto durante l'analisi. Si prega di riprovare." # Fallback generico per altri errori

    # Se il loop finisce senza return (improbabile con l'except sopra, ma per sicurezza)
    st.error("Impossibile completare l'analisi dopo i tentativi.")
    return analisi_fallback(contenuto, tipo_contenuto)


def analisi_fallback(contenuto, tipo_contenuto):
    """
    Fornisce un'analisi di base se l'API Gemini fallisce ripetutamente.
    """
    st.warning("Utilizzo del metodo di analisi di fallback a causa di problemi con l'API principale.")
    if tipo_contenuto == "immagine":
        analisi = "Analisi di fallback: Impossibile analizzare l'immagine a causa di problemi con l'API. Si prega di consultare un professionista medico per un'interpretazione accurata."
    else: # testo
        try:
             numero_parole = len(contenuto.split())
             analisi = f"""
Analisi di fallback:
*   **Tipo:** Referto medico testuale.
*   **Lunghezza:** Circa {numero_parole} parole.
*   **Contenuto:** Il documento contiene informazioni mediche. L'analisi dettagliata tramite IA non è al momento disponibile.
*   **Raccomandazione:** Rivedere il documento manualmente o consultare un professionista sanitario per un'interpretazione e una diagnosi accurate.
*   **Nota:** Analisi semplificata a causa di indisponibilità del servizio AI.
"""
        except Exception: # Se 'contenuto' non è una stringa valida
             analisi = "Analisi di fallback: Impossibile elaborare il contenuto testuale fornito. Si prega di verificare il file PDF."

    # Aggiungi suggerimenti di fallback
    suggerimenti = "\n\n---\n*Disclaimer: Questa è un'analisi di fallback. Consulta sempre un medico.*\n*Suggerimenti di fallback:*\n- In caso di dubbio, consulta il tuo medico curante.\n- Se non sei sicuro della diagnosi, chiedi una seconda opinione medica."
    return analisi + suggerimenti


def estrai_testo_da_pdf(pdf_file_path):
    """
    Estrae il testo da un file PDF specificato dal percorso.
    """
    try:
        with open(pdf_file_path, 'rb') as file:
            lettore_pdf = PyPDF2.PdfReader(file)
            testo = ""
            for pagina in lettore_pdf.pages:
                testo_pagina = pagina.extract_text()
                if testo_pagina: # Aggiungi solo se l'estrazione ha avuto successo
                    testo += testo_pagina + "\n" # Aggiungi un a capo tra le pagine
            if not testo:
                 st.warning("Il PDF sembra essere vuoto o contenere solo immagini non scansionate (OCR non eseguito). L'analisi potrebbe non funzionare.")
            return testo
    except Exception as e:
        st.error(f"Errore durante l'estrazione del testo dal PDF: {e}")
        return None # Ritorna None in caso di errore


def main():
    st.set_page_config(page_title="Analizzatore Referti Medici IA", layout="wide")
    st.title("Analizzatore di Referti Medici Basato su IA (Gemini)")
    st.markdown("Carica un referto medico in formato immagine (JPG, PNG) o PDF per ottenere un'analisi preliminare concisa.")
    st.warning("⚠️ **Disclaimer:** Questo strumento fornisce un'analisi automatica e **non sostituisce il parere di un medico qualificato**. Usa i risultati come supporto informativo e consulta sempre un professionista sanitario per diagnosi e decisioni mediche.")

    tipo_file = st.radio(
        "Seleziona il tipo di file del referto:",
        ("Immagine", "PDF"),
        horizontal=True,
        key="tipo_file_radio"
    )

    file_caricato = None # Inizializza a None

    if tipo_file == "Immagine":
        file_caricato = st.file_uploader("🖼️ Carica un'immagine del referto", type=["jpg", "jpeg", "png"], key="uploader_img")
        if file_caricato is not None:
            try:
                # Usa direttamente i bytes del file caricato con PIL
                immagine = Image.open(file_caricato)
                st.image(immagine, caption="Referto Medico Caricato", use_container_width=True)

                if st.button("Analizza Immagine Referto", key="btn_analizza_img"):
                    with st.spinner("🔬 Analizzando l'immagine del referto..."):
                        analisi = analizza_referto_medico(immagine, "immagine")
                        st.subheader("Risultati dell'Analisi:")
                        st.markdown(analisi) # Usa markdown per una migliore formattazione

            except Exception as e:
                st.error(f"Errore durante il caricamento o la visualizzazione dell'immagine: {e}")

    elif tipo_file == "PDF":
        file_caricato = st.file_uploader("📄 Carica un referto medico in formato PDF", type=["pdf"], key="uploader_pdf")
        if file_caricato is not None:
            # Gestione del file temporaneo per PyPDF2
            percorso_tmp_file = None # Inizializza
            try:
                # Crea un file temporaneo sicuro
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(file_caricato.getvalue())
                    percorso_tmp_file = tmp_file.name # Salva il percorso

                st.success(f"PDF '{file_caricato.name}' caricato con successo.")

                if st.button("Analizza PDF Referto", key="btn_analizza_pdf"):
                    with st.spinner("🔬 Analizzando il testo del referto PDF..."):
                        # Estrai testo usando il percorso del file temporaneo
                        testo_pdf = estrai_testo_da_pdf(percorso_tmp_file)

                        if testo_pdf is not None: # Procedi solo se l'estrazione ha avuto successo
                            if testo_pdf.strip(): # Controlla se c'è testo effettivo
                                analisi = analizza_referto_medico(testo_pdf, "testo")
                                st.subheader("Risultati dell'Analisi:")
                                st.markdown(analisi) # Usa markdown
                            else:
                                st.warning("Non è stato possibile estrarre testo significativo dal PDF. Potrebbe contenere solo immagini o essere protetto.")
                        else:
                             st.error("Estrazione del testo dal PDF fallita. Impossibile procedere con l'analisi.")


            except Exception as e:
                st.error(f"Si è verificato un errore durante l'elaborazione del PDF: {e}")
            finally:
                # Assicurati che il file temporaneo venga eliminato in ogni caso
                if percorso_tmp_file and os.path.exists(percorso_tmp_file):
                    try:
                        os.unlink(percorso_tmp_file)
                    except Exception as e_unlink:
                         st.warning(f"Impossibile eliminare il file temporaneo {percorso_tmp_file}: {e_unlink}")

    else:
        st.info("Seleziona un tipo di file per iniziare.")

# Esegui la funzione principale solo se lo script è eseguito direttamente
if __name__ == "__main__":
    main()
