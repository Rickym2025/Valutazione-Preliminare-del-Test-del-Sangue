# -*- coding: utf-8 -*-
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
    page_icon="⚕️",  # Icona medica
    layout="wide"
)

# --- Configurazione del modello Gemini AI usando st.secrets ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    if not api_key:
        st.error("Chiave API Gemini vuota trovata nei segreti di Streamlit. Verifica che sia impostata correttamente.")
        st.stop()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

except KeyError:
    st.error("Chiave API Gemini ('GEMINI_API_KEY') non trovata nei segreti di Streamlit.")
    st.error("Vai su 'Manage app' (in basso a destra), poi 'Settings' -> 'Secrets' e aggiungi la tua chiave API nel formato: \nGEMINI_API_KEY = \"LA_TUA_CHIAVE_API\"")
    st.stop()
except Exception as e:
    st.error(f"Errore durante la configurazione dell'API Gemini: {e}")
    st.stop()
# --- Fine Configurazione ---

MAX_RETRIES = 3
RETRY_DELAY = 2 # secondi

def analizza_referto_medico(contenuto, tipo_contenuto):
    """
    Invia il contenuto (immagine o testo) a Gemini per l'analisi.
    Gestisce tentativi e fallback. Totalmente in Italiano.
    """
    prompt = "Analizza questo referto medico in modo conciso e strutturato, in ITALIANO. Fornisci: 1. Principali Risultati (valori chiave, osservazioni). 2. Possibile Diagnosi o Interpretazione (se menzionata/deducibile). 3. Raccomandazioni (come indicate nel referto). Sii chiaro e usa elenchi puntati se appropriato."
    for tentativo in range(MAX_RETRIES):
        try:
            if tipo_contenuto == "immagine":
                # Gemini può gestire direttamente oggetti PIL.Image
                risposta = model.generate_content([prompt, contenuto])
            else:  # testo
                risposta = model.generate_content(f"{prompt}\n\n--- INIZIO REFERTO ---\n{contenuto}\n--- FINE REFERTO ---")

            disclaimer = "\n\n---\n**⚠️ Disclaimer Importante:** *Questa è un'analisi preliminare generata da Intelligenza Artificiale. Non sostituisce in alcun modo il parere di un medico qualificato. Consulta sempre il tuo medico o uno specialista per una diagnosi accurata, interpretazione completa e decisioni terapeutiche.*"
            suggerimenti = "\n\n*Suggerimenti generali:*\n- Confronta questa analisi con il referto originale.\n- Discuti i risultati e le raccomandazioni con il tuo medico.\n- Segui attentamente le indicazioni terapeutiche fornite dai professionisti sanitari."
            # Assicurati che la risposta del modello non contenga errori o messaggi strani
            if hasattr(risposta, 'text'):
                return risposta.text + disclaimer + suggerimenti
            else:
                # Se la risposta non ha 'text', potrebbe esserci stato un problema
                st.warning(f"Risposta inattesa dal modello (Tentativo {tentativo + 1}): {risposta}")
                # Forziamo l'uso del fallback se la risposta non è valida
                if tentativo == MAX_RETRIES - 1:
                     return analisi_fallback(contenuto, tipo_contenuto)
                time.sleep(RETRY_DELAY) # Aspetta prima del prossimo tentativo

        except exceptions.GoogleAPIError as e:
            st.warning(f"Errore API Google durante l'analisi (Tentativo {tentativo + 1}/{MAX_RETRIES}): {str(e)}")
            if "quota" in str(e).lower():
                 st.error("Limite di richieste API superato (Quota). Controlla il tuo account Google Cloud o riprova più tardi.")
                 return "Errore: Quota API superata."
            if tentativo < MAX_RETRIES - 1:
                st.info(f"Riprovo tra {RETRY_DELAY} secondi...")
                time.sleep(RETRY_DELAY)
            else:
                st.error(f"Impossibile analizzare il referto dopo {MAX_RETRIES} tentativi a causa di errori API persistenti.")
                return analisi_fallback(contenuto, tipo_contenuto)
        except Exception as e:
             st.error(f"Si è verificato un errore imprevisto durante l'analisi: {str(e)}")
             # Non restituire il fallback qui, potrebbe essere un errore diverso
             return f"Errore imprevisto durante l'analisi ({type(e).__name__}). Si prega di riprovare o verificare il file caricato."

    # Se esce dal loop senza successo (improbabile con la logica sopra, ma per sicurezza)
    st.error("Impossibile completare l'analisi dopo tutti i tentativi.")
    return analisi_fallback(contenuto, tipo_contenuto)

