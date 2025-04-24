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
    page_title="Valutazione Preliminare Analisi Del Sangue IA",
    page_icon="🩸",
    layout="wide"
)

# --- Configurazione Gemini (come prima) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    if not api_key:
        st.error("Chiave API Gemini vuota trovata nei segreti di Streamlit. Verifica che sia impostata correttamente.")
        st.stop()
    model = genai.GenerativeModel('gemini-1.5-flash')
    genai.configure(api_key=api_key)

except KeyError:
    st.error("Chiave API Gemini ('GEMINI_API_KEY') non trovata nei segreti di Streamlit.")
    st.error("Vai su 'Manage app' -> 'Settings' -> 'Secrets' e aggiungi: \nGEMINI_API_KEY = \"LA_TUA_CHIAVE_API\"")
    st.stop()
except Exception as e:
    st.error(f"Errore durante la configurazione dell'API Gemini: {e}")
    st.stop()

MAX_RETRIES = 3
RETRY_DELAY = 2

# --- Funzioni Helper ---

def analizza_referto_medico(contenuto, tipo_contenuto):
    """
    Invia il contenuto a Gemini per un'analisi DETTAGLIATA e STRUTTURATA.
    Omette sezioni non pertinenti e non include la nota finale AI.
    Aggiunge il disclaimer finale controllato dall'app.
    """
    prompt = """
    Analizza questo referto medico (probabilmente analisi del sangue) in modo DETTAGLIATO e STRUTTURATO, in ITALIANO. **NON FARE DIAGNOSI MEDICHE**. Fornisci ESCLUSIVAMENTE le sezioni pertinenti tra le seguenti, usando un linguaggio chiaro, cauto e includendo l'emoji indicata all'inizio di ogni titolo di sezione:

    **📊 1. Riassunto dei Risultati Chiave:**
        *   Elenca i principali valori che risultano **significativamente** fuori dagli intervalli di riferimento standard indicati nel referto (se presenti) o che sono comunemente considerati rilevanti.
        *   Riporta i valori numerici e le unità di misura esatte come appaiono nel referto.

    **⚠️ 2. Identificazione Potenziali Aree di Attenzione:**
        *   Basandoti *SOLO ED ESCLUSIVAMENTE* sui risultati fuori norma o significativi elencati sopra, indica quali potrebbero essere le aree fisiologiche o i sistemi corporei che *potrebbero* richiedere attenzione o ulteriori valutazioni da parte di un medico.
        *   Usa espressioni caute come: "I valori di [Nome Esame] potrebbero suggerire un'area da monitorare relativamente a...", "Livelli alterati di [Nome Esame] sono generalmente associati a...".
        *   **NON USARE TERMINI DIAGNOSTICI SPECIFICI (es. 'diabete', 'anemia', 'infezione').** Limita l'analisi ai sistemi coinvolti (es. metabolismo glucidico, funzionalità epatica, sistema immunitario, ecc.).

    **🩺 3. Eventuali Esami Aggiuntivi o Follow-up:**
        *   **INCLUDI QUESTA SEZIONE SOLO SE IL REFERTO FORNITO SUGGERISCE ESPLICITAMENTE ulteriori test, controlli o visite specialistiche.** Riporta *solo* quanto menzionato nel testo originale. Altrimenti, OMETTI completamente questa sezione (incluso il titolo).

    **💡 4. Consigli Generali sullo Stile di Vita:**
        *   **INCLUDI QUESTA SEZIONE SOLO SE i risultati toccano aree molto comuni (es. colesterolo, glicemia, pressione).** Fornisci 1-2 consigli *ESTREMAMENTE GENERICI* e universalmente validi (es., "Mantenere una dieta equilibrata e varia", "Praticare regolare attività fisica moderata").
        *   **Sottolinea che sono consigli generali e NON sostituiscono le indicazioni personalizzate del medico.**
        *   **NON dare consigli specifici su cibi, diete, integratori o farmaci.** Se non applicabile, OMETTI completamente questa sezione (incluso il titolo).

    **🔗 5. Link a Risorse Informative Istituzionali:**
        *   **INCLUDI QUESTA SEZIONE SOLO SE emergono temi di salute *molto generali* e ben definiti (es. colesterolo alto, ipertensione) E SE trovi un link pertinente a una pagina informativa generale del Ministero della Salute Italiano o dell'Istituto Superiore di Sanità (ISS).**
        *   **NON linkare MAI a siti commerciali, blog, forum, articoli specifici o fonti non istituzionali.** Se non applicabile, OMETTI completamente questa sezione (incluso il titolo).

    **(NON AGGIUNGERE NOTE FINALI O DISCLAIMER AGGIUNTIVI TUOI. L'applicazione ne ha già uno).**
    """

    for tentativo in range(MAX_RETRIES):
        try:
            # Non mostriamo più l'info qui, lo gestirà lo spinner principale
            if tipo_contenuto == "immagine":
                risposta = model.generate_content([prompt, contenuto])
            else:  # testo
                input_content = f"{prompt}\n\n--- INIZIO TESTO REFERTO FORNITO ---\n{contenuto}\n--- FINE TESTO REFERTO FORNITO ---"
                risposta = model.generate_content(input_content)

            if hasattr(risposta, 'text') and risposta.text:
                # === RIPRISTINATO DISCLAIMER FINALE APP ===
                disclaimer_finale_app = "\n\n---\n**⚠️⚠️ DISCLAIMER FINALE (DA APP) ⚠️⚠️**\n*Ricorda ancora una volta: questa analisi, per quanto dettagliata, è **AUTOMATICA**, **NON PERSONALIZZATA** e **NON SOSTITUISCE IL MEDICO**. Errori, omissioni o interpretazioni imprecise sono possibili. **Consulta SEMPRE il tuo medico** per una valutazione corretta e completa.*"
                return risposta.text.strip() + disclaimer_finale_app
            elif hasattr(risposta, 'prompt_feedback') and risposta.prompt_feedback.block_reason:
                 st.error(f"L'analisi è stata bloccata dall'IA per motivi di sicurezza/contenuto (Reason: {risposta.prompt_feedback.block_reason}). Ciò può accadere con dati medici sensibili.")
                 return "Errore: L'analisi è stata bloccata dal sistema di sicurezza dell'IA. Prova a caricare un'immagine/PDF più chiaro o meno complesso."
            else:
                st.warning(f"L'IA ha restituito una risposta vuota o inattesa (Tentativo {tentativo + 1}).")
                if tentativo == MAX_RETRIES - 1:
                     return analisi_fallback(contenuto, tipo_contenuto)
                time.sleep(RETRY_DELAY)

        except exceptions.GoogleAPIError as e:
            # ... (gestione errori API come prima) ...
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
             return f"Errore imprevisto durante l'analisi ({type(e).__name__}). Si prega di riprovare o verificare il file caricato."

    st.error("Impossibile completare l'analisi dopo tutti i tentativi.")
    return analisi_fallback(contenuto, tipo_contenuto)


