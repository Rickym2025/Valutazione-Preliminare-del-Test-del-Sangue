import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
import tempfile
import os
from google.api_core import exceptions
import time

# --- Configurazione Pagina Streamlit ---
st.set_page_config(
    page_title="Analizzatore Referti Medici IA",
    page_icon="⚕️",  # Icona medica come favicon
    layout="wide" # Usa l'intera larghezza
)

# --- Configurazione del modello Gemini AI usando st.secrets ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    if not api_key:
        st.error("Chiave API Gemini vuota trovata nei segreti di Streamlit. Assicurati che sia impostata correttamente.")
        st.stop()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

except KeyError:
    st.error("Chiave API Gemini ('GEMINI_API_KEY') non trovata nei segreti di Streamlit.")
    st.error("Vai su 'Manage app' (in basso a destra), poi 'Settings' -> 'Secrets' e aggiungi la tua chiave API: \nGEMINI_API_KEY = \"LA_TUA_CHIAVE_API\"")
    st.stop()
except Exception as e:
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
    prompt = "Analizza questo referto medico in modo conciso e strutturato. Fornisci: 1. Principali Risultati (valori chiave, osservazioni). 2. Possibile Diagnosi o Interpretazione (se menzionata/deducibile). 3. Raccomandazioni (come indicate nel referto). Sii chiaro e usa elenchi puntati se appropriato."
    for tentativo in range(MAX_RETRIES):
        try:
            if tipo_contenuto == "immagine":
                risposta = model.generate_content([prompt, contenuto])
            else:  # testo
                risposta = model.generate_content(f"{prompt}\n\n--- REFERTO ---\n{contenuto}\n--- FINE REFERTO ---")

            # Aggiungi disclaimer e suggerimenti
            disclaimer = "\n\n---\n**⚠️ Disclaimer Importante:** *Questa è un'analisi preliminare generata da Intelligenza Artificiale. Non sostituisce in alcun modo il parere di un medico qualificato. Consulta sempre il tuo medico o uno specialista per una diagnosi accurata, interpretazione completa e decisioni terapeutiche.*"
            suggerimenti = "\n\n*Suggerimenti generali:*\n- Confronta questa analisi con il referto originale.\n- Discuti i risultati e le raccomandazioni con il tuo medico.\n- Segui attentamente le indicazioni terapeutiche fornite dai professionisti sanitari."
            return risposta.text + disclaimer + suggerimenti

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
                return analisi_fallback(contenuto, tipo_contenuto)
        except Exception as e:
             st.error(f"Si è verificato un errore imprevisto durante l'analisi: {str(e)}")
             return "Errore imprevisto durante l'analisi. Si prega di riprovare."

    st.error("Impossibile completare l'analisi dopo i tentativi.")
    return analisi_fallback(contenuto, tipo_contenuto)


def analisi_fallback(contenuto, tipo_contenuto):
    """
    Fornisce un'analisi di base se l'API Gemini fallisce ripetutamente.
    """
    st.warning("⚠️ Attenzione: Utilizzo del metodo di analisi di fallback a causa di problemi con l'API principale.")
    if tipo_contenuto == "immagine":
        analisi = "Analisi di fallback: Impossibile analizzare l'immagine a causa di problemi tecnici con l'API. Si prega di consultare un professionista medico per un'interpretazione accurata."
    else: # testo
        try:
             numero_parole = len(contenuto.split())
             analisi = f"""
Analisi di fallback:
*   **Tipo:** Referto medico testuale.
*   **Lunghezza:** Circa {numero_parole} parole.
*   **Contenuto:** Il documento contiene informazioni mediche. L'analisi dettagliata tramite IA non è al momento disponibile.
*   **Raccomandazione:** Rivedere il documento manualmente o **consultare un professionista sanitario** per un'interpretazione e una diagnosi accurate.
*   **Nota:** Analisi semplificata a causa di indisponibilità temporanea del servizio AI.
"""
        except Exception:
             analisi = "Analisi di fallback: Impossibile elaborare il contenuto testuale fornito. Si prega di verificare il file PDF."

    disclaimer = "\n\n---\n**⚠️ Disclaimer Importante:** *Questa è un'analisi di fallback. Consulta sempre il tuo medico per interpretazioni e decisioni mediche.*"
    suggerimenti = "\n\n*Suggerimenti di fallback:*\n- In caso di dubbio, contatta il tuo medico curante.\n- Chiedi una seconda opinione medica se necessario."
    return analisi + disclaimer + suggerimenti


def estrai_testo_da_pdf(pdf_file_path):
    """
    Estrae il testo da un file PDF specificato dal percorso.
    """
    try:
        with open(pdf_file_path, 'rb') as file:
            lettore_pdf = PyPDF2.PdfReader(file)
            if lettore_pdf.is_encrypted:
                 st.warning("Il PDF è criptato e potrebbe non essere possibile estrarre il testo.")
                 # Prova a decriptarlo se non ha password (a volte funziona)
                 try:
                      lettore_pdf.decrypt('')
                 except Exception as decrypt_err:
                      st.error(f"Impossibile decriptare il PDF: {decrypt_err}")
                      return None

            testo = ""
            for i, pagina in enumerate(lettore_pdf.pages):
                try:
                    testo_pagina = pagina.extract_text()
                    if testo_pagina:
                        testo += testo_pagina + "\n"
                    # else:
                    #    st.info(f"Nessun testo estratto dalla pagina {i+1}. Potrebbe essere un'immagine.")
                except Exception as page_err:
                     st.warning(f"Errore durante l'estrazione della pagina {i+1}: {page_err}")

            if not testo.strip():
                 st.warning("Non è stato possibile estrarre testo dal PDF. Potrebbe contenere solo immagini (scansione senza OCR) o essere vuoto/corrotto.")
                 return None # Ritorna None se nessun testo è stato estratto
            return testo
    except Exception as e:
        st.error(f"Errore critico durante l'apertura o lettura del PDF: {e}")
        return None