def analisi_fallback(contenuto, tipo_contenuto):
    """
    Fornisce un'analisi di base in italiano se l'API Gemini fallisce.
    """
    st.warning("⚠️ Attenzione: Si è verificato un problema con l'analisi IA. Viene mostrata un'analisi di base.")
    if tipo_contenuto == "immagine":
        analisi = "Analisi di Fallback: Impossibile analizzare l'immagine a causa di problemi tecnici. Si prega di consultare un professionista medico per un'interpretazione accurata."
    else: # testo
        try:
             numero_parole = len(contenuto.split())
             analisi = f"""
Analisi di Fallback:
*   **Tipo:** Referto medico testuale.
*   **Lunghezza:** Circa {numero_parole} parole.
*   **Contenuto:** Il documento sembra contenere informazioni mediche, ma l'analisi dettagliata tramite IA non è al momento disponibile.
*   **Raccomandazione:** È fondamentale **consultare un professionista sanitario** per un'interpretazione accurata e una diagnosi.
*   **Nota:** Analisi semplificata a causa di indisponibilità temporanea del servizio principale.
"""
        except Exception:
             analisi = "Analisi di Fallback: Impossibile elaborare il contenuto testuale fornito. Verifica che il PDF non sia corrotto o vuoto."

    disclaimer = "\n\n---\n**⚠️ Disclaimer Importante:** *Questa è un'analisi di fallback. Consulta SEMPRE il tuo medico per interpretazioni e decisioni mediche.*"
    suggerimenti = "\n\n*Suggerimenti di fallback:*\n- Contatta il tuo medico curante.\n- Chiedi una seconda opinione medica se necessario."
    return analisi + disclaimer + suggerimenti


def estrai_testo_da_pdf(pdf_file_path):
    """
    Estrae testo da un PDF. Gestisce errori comuni. Totalmente in Italiano.
    """
    testo_completo = ""
    try:
        with open(pdf_file_path, 'rb') as file:
            lettore_pdf = PyPDF2.PdfReader(file)

            if lettore_pdf.is_encrypted:
                st.warning("Il PDF è protetto da password. Tentativo di sblocco senza password...")
                try:
                    if lettore_pdf.decrypt('') == PyPDF2.PasswordType.NOT_DECRYPTED:
                         st.error("Impossibile sbloccare il PDF senza password. L'analisi non può procedere.")
                         return None
                    st.info("PDF sbloccato con successo (senza password).")
                except Exception as decrypt_err:
                    st.error(f"Errore durante il tentativo di sblocco del PDF: {decrypt_err}")
                    return None

            num_pagine = len(lettore_pdf.pages)
            st.info(f"Lettura di {num_pagine} pagine dal PDF...")

            for i, pagina in enumerate(lettore_pdf.pages):
                try:
                    testo_pagina = pagina.extract_text()
                    if testo_pagina:
                        testo_completo += testo_pagina + "\n"
                    # else:
                        # Potrebbe essere utile per debug, ma evitiamo troppi messaggi
                        # st.caption(f"Pagina {i+1}: Nessun testo estraibile (potrebbe essere un'immagine).")
                except Exception as page_err:
                     st.warning(f"Impossibile estrarre completamente il testo dalla pagina {i+1}: {page_err}")

            if not testo_completo.strip():
                 st.warning("Non è stato possibile estrarre testo utilizzabile dal PDF. Verifica che non contenga solo immagini (scansione senza OCR) o che non sia vuoto/danneggiato.")
                 return None # Nessun testo valido estratto
            st.success("Estrazione del testo dal PDF completata.")
            return testo_completo

    except FileNotFoundError:
         st.error(f"Errore: File temporaneo PDF non trovato nel percorso: {pdf_file_path}")
         return None
    except PyPDF2.errors.PdfReadError as pdf_err:
         st.error(f"Errore nella lettura del PDF: Il file potrebbe essere danneggiato o non essere un PDF valido. ({pdf_err})")
         return None
    except Exception as e:
        st.error(f"Errore critico durante l'elaborazione del PDF: {e}")
        return None