def analisi_fallback(contenuto, tipo_contenuto):
    # ... (come prima) ...
    st.warning("⚠️ Attenzione: Si è verificato un problema con l'analisi IA dettagliata. Viene mostrata un'analisi di base.")
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
    # ... (come prima) ...
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
            for i, pagina in enumerate(lettore_pdf.pages):
                try:
                    testo_pagina = pagina.extract_text()
                    if testo_pagina:
                        testo_completo += testo_pagina + "\n"
                except Exception as page_err:
                     st.warning(f"Impossibile estrarre completamente il testo dalla pagina {i+1}: {page_err}")

            if not testo_completo.strip():
                 st.warning("Non è stato possibile estrarre testo utilizzabile dal PDF...")
                 return None
            return testo_completo
    except FileNotFoundError:
         st.error(f"Errore: File temporaneo PDF non trovato: {pdf_file_path}")
         return None
    except PyPDF2.errors.PdfReadError as pdf_err:
         st.error(f"Errore lettura PDF: File danneggiato o non valido. ({pdf_err})")
         return None
    except Exception as e:
        st.error(f"Errore critico elaborazione PDF: {e}")
        return None

# --- Funzione Main ---
def main():

    # Inizializza session state se non esiste (come prima)
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'processed_file_id' not in st.session_state:
        st.session_state.processed_file_id = None
    if 'current_file_type' not in st.session_state:
         st.session_state.current_file_type = "Immagine (JPG, PNG)"

    # --- IMMAGINE DI INTESTAZIONE ---
    header_image_url = "https://cdn.leonardo.ai/users/efef8ea0-d41a-4914-8f6f-1d8591a11f28/generations/dbcb618a-0840-46bb-8129-bdeeed315bf5/Leonardo_Phoenix_10_a_highly_detailed_surreal_and_vibrant_cine_0.jpg"
    try:
        st.image(header_image_url, use_container_width=True)
    except Exception as img_err:
        st.warning(f"Avviso: Impossibile caricare l'immagine di intestazione dal link fornito. ({img_err})", icon="🖼️")

    # --- Titolo App ---
    st.title("⚕️ Valutazione Preliminare Analisi Del Sangue IA 🩸")
    st.markdown("Carica il tuo referto delle analisi del sangue (immagine o PDF) per ottenere una **valutazione preliminare, dettagliata e strutturata** basata su Intelligenza Artificiale.")
    st.markdown("---")

    # === RIPRISTINATO DISCLAIMER INIZIALE ===
    st.error("""
    **🛑 ATTENZIONE MASSIMA: Leggere Prima di Procedere! 🛑**

    *   Questa applicazione fornisce un'**ANALISI AUTOMATICA E DETTAGLIATA** ma **ASSOLUTAMENTE NON MEDICA**.
    *   **NON È UNO STRUMENTO DIAGNOSTICO.** L'IA può commettere errori, interpretare male o fornire informazioni fuorvianti.
    *   L'obiettivo è solo quello di **strutturare le informazioni** presenti nel referto in modo più leggibile.
    *   **NON BASARE NESSUNA DECISIONE DI SALUTE SU QUESTI RISULTATI.**
    *   **È OBBLIGATORIO CONSULTARE IL PROPRIO MEDICO CURANTE** per l'interpretazione corretta del referto, la diagnosi e qualsiasi indicazione terapeutica.
    """)
    st.markdown("---")

    # --- Sezione 1: Selezione Tipo File con Immagine Affiancata ---
    col_select, col_img1 = st.columns([3, 1], gap="medium")

    def clear_analysis_on_type_change():
         st.session_state.analysis_result = None
         st.session_state.processed_file_id = None

    with col_select:
        st.subheader("1. Scegli il formato del referto")
        tipo_file = st.radio(
            "Seleziona il tipo di file:",
            ("Immagine (JPG, PNG)", "Documento PDF"),
            horizontal=True,
            key="tipo_file_radio_key",
            label_visibility="collapsed",
            on_change=clear_analysis_on_type_change
        )
        st.session_state.current_file_type = tipo_file

    with col_img1:
        section1_image_url = "https://www.cdi.it/wp-content/uploads/2021/08/shutterstock_1825232600-800x450-1.jpg"
        try:
            st.image(section1_image_url, width=200)
        except Exception as img_err:
             st.warning(f"Avviso: Impossibile caricare l'immagine Sezione 1. ({img_err})", icon="🖼️")

    st.markdown("---")

    # --- Sezione 2: Caricamento File con Immagine Decorativa ---
    st.subheader("2. Carica il Referto")
    col_upload, col_filler_img = st.columns([3, 1], gap="medium")

    with col_filler_img:
        filler_image_url = "https://cdn.leonardo.ai/users/efef8ea0-d41a-4914-8f6f-1d8591a11f28/generations/1cf09cf6-3b12-4575-82e5-7350966327b5/Leonardo_Phoenix_10_a_mesmerizing_and_vibrant_cinematic_photo_1.jpg"
        try:
            st.image(filler_image_url, width=200)
        except Exception as img_err:
            st.warning(f"Avviso: Impossibile caricare l'immagine decorativa. ({img_err})", icon="🎨")

    file_caricato = None
    with col_upload:
        # === REINSERITE E MIGLIORATE ISTRUZIONI UPLOAD ===
        if tipo_file == "Immagine (JPG, PNG)":
            st.info("""
            **Carica l'immagine del tuo referto:**
            *   Clicca sul pulsante "Browse files" (o simile) qui sotto.
            *   Oppure, trascina il file (JPG, PNG) dal tuo computer nell'area grigia.

            *Suggerimento: Assicurati che l'immagine sia chiara e leggibile.*
            """, icon="🖼️") # Cambiata icona per immagine
            file_caricato = st.file_uploader(
                "Carica Immagine",
                 type=["jpg", "jpeg", "png"], key="uploader_img",
                 label_visibility="collapsed", help="Trascina o clicca per selezionare un file JPG, JPEG o PNG (max 200MB)"
            )
            st.caption("Formati accettati: JPG, JPEG, PNG.")

        elif tipo_file == "Documento PDF":
            st.info("""
            **Carica il tuo referto in formato PDF:**
            *   Clicca sul pulsante "Browse files" (o simile) qui sotto.
            *   Oppure, trascina il file PDF dal tuo computer nell'area grigia.

            *Nota: Verrà estratto solo il testo dal PDF.*
            """, icon="📄")
            file_caricato = st.file_uploader(
                "Carica PDF",
                 type=["pdf"], key="uploader_pdf",
                 label_visibility="collapsed", help="Trascina o clicca per selezionare un file PDF (max 200MB)"
            )
            st.caption("Formato accettato: PDF.")
        # === FINE REINSERIMENTO ISTRUZIONI ===


    # --- Logica di Analisi Automatica (come prima) ---
    analysis_placeholder = st.empty()

    if file_caricato is not None:
        current_file_id = f"{file_caricato.name}_{file_caricato.size}"

        if current_file_id != st.session_state.processed_file_id:
            st.session_state.analysis_result = None
            st.session_state.processed_file_id = current_file_id

            with analysis_placeholder.container():
                st.success(f"File '{file_caricato.name}' caricato. Avvio analisi automatica...")
                st.warning("Ricorda i limiti dell'IA e consulta il medico!") # Warning prima dell'analisi

                analisi_output = None
                if tipo_file == "Immagine (JPG, PNG)":
                    try:
                        immagine = Image.open(file_caricato)
                        st.image(immagine, caption="Anteprima Referto Caricato", use_container_width=True)
                        st.markdown("---")
                        with st.spinner("🔬 Analisi dettagliata IA in corso... Potrebbe richiedere più tempo..."):
                            analisi_output = analizza_referto_medico(immagine, "immagine") # Chiama funzione aggiornata
                    except Exception as e:
                        st.error(f"Errore nell'apertura o analisi dell'immagine: {e}")
                        analisi_output = f"Errore: Impossibile processare l'immagine '{file_caricato.name}'."

                elif tipo_file == "Documento PDF":
                    percorso_tmp_file = None
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(file_caricato.getvalue())
                            percorso_tmp_file = tmp_file.name

                        testo_pdf = None
                        with st.spinner("📄 Estrazione testo dal PDF..."):
                            testo_pdf = estrai_testo_da_pdf(percorso_tmp_file)

                        if testo_pdf:
                            with st.spinner("🤖 Elaborazione IA Dettagliata in corso... Attendere prego..."):
                                analisi_output = analizza_referto_medico(testo_pdf, "testo") # Chiama funzione aggiornata
                        else:
                            st.error("Analisi non possibile: nessun testo valido estratto dal PDF.")
                            analisi_output = "Errore: Nessun testo valido estratto dal PDF."

                    except Exception as e:
                        st.error(f"Errore generale durante elaborazione PDF: {e}")
                        analisi_output = f"Errore: Impossibile processare il PDF '{file_caricato.name}'."
                    finally:
                        if percorso_tmp_file and os.path.exists(percorso_tmp_file):
                            try: os.unlink(percorso_tmp_file)
                            except Exception as e_unlink: st.warning(f"Avviso: Impossibile eliminare file temporaneo: {e_unlink}")

                st.session_state.analysis_result = analisi_output

                if st.session_state.analysis_result:
                     st.markdown("---")
                     st.subheader("✅ Risultati Valutazione IA Dettagliata")
                     st.markdown(st.session_state.analysis_result) # Mostra risultato (che include disclaimer app)

        elif st.session_state.analysis_result:
             with analysis_placeholder.container():
                 if tipo_file == "Immagine (JPG, PNG)":
                     try:
                         immagine = Image.open(file_caricato)
                         st.image(immagine, caption="Anteprima Referto (già analizzato)", use_container_width=True)
                         st.markdown("---")
                     except: pass
                 st.subheader("✅ Risultati Valutazione IA Dettagliata (Precedente)")
                 st.markdown(st.session_state.analysis_result) # Mostra risultato salvato (che include disclaimer app)

    else:
         if st.session_state.processed_file_id is not None:
              st.session_state.analysis_result = None
              st.session_state.processed_file_id = None
              analysis_placeholder.empty()


    # --- Separatore e Caption Finale ---
    st.markdown("---")
    st.caption("Applicazione sviluppata con Streamlit e Google Gemini. **Consulta sempre un professionista sanitario.**")


if __name__ == "__main__":
    main()
