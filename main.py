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

# --- Funzioni Helper (analizza_referto_medico, analisi_fallback, estrai_testo_da_pdf - NESSUNA MODIFICA QUI) ---
# ... (Copia le funzioni analizza_referto_medico, analisi_fallback, estrai_testo_da_pdf dalla versione precedente qui) ...
def analizza_referto_medico(contenuto, tipo_contenuto):
    """
    Invia il contenuto a Gemini per un'analisi DETTAGLIATA e STRUTTURATA.
    Include sezioni specifiche come richiesto, con forti disclaimer.
    """
    prompt = """
    Analizza questo referto medico (probabilmente analisi del sangue) in modo DETTAGLIATO e STRUTTURATO, in ITALIANO. **NON FARE DIAGNOSI MEDICHE**. Fornisci ESCLUSIVAMENTE le seguenti sezioni, usando un linguaggio chiaro e cauto:

    1.  **Riassunto dei Risultati Chiave:**
        *   Elenca i principali valori che risultano **significativamente** fuori dagli intervalli di riferimento standard indicati nel referto (se presenti) o che sono comunemente considerati rilevanti.
        *   Riporta i valori numerici e le unità di misura esatte come appaiono nel referto.

    2.  **Identificazione Potenziali Aree di Attenzione:**
        *   Basandoti *SOLO ED ESCLUSIVAMENTE* sui risultati fuori norma o significativi elencati sopra, indica quali potrebbero essere le aree fisiologiche o i sistemi corporei che *potrebbero* richiedere attenzione o ulteriori valutazioni da parte di un medico.
        *   Usa espressioni caute come: "I valori di [Nome Esame] potrebbero suggerire un'area da monitorare relativamente a...", "Livelli alterati di [Nome Esame] sono generalmente associati a...".
        *   **NON USARE TERMINI DIAGNOSTICI SPECIFICI (es. 'diabete', 'anemia', 'infezione').** Limita l'analisi ai sistemi coinvolti (es. metabolismo glucidico, funzionalità epatica, sistema immunitario, ecc.).

    3.  **Eventuali Esami Aggiuntivi o Follow-up (SOLO SE MENZIONATI NEL REFERTO):**
        *   Riporta *SOLAMENTE* se il testo del referto fornito suggerisce *esplicitamente* ulteriori test, controlli o visite specialistiche.
        *   **NON INVENTARE O SUGGERIRE TEST** non menzionati nel documento originale. Se non ci sono indicazioni, scrivi: "Il referto non menziona esami aggiuntivi o follow-up specifici."

    4.  **Consigli Generali sullo Stile di Vita (MOLTO GENERICI e se PERTINENTI):**
        *   *SOLO SE* i risultati toccano aree molto comuni (es. colesterolo, glicemia, pressione), fornisci 1-2 consigli *ESTREMAMENTE GENERICI* e universalmente validi (es., "Mantenere una dieta equilibrata e varia", "Praticare regolare attività fisica moderata", "Limitare il consumo di grassi saturi/zuccheri semplici").
        *   **Sottolinea che sono consigli generali e NON sostituiscono le indicazioni personalizzate del medico.** Se nessun'area comune è coinvolta, scrivi: "Non applicabile o non deducibile dal referto."
        *   **NON dare consigli specifici su cibi, diete particolari, integratori o farmaci.**

    5.  **Link a Risorse Informative Istituzionali (Opzionale e con Cautela):**
        *   *SOLO SE* emergono temi di salute *molto generali* e ben definiti (es. colesterolo alto, ipertensione), puoi includere UN link a una pagina informativa generale del **Ministero della Salute Italiano** o dell'**Istituto Superiore di Sanità (ISS)**, se trovi una corrispondenza pertinente.
        *   Esempio: Se si parla di colesterolo, potresti linkare la pagina generale sul colesterolo del Ministero.
        *   **NON linkare MAI a siti commerciali, blog, forum, articoli specifici o fonti non istituzionali.** Se non trovi un link istituzionale pertinente e generale, scrivi: "Nessun link a risorse istituzionali generali applicabile."

    **Nota Bene Finale (Includi questo testo alla fine della risposta):**
    "Questa analisi è generata automaticamente da un'IA ed è puramente informativa. Non ha valore diagnostico e non sostituisce il consulto medico. Discuti SEMPRE questi risultati e qualsiasi dubbio con il tuo medico curante."
    """

    for tentativo in range(MAX_RETRIES):
        try:
            st.info(f"Invio richiesta all'IA (Tentativo {tentativo + 1}/{MAX_RETRIES})... L'analisi dettagliata potrebbe richiedere più tempo.")
            if tipo_contenuto == "immagine":
                risposta = model.generate_content([prompt, contenuto])
            else:  # testo
                input_content = f"{prompt}\n\n--- INIZIO TESTO REFERTO FORNITO ---\n{contenuto}\n--- FINE TESTO REFERTO FORNITO ---"
                risposta = model.generate_content(input_content)

            if hasattr(risposta, 'text') and risposta.text:
                disclaimer_finale_app = "\n\n---\n**⚠️⚠️ DISCLAIMER FINALE (DA APP) ⚠️⚠️**\n*Ricorda ancora una volta: questa analisi, per quanto dettagliata, è **AUTOMATICA**, **NON PERSONALIZZATA** e **NON SOSTITUISCE IL MEDICO**. Errori, omissioni o interpretazioni imprecise sono possibili. **Consulta SEMPRE il tuo medico** per una valutazione corretta e completa.*"
                return risposta.text + disclaimer_finale_app
            elif hasattr(risposta, 'prompt_feedback') and risposta.prompt_feedback.block_reason:
                 st.error(f"L'analisi è stata bloccata dall'IA per motivi di sicurezza/contenuto (Reason: {risposta.prompt_feedback.block_reason}). Ciò può accadere con dati medici sensibili.")
                 return "Errore: L'analisi è stata bloccata dal sistema di sicurezza dell'IA. Prova a caricare un'immagine/PDF più chiaro o meno complesso."
            else:
                st.warning(f"L'IA ha restituito una risposta vuota o inattesa (Tentativo {tentativo + 1}).")
                if tentativo == MAX_RETRIES - 1:
                     return analisi_fallback(contenuto, tipo_contenuto)
                time.sleep(RETRY_DELAY)

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
             return f"Errore imprevisto durante l'analisi ({type(e).__name__}). Si prega di riprovare o verificare il file caricato."

    st.error("Impossibile completare l'analisi dopo tutti i tentativi.")
    return analisi_fallback(contenuto, tipo_contenuto)


