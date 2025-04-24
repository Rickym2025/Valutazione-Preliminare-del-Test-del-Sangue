# -*- coding: utf-8 -*-
import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
import tempfile
import os
from google.api_core import exceptions
import time

# ... (altri import e configurazioni come prima) ...
# --- Configurazione Pagina Streamlit ---
st.set_page_config(
    page_title="Valutazione Preliminare Analisi Del Sangue IA",
    page_icon="🩸", # Questa rimane per la tab del browser
    layout="wide"
)

# ... (configurazione Gemini e funzioni helper come prima) ...

# --- Funzione Main ---
def main():

    # --- IMMAGINE DI INTESTAZIONE (come prima) ---
    header_image_url = "https://www.healthtech360.it/wp-content/uploads/sites/6/2024/01/shutterstock_2145128041.jpg"
    try:
        st.image(header_image_url, use_container_width=True)
    except Exception as img_err:
        st.warning(f"Avviso: Impossibile caricare l'immagine di intestazione. {img_err}", icon="🖼️")

    # --- Titolo App ---
    # MODIFICATO: Spostata l'icona 🩸 alla fine
    st.title("⚕️ Valutazione Preliminare Analisi Del Sangue IA 🩸")
    st.markdown("Carica il tuo referto delle analisi del sangue (immagine o PDF) per ottenere una **valutazione preliminare, dettagliata e strutturata** basata su Intelligenza Artificiale.")
    st.markdown("---")

    # ... (Disclaimer, selezione tipo file, logica upload, footer come prima) ...
    st.error("""
    **🛑 ATTENZIONE MASSIMA: Leggere Prima di Procedere! 🛑**
    *   Questa applicazione fornisce un'**ANALISI AUTOMATICA E DETTAGLIATA** ma **ASSOLUTAMENTE NON MEDICA**.
    *   **NON È UNO STRUMENTO DIAGNOSTICO.** L'IA può commettere errori, interpretare male o fornire informazioni fuorvianti.
    *   L'obiettivo è solo quello di **strutturare le informazioni** presenti nel referto in modo più leggibile.
    *   **NON BASARE NESSUNA DECISIONE DI SALUTE SU QUESTI RISULTATI.**
    *   **È OBBLIGATORIO CONSULTARE IL PROPRIO MEDICO CURANTE** per l'interpretazione corretta del referto, la diagnosi e qualsiasi indicazione terapeutica.
    """)
    st.markdown("---")

    st.subheader("1. Scegli il formato del referto")
    tipo_file = st.radio(
        "Seleziona il tipo di file:",
        ("Immagine (JPG, PNG)", "Documento PDF"),
        horizontal=True, key="tipo_file_radio", label_visibility="collapsed"
    )
    st.markdown("---")

    file_caricato = None

    if tipo_file == "Immagine (JPG, PNG)":
        st.subheader("2. Carica l'Immagine del Referto")
        st.info("""
        **Come caricare l'immagine:**
        *   Clicca sul pulsante "Browse files" (o simile) nel riquadro grigio qui sotto.
        *   Oppure, trascina il file immagine dal tuo computer al riquadro grigio.
        *Consiglio: Usa un'immagine chiara e ben leggibile!*
        """, icon="💡")

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
                        # Assicurati che le funzioni helper siano definite o importate correttamente sopra
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
                        # Assicurati che le funzioni helper siano definite o importate correttamente sopra
                        testo_pdf = estrai_testo_da_pdf(percorso_tmp_file)

                    if testo_pdf:
                         with st.spinner("🤖 Elaborazione IA Dettagliata in corso... Attendere prego..."):
                              # Assicurati che le funzioni helper siano definite o importate correttamente sopra
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

    st.markdown("---")

    # --- IMMAGINE DI PIÈ DI PAGINA (come prima) ---
    footer_image_url = "https://www.cdi.it/wp-content/uploads/2023/04/Prescrizione-farmaci.jpg"
    try:
        st.image(footer_image_url, width=300)
    except Exception as img_err:
        st.warning(f"Avviso: Impossibile caricare l'immagine di piè di pagina. {img_err}", icon="🖼️")

    st.caption("Applicazione sviluppata con Streamlit e Google Gemini. **Consulta sempre un professionista sanitario.**")


if __name__ == "__main__":
    # Assicurati che le funzioni analizza_referto_medico, analisi_fallback, estrai_testo_da_pdf
    # siano definite PRIMA della chiamata a main() o importate correttamente.
    main()
