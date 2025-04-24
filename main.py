# (Assicurati che gli import e le funzioni helper sopra main() siano corretti)

# --- Funzione Main ---
def main():

    # Inizializza session state se non esiste
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'processed_file_id' not in st.session_state:
        st.session_state.processed_file_id = None
    if 'current_file_type' not in st.session_state:
         st.session_state.current_file_type = "Immagine (JPG, PNG)" # Default iniziale

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

    # --- Disclaimer Principale ---
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
    # QUESTA SEZIONE DEVE VENIRE PRIMA DELLA SEZIONE 2
    col_select, col_img1 = st.columns([3, 1], gap="medium")

    def clear_analysis_on_type_change():
         st.session_state.analysis_result = None
         st.session_state.processed_file_id = None

    with col_select:
        st.subheader("1. Scegli il formato del referto")
        # LA VARIABILE 'tipo_file' VIENE DEFINITA QUI
        tipo_file = st.radio(
            "Seleziona il tipo di file:",
            ("Immagine (JPG, PNG)", "Documento PDF"),
            horizontal=True,
            key="tipo_file_radio_key",
            label_visibility="collapsed",
            on_change=clear_analysis_on_type_change
        )
        # Aggiorna lo stato (opzionale ma buona pratica)
        st.session_state.current_file_type = tipo_file

    with col_img1:
        section1_image_url = "https://www.cdi.it/wp-content/uploads/2021/08/shutterstock_1825232600-800x450-1.jpg"
        try:
            st.image(section1_image_url, width=200)
        except Exception as img_err:
             st.warning(f"Avviso: Impossibile caricare l'immagine Sezione 1. ({img_err})", icon="🖼️")

    st.markdown("---") # Separatore DOPO la sezione 1

    # --- Sezione 2: Caricamento File con Immagine Decorativa ---
    # QUESTA SEZIONE DEVE VENIRE DOPO LA SEZIONE 1
    st.subheader("2. Carica il Referto")
    col_upload, col_filler_img = st.columns([3, 1], gap="medium")

    with col_filler_img:
        filler_image_url = "https://cdn.leonardo.ai/users/efef8ea0-d41a-4914-8f6f-1d8591a11f28/generations/1cf09cf6-3b12-4575-82e5-7350966327b5/Leonardo_Phoenix_10_a_mesmerizing_and_vibrant_cinematic_photo_1.jpg"
        try:
            st.image(filler_image_url, width=200)
        except Exception as img_err:
            st.warning(f"Avviso: Impossibile caricare l'immagine decorativa. ({img_err})", icon="🎨")

    file_caricato = None # Resetta qui
    with col_upload:
        # LA VARIABILE 'tipo_file' VIENE USATA QUI, DOPO ESSERE STATA DEFINITA
        if tipo_file == "Immagine (JPG, PNG)":
            st.info("""
            **Carica l'immagine del tuo referto:**
            *   Clicca sul pulsante "Browse files" (o simile) qui sotto.
            *   Oppure, trascina il file (JPG, PNG) dal tuo computer nell'area grigia.

            *Suggerimento: Assicurati che l'immagine sia chiara e leggibile.*
            """) # Rimosso icona potenzialmente problematica
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


    # --- Logica di Analisi Automatica (come prima) ---
    analysis_placeholder = st.empty()

    if file_caricato is not None:
        current_file_id = f"{file_caricato.name}_{file_caricato.size}"

        if current_file_id != st.session_state.processed_file_id:
            st.session_state.analysis_result = None
            st.session_state.processed_file_id = current_file_id

            with analysis_placeholder.container():
                st.success(f"File '{file_caricato.name}' caricato. Avvio analisi automatica...")
                st.warning("Ricorda i limiti dell'IA e consulta il medico!")

                analisi_output = None
                if tipo_file == "Immagine (JPG, PNG)":
                    try:
                        immagine = Image.open(file_caricato)
                        st.image(immagine, caption="Anteprima Referto Caricato", use_container_width=True)
                        st.markdown("---")
                        with st.spinner("🔬 Analisi dettagliata IA in corso... Potrebbe richiedere più tempo..."):
                            analisi_output = analizza_referto_medico(immagine, "immagine")
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
                                analisi_output = analizza_referto_medico(testo_pdf, "testo")
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
                     st.markdown(st.session_state.analysis_result)

        elif st.session_state.analysis_result:
             with analysis_placeholder.container():
                 if tipo_file == "Immagine (JPG, PNG)":
                     try:
                         immagine = Image.open(file_caricato)
                         st.image(immagine, caption="Anteprima Referto (già analizzato)", use_container_width=True)
                         st.markdown("---")
                     except: pass
                 st.subheader("✅ Risultati Valutazione IA Dettagliata (Precedente)")
                 st.markdown(st.session_state.analysis_result)

    else:
         if st.session_state.processed_file_id is not None:
              st.session_state.analysis_result = None
              st.session_state.processed_file_id = None
              analysis_placeholder.empty()


    # --- Separatore e Caption Finale ---
    st.markdown("---")
    st.caption("Applicazione sviluppata con Streamlit e Google Gemini. **Consulta sempre un professionista sanitario.**")

# --- Assicurati che tutte le funzioni (analizza_referto_medico, etc.) siano definite PRIMA di questa linea ---
if __name__ == "__main__":
    main()