def analisi_fallback(contenuto, tipo_contenuto):
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

    # --- IMMAGINE DI INTESTAZIONE ---
    # NUOVO URL INTESTAZIONE
    header_image_url = "https://cdn.leonardo.ai/users/efef8ea0-d41a-4914-8f6f-1d8591a11f28/generations/5c2a4da3-bea8-4549-ab77-6dd0846b73d1/Leonardo_Phoenix_10_a_highly_detailed_and_hyperrealistic_cinem_0.jpg"                        # HEADER IMAGE
    try:
        st.image(header_image_url, use_container_width=True)
    except Exception as img_err:
        st.warning(f"Avviso: Impossibile caricare l'immagine di intestazione. {img_err}", icon="🖼️")

    # --- Titolo App ---
    st.title("⚕️ Valutazione Preliminare Analisi Del Sangue IA 🩸")
    st.markdown("Carica il tuo referto delle analisi del sangue (immagine o PDF) per ottenere una **valutazione preliminare, dettagliata e strutturata** basata su Intelligenza Artificiale.")
    st.markdown("---")

    # --- Disclaimer Principale (invariato) ---
    st.error("""
    **🛑 ATTENZIONE MASSIMA: Leggere Prima di Procedere! 🛑**
    *   Questa applicazione fornisce un'**ANALISI AUTOMATICA E DETTAGLIATA** ma **ASSOLUTAMENTE NON MEDICA**.
    *   **NON È UNO STRUMENTO DIAGNOSTICO.** L'IA può commettere errori, interpretare male o fornire informazioni fuorvianti.
    *   L'obiettivo è solo quello di **strutturare le informazioni** presenti nel referto in modo più leggibile.
    *   **NON BASARE NESSUNA DECISIONE DI SALUTE SU QUESTI RISULTATI.**
    *   **È OBBLIGATORIO CONSULTARE IL PROPRIO MEDICO CURANTE** per l'interpretazione corretta del referto, la diagnosi e qualsiasi indicazione terapeutica.
    """)
    st.markdown("---")

    # --- Selezione Tipo File (invariato) ---
    st.subheader("1. Scegli il formato del referto")
    tipo_file = st.radio(
        "Seleziona il tipo di file:",
        ("Immagine (JPG, PNG)", "Documento PDF"),
        horizontal=True, key="tipo_file_radio", label_visibility="collapsed"
    )
    st.markdown("---")

    file_caricato = None

    # --- Logica di Upload e Analisi ---
    if tipo_file == "Immagine (JPG, PNG)":
        st.subheader("2. Carica l'Immagine del Referto")
        st.info("""
        **Come caricare l'immagine:**
        *   Clicca sul pulsante "Browse files" (o simile) nel riquadro grigio qui sotto.
        *   Oppure, trascina il file immagine dal tuo computer al riquadro grigio.
        *Consiglio: Usa un'immagine chiara e ben leggibile!*
        """, icon="💡")

        # File Uploader
        file_caricato = st.file_uploader(
            "Area di caricamento immagine", type=["jpg", "jpeg", "png"], key="uploader_img",
            label_visibility="collapsed", help="Clicca o trascina qui JPG, JPEG o PNG (max 200MB)"
        )
        st.caption("Formati accettati: JPG, JPEG, PNG.")

        if file_caricato is not None:
            st.success(f"Immagine '{file_caricato.name}' caricata!")
            col1, col2 = st.columns([2, 3])
            with col1:
                 try:
                    immagine = Image.open(file_caricato)
                    st.image(immagine, caption="Anteprima Referto Caricato", use_container_width=True)
                 except Exception as e:
                    st.error(f"Errore apertura immagine: {e}")
                    immagine = None
            with col2:
                st.markdown("---")
                st.subheader("3. Avvia Valutazione Dettagliata")
                if immagine and st.button("✨ Valuta Immagine (Dettagliato)", key="btn_analizza_img", type="primary", use_container_width=True):
                    st.warning("Avvio analisi dettagliata. Ricorda i limiti dell'IA e consulta il medico!")
                    with st.spinner("🔬 Analisi dettagliata IA in corso... Potrebbe richiedere più tempo..."):
                        analisi = analizza_referto_medico(immagine, "immagine")
                        st.markdown("---")
                        st.subheader("✅ Risultati Valutazione IA Dettagliata")
                        st.markdown(analisi)

    elif tipo_file == "Documento PDF":
        st.subheader("2. Carica il Documento PDF")
        st.info("""
        **Come caricare il PDF:**
        *   Clicca sul pulsante "Browse files" (o simile) nel riquadro grigio qui sotto.
        *   Oppure, trascina il file PDF dal tuo computer al riquadro grigio.
        """, icon="📄")

        file_caricato = st.file_uploader(
            "Area di caricamento PDF", type=["pdf"], key="uploader_pdf",
            label_visibility="collapsed", help="Clicca o trascina qui un file PDF (max 200MB)"
        )
        st.caption("Formato accettato: PDF.")

        if file_caricato is not None:
            percorso_tmp_file = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(file_caricato.getvalue())
                    percorso_tmp_file = tmp_file.name

                st.success(f"📄 PDF '{file_caricato.name}' caricato.")
                st.markdown("---")
                st.subheader("3. Avvia Valutazione Dettagliata")

                if st.button("✨ Valuta PDF (Dettagliato)", key="btn_analizza_pdf", type="primary", use_container_width=True):
                    st.warning("Avvio analisi dettagliata. Ricorda i limiti dell'IA e consulta il medico!")
                    testo_pdf = None
                    with st.spinner("📄 Estrazione testo dal PDF..."):
                        testo_pdf = estrai_testo_da_pdf(percorso_tmp_file)

                    if testo_pdf:
                         with st.spinner("🤖 Elaborazione IA Dettagliata in corso... Attendere prego..."):
                              analisi = analizza_referto_medico(testo_pdf, "testo")
                              st.markdown("---")
                              st.subheader("✅ Risultati Valutazione IA Dettagliata")
                              st.markdown(analisi)
                    else:
                         st.error("Valutazione non possibile: nessun testo valido estratto dal PDF.")

            except Exception as e:
                st.error(f"Errore generale durante elaborazione PDF: {e}")
            finally:
                if percorso_tmp_file and os.path.exists(percorso_tmp_file):
                    try:
                        os.unlink(percorso_tmp_file)
                    except Exception as e_unlink:
                         st.warning(f"Avviso: Impossibile eliminare file temporaneo: {e_unlink}")


    # --- Separatore prima del footer ---
    st.markdown("---")

    # --- IMMAGINE DI PIÈ DI PAGINA ---
    # NUOVO URL PIÈ DI PAGINA
    footer_image_url = "https://cdn.leonardo.ai/users/efef8ea0-d41a-4914-8f6f-1d8591a11f28/generations/1cf09cf6-3b12-4575-82e5-7350966327b5/Leonardo_Phoenix_10_a_mesmerizing_and_vibrant_cinematic_photo_1.jpg"                   # FOOTER IMAGE
    try:
        # Regola width se necessario per la nuova immagine
        st.image(footer_image_url, width=400) # Leggermente più larga
    except Exception as img_err:
        st.warning(f"Avviso: Impossibile caricare l'immagine di piè di pagina. {img_err}", icon="🖼️")

    # --- Caption Finale ---
    st.caption("Applicazione sviluppata con Streamlit e Google Gemini. **Consulta sempre un professionista sanitario.**")


if __name__ == "__main__":
    main()