def main():
    # --- Header ---
    st.title("⚕️ Analizzatore Referti Medici IA")
    st.markdown("Carica il tuo referto medico (immagine o PDF) per ottenere un'analisi preliminare e concisa basata su IA.")
    st.markdown("---")

    # --- Disclaimer Principale ---
    st.warning("""
    **⚠️ ATTENZIONE: Strumento Informativo, NON Diagnostico!**
    Questa applicazione fornisce un riassunto automatico e **non sostituisce MAI** il parere, la diagnosi o il trattamento di un medico qualificato.
    Utilizza i risultati solo come **supporto informativo** e **consulta SEMPRE il tuo medico** per qualsiasi decisione riguardante la tua salute.
    """)
    st.markdown("---")

    # --- Selezione Tipo File ---
    st.subheader("1. Seleziona il tipo di referto")
    tipo_file = st.radio(
        "Che tipo di file vuoi caricare?",
        ("Immagine (JPG, PNG)", "Documento PDF"),
        horizontal=True,
        key="tipo_file_radio",
        label_visibility="collapsed" # Nasconde l'etichetta "Che tipo..." che è già nel subheader
    )
    st.markdown("---")


    file_caricato = None
    placeholder_img_url = "https://images.unsplash.com/photo-1584515933487-75a87d24c8e7?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8bWVkaWNhbCUyMHJlcG9ydHxlbnwwfHwwfHx8MA%3D%3D&auto=format&fit=crop&w=500&q=60" # URL di un'immagine generica (sostituire se necessario)

    # --- Logica di Upload e Analisi ---
    if tipo_file == "Immagine (JPG, PNG)":
        st.subheader("2. Carica l'Immagine del Referto")
        st.markdown("Trascina l'immagine qui sotto o clicca per selezionarla.")
        # Visualizza un'immagine placeholder sopra l'uploader
        st.image(placeholder_img_url, caption="Esempio: Carica un'immagine chiara e leggibile del tuo referto.", width=300)

        file_caricato = st.file_uploader(
            "Seleziona un file immagine",
            type=["jpg", "jpeg", "png"],
            key="uploader_img",
            label_visibility="collapsed" # Nasconde l'etichetta, l'istruzione è già sopra
        )
        st.caption("Formati supportati: JPG, JPEG, PNG.")

        if file_caricato is not None:
            try:
                immagine = Image.open(file_caricato)
                st.image(immagine, caption="Immagine Referto Caricata", use_container_width=True)
                st.markdown("---")
                st.subheader("3. Avvia l'Analisi")
                if st.button("✨ Analizza Immagine", key="btn_analizza_img", type="primary"):
                    with st.spinner("🔬 Sto analizzando l'immagine del referto... Potrebbe richiedere un momento..."):
                        analisi = analizza_referto_medico(immagine, "immagine")
                        st.markdown("---")
                        st.subheader("✅ Risultati dell'Analisi IA")
                        st.markdown(analisi)

            except Exception as e:
                st.error(f"Errore durante il caricamento o la visualizzazione dell'immagine: {e}")

    elif tipo_file == "Documento PDF":
        st.subheader("2. Carica il Documento PDF")
        st.markdown("Trascina il file PDF qui sotto o clicca per selezionarlo.")

        file_caricato = st.file_uploader(
            "Seleziona un file PDF",
            type=["pdf"],
            key="uploader_pdf",
            label_visibility="collapsed"
        )
        st.caption("Formato supportato: PDF.")

        if file_caricato is not None:
            percorso_tmp_file = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(file_caricato.getvalue())
                    percorso_tmp_file = tmp_file.name

                st.success(f"📄 File PDF '{file_caricato.name}' caricato con successo.")
                st.markdown("---")
                st.subheader("3. Avvia l'Analisi")

                if st.button("✨ Analizza PDF", key="btn_analizza_pdf", type="primary"):
                    with st.spinner(" BZ Analizzando il testo del referto PDF..."):
                        testo_pdf = estrai_testo_da_pdf(percorso_tmp_file)

                        if testo_pdf: # Controlla se testo_pdf non è None e non è vuoto
                             with st.spinner("🤖 L'IA sta elaborando il testo estratto..."):
                                  analisi = analizza_referto_medico(testo_pdf, "testo")
                                  st.markdown("---")
                                  st.subheader("✅ Risultati dell'Analisi IA")
                                  st.markdown(analisi)
                        else:
                             # Messaggio già mostrato da estrai_testo_da_pdf se l'estrazione fallisce o il testo è vuoto
                             st.error("Impossibile procedere con l'analisi perché non è stato estratto testo valido dal PDF.")

            except Exception as e:
                st.error(f"Si è verificato un errore durante l'elaborazione del PDF: {e}")
            finally:
                if percorso_tmp_file and os.path.exists(percorso_tmp_file):
                    try:
                        os.unlink(percorso_tmp_file)
                    except Exception as e_unlink:
                         st.warning(f"Impossibile eliminare il file temporaneo {percorso_tmp_file}: {e_unlink}")

    else:
        # Questo caso non dovrebbe verificarsi con st.radio, ma è una sicurezza
        st.info("Seleziona un tipo di file (Immagine o PDF) per iniziare.")

    # --- Footer (opzionale) ---
    st.markdown("---")
    st.caption("Applicazione sviluppata con Streamlit e Google Gemini | Ricorda: consulta sempre un medico.")


if __name__ == "__main__":
    main()