def main():
    # --- Header ---
    st.title("⚕️ Analizzatore Referti Medici IA")
    st.markdown("Carica il tuo referto medico (immagine o PDF) per ottenere un'analisi preliminare e concisa basata su Intelligenza Artificiale.")
    st.markdown("---")

    # --- Disclaimer Principale ---
    st.warning("""
    **⚠️ ATTENZIONE: Strumento Puramente Informativo!**
    Questa applicazione offre un riassunto automatico e **NON sostituisce MAI** il parere, la diagnosi o il trattamento forniti da un medico qualificato.
    I risultati sono da intendersi **ESCLUSIVAMENTE come supporto informativo**.
    **CONSULTA SEMPRE IL TUO MEDICO** per qualsiasi questione o decisione riguardante la tua salute.
    """)
    st.markdown("---")

    # --- Selezione Tipo File ---
    st.subheader("1. Scegli il formato del referto")
    tipo_file = st.radio(
        "Seleziona il tipo di file:",
        ("Immagine (JPG, PNG)", "Documento PDF"),
        horizontal=True,
        key="tipo_file_radio",
        label_visibility="collapsed"
    )
    st.markdown("---")

    file_caricato = None
    # --- USA IMMAGINE LOCALE ---
    placeholder_img_path = "assets/report_placeholder.png" # Percorso relativo all'immagine nella cartella assets

    # --- Logica di Upload e Analisi ---
    if tipo_file == "Immagine (JPG, PNG)":
        st.subheader("2. Carica l'Immagine del Referto")

        # Istruzioni chiare in Italiano prima dell'uploader
        st.markdown("👇 **Trascina qui sotto il file immagine o clicca per cercarlo sul tuo dispositivo.**")
        st.markdown("*(Assicurati che l'immagine sia ben leggibile)*")

        # Visualizza l'immagine placeholder locale
        try:
            # Controlla se il file esiste prima di tentare di visualizzarlo
            if os.path.exists(placeholder_img_path):
                 # Rimosso caption dall'immagine placeholder per evitare confusione
                 st.image(placeholder_img_path, width=250) # Leggermente più piccola
            else:
                 st.caption("Nota: Immagine dimostrativa non trovata. Assicurati che 'assets/report_placeholder.png' esista nel repository.")
        except Exception as img_err:
            # Non mostrare un errore bloccante per l'immagine demo, solo un avviso
            st.warning(f"Avviso: Impossibile caricare l'immagine dimostrativa ({placeholder_img_path}). {img_err}", icon="🖼️")

        # File Uploader
        file_caricato = st.file_uploader(
            "Carica immagine referto", # Etichetta accessibile, ma nascosta visivamente
            type=["jpg", "jpeg", "png"],
            key="uploader_img",
            label_visibility="collapsed", # Nasconde l'etichetta "Carica immagine referto"
            help="Clicca o trascina qui un file JPG, JPEG o PNG (max 200MB)" # Testo tooltip in italiano
        )
        # Riafferma i dettagli in italiano sotto l'uploader
        st.caption("Formati accettati: JPG, JPEG, PNG. Dimensione massima: 200MB.")

        if file_caricato is not None:
            st.success(f"Immagine '{file_caricato.name}' caricata correttamente!")
            col1, col2 = st.columns([2, 3]) # Colonne per affiancare immagine e bottone
            with col1:
                try:
                    immagine = Image.open(file_caricato)
                    st.image(immagine, caption="Anteprima Referto Caricato", use_container_width=True)
                except Exception as e:
                    st.error(f"Errore durante l'apertura dell'immagine: {e}")
                    immagine = None # Impedisce di procedere se l'immagine non è valida
            with col2:
                st.markdown("---")
                st.subheader("3. Avvia l'Analisi")
                if immagine and st.button("✨ Analizza Immagine", key="btn_analizza_img", type="primary", use_container_width=True):
                    with st.spinner("🔬 Sto analizzando l'immagine... Potrebbe richiedere qualche istante..."):
                        analisi = analizza_referto_medico(immagine, "immagine")
                        st.markdown("---")
                        st.subheader("✅ Risultati dell'Analisi IA")
                        st.markdown(analisi) # Usa markdown per formattazione

    elif tipo_file == "Documento PDF":
        st.subheader("2. Carica il Documento PDF")
        st.markdown("👇 **Trascina qui sotto il file PDF o clicca per cercarlo sul tuo dispositivo.**")

        file_caricato = st.file_uploader(
            "Carica documento PDF",
            type=["pdf"],
            key="uploader_pdf",
            label_visibility="collapsed",
            help="Clicca o trascina qui un file PDF (max 200MB)" # Tooltip in italiano
        )
        st.caption("Formato accettato: PDF. Dimensione massima: 200MB.")

        if file_caricato is not None:
            percorso_tmp_file = None
            try:
                # Salva in un file temporaneo per PyPDF2
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(file_caricato.getvalue())
                    percorso_tmp_file = tmp_file.name # Salva il percorso

                st.success(f"📄 File PDF '{file_caricato.name}' caricato con successo.")
                st.markdown("---")
                st.subheader("3. Avvia l'Analisi")

                if st.button("✨ Analizza PDF", key="btn_analizza_pdf", type="primary", use_container_width=True):
                    testo_pdf = None # Inizializza
                    with st.spinner("📄 Sto estraendo il testo dal PDF..."):
                        testo_pdf = estrai_testo_da_pdf(percorso_tmp_file)

                    if testo_pdf: # Procede solo se l'estrazione ha prodotto testo
                         with st.spinner("🤖 L'IA sta elaborando il testo estratto... Attendere prego..."):
                              analisi = analizza_referto_medico(testo_pdf, "testo")
                              st.markdown("---")
                              st.subheader("✅ Risultati dell'Analisi IA")
                              st.markdown(analisi) # Usa markdown
                    else:
                         # Messaggio di errore o warning già mostrato da estrai_testo_da_pdf
                         st.error("Analisi non possibile: nessun testo valido estratto dal PDF.")

            except Exception as e:
                st.error(f"Si è verificato un errore generale durante l'elaborazione del PDF: {e}")
            finally:
                # Pulizia del file temporaneo
                if percorso_tmp_file and os.path.exists(percorso_tmp_file):
                    try:
                        os.unlink(percorso_tmp_file)
                    except Exception as e_unlink:
                         st.warning(f"Avviso: Impossibile eliminare automaticamente il file temporaneo {percorso_tmp_file}. {e_unlink}")

    # --- Footer ---
    st.markdown("---")
    st.caption("Applicazione sviluppata con Streamlit e Google Gemini. Ricorda sempre di consultare un professionista sanitario.")


if __name__ == "__main__":
    main()
