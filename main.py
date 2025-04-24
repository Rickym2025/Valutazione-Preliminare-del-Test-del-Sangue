# -*- coding: utf-8 -*-
import streamlit as st
# ... altri import ...

# ... Configurazioni e funzioni helper (analizza_referto_medico, etc.) ...

# --- Funzione Main ---
def main():
    # ... (Inizializzazioni session_state, immagine intestazione, titolo, disclaimer iniziale, sezione 1) ...

    st.markdown("---")

    # --- Sezione 2: Caricamento File con Immagine Decorativa ---
    st.subheader("2. Carica il Referto")
    col_upload, col_filler_img = st.columns([3, 1], gap="medium")

    with col_filler_img:
        # ... (immagine decorativa come prima) ...
        filler_image_url = "https://cdn.leonardo.ai/users/efef8ea0-d41a-4914-8f6f-1d8591a11f28/generations/1cf09cf6-3b12-4575-82e5-7350966327b5/Leonardo_Phoenix_10_a_mesmerizing_and_vibrant_cinematic_photo_1.jpg"
        try:
            st.image(filler_image_url, width=200)
        except Exception as img_err:
            st.warning(f"Avviso: Impossibile caricare l'immagine decorativa. ({img_err})", icon="🎨")


    file_caricato = None
    with col_upload:
        if tipo_file == "Immagine (JPG, PNG)":
            # === MODIFICA QUI: Rimosso icon="🖼️" ===
            st.info("""
            **Carica l'immagine del tuo referto:**
            *   Clicca sul pulsante "Browse files" (o simile) qui sotto.
            *   Oppure, trascina il file (JPG, PNG) dal tuo computer nell'area grigia.

            *Suggerimento: Assicurati che l'immagine sia chiara e leggibile.*
            """) # Icona rimossa
            file_caricato = st.file_uploader(
                "Carica Immagine",
                 type=["jpg", "jpeg", "png"], key="uploader_img",
                 label_visibility="collapsed", help="Trascina o clicca per selezionare un file JPG, JPEG o PNG (max 200MB)"
            )
            st.caption("Formati accettati: JPG, JPEG, PNG.")

        elif tipo_file == "Documento PDF":
            # Lasciamo l'icona per il PDF se non dà problemi, altrimenti rimuovi anche icon="📄"
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

    # ... (Logica di analisi automatica come prima) ...

    # --- Separatore e Caption Finale ---
    st.markdown("---")
    st.caption("Applicazione sviluppata con Streamlit e Google Gemini. **Consulta sempre un professionista sanitario.**")


if __name__ == "__main__":
    main()
