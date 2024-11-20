"""UI components for the Streamlit app."""
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from config import CANVAS_CONFIG
import json
from utils.auth_utils import check_credentials, parse_credentials_file, get_credentials_status, clear_credentials
from utils.text_utils import DEFAULT_PROMPT, generate_excel_file

def render_prompt_editor():
    """Render the prompt editor in the sidebar."""
    with st.sidebar:
        st.header("🤖 Prompt Configuration")

        if 'custom_prompt' not in st.session_state:
            st.session_state.custom_prompt = DEFAULT_PROMPT

        prompt = st.text_area(
            "Editar Prompt",
            value=st.session_state.custom_prompt,
            height=300,
            help="Use {text} como placeholder para el contenido de la sección"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Actualizar"):
                st.session_state.custom_prompt = prompt
                st.success("✅ Prompt actualizado")
        with col2:
            if st.button("Restaurar Default"):
                st.session_state.custom_prompt = DEFAULT_PROMPT
                st.success("🔄 Prompt restaurado")

        st.divider()
                    
def render_auth_section():
    """Render the authentication section."""
    with st.sidebar:
        st.header("🔑 Google Cloud Auth")
        
        cred_status = get_credentials_status()
        
        if cred_status["status"] == "not_configured":
            st.warning("Google Cloud credentials not configured")
            
            with st.expander("ℹ️ How to get credentials"):
                st.markdown("""
                1. Go to Google Cloud Console
                2. Create or select a project
                3. Enable Vertex AI API
                4. Create a service account
                5. Create and download JSON key
                """)
            
            # Credentials uploader
            uploaded_file = st.file_uploader(
                "Upload credentials.json",
                type=['json'],
                help="Upload your Google Cloud service account key file"
            )
            
            if uploaded_file:
                if parse_credentials_file(uploaded_file):
                    st.success("✅ Credentials configured successfully!")
                    st.rerun()
        else:
            st.success("✅ Credentials configured")
            st.code(f"Project ID: {cred_status['project_id']}", language="bash")
            
            if st.button("🗑️ Clear Credentials", type="secondary"):
                if clear_credentials():
                    st.success("Credentials cleared successfully!")
                    st.rerun()

def render_sidebar():
    """Render the sidebar components."""
    with st.sidebar:
        uploaded_pdf = st.file_uploader("Choose a PDF file", type=["pdf"])
        
        if uploaded_pdf:
            st.session_state['pdf_name'] = uploaded_pdf.name
            
        extract_mode = st.radio(
            "Extraction Mode",
            ["Current Page Only", "All Pages"],
            help="Choose whether to extract text from the current page or search the same region across all pages"
        )
        
        return uploaded_pdf, extract_mode

def render_canvas(img_pil, canvas_dims, page_number):
    """Render the drawable canvas."""
    width, height = canvas_dims
    
    # Render canvas
    canvas_result = st_canvas(
        fill_color=CANVAS_CONFIG["fill_color"],
        stroke_width=CANVAS_CONFIG["stroke_width"],
        stroke_color=CANVAS_CONFIG["stroke_color"],
        background_image=img_pil,
        drawing_mode="rect",
        update_streamlit=True,
        width=width,
        height=height,
        key=f"canvas_{page_number}",
    )
    
    # Show coordinates if a box is drawn
    if canvas_result.json_data and canvas_result.json_data["objects"]:
        last_object = canvas_result.json_data["objects"][-1]
        
        # Get coordinates
        left = int(last_object['left'])
        top = int(last_object['top'])
        width = int(last_object['width'])
        height = int(last_object['height'])
        
        # Display coordinates
        st.sidebar.code(f"""
        Top-left:     ({left}, {top})
        Width/Height: {width} x {height}
        Bottom-right: ({left + width}, {top + height})
        """)
    
    return canvas_result

def render_sections(sections, page_number):
    """Render the extracted sections with structured data."""
    st.subheader("📑 Extracted Sections")
    
    for title, content, data in sections:
        st.markdown(f"### Section {title}")
        
        # Original content
        st.markdown("#### Original Content")
        st.text_area(
            label="Raw Text",
            value=content,
            height=200,
            key=f"section_raw_{title}_{page_number}",
            disabled=True
        )
        
        # Show structured data
        st.markdown("#### Structured Data")
        if isinstance(data, list):
            for idx, json_obj in enumerate(data, 1):
                st.markdown(f"**Object {idx}**")
                st.json(json_obj)
                show_status(json_obj)
        else:
            st.json(data)
            show_status(data)
        
        st.markdown("---")

def show_status(json_obj):
    status = json_obj.get("Estado", "No Absuelta")
    status_color = {
        "Absuelta": "#28a745",
        "No Absuelta": "#dc3545",
        "Invalidada": "#6c757d"
    }.get(status, "#dc3545")
    
    st.markdown(
        f"""
        <div style='
            padding: 10px;
            background-color: {status_color};
            border-radius: 5px;
            color: white;
            text-align: center;
            margin-top: 10px;
            margin-bottom: 20px;
            font-weight: bold;
        '>
            {status}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_download_buttons(formatted_text, markdown_text, sections):
    """Render the download buttons."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            "📥 Download as TXT",
            formatted_text,
            file_name=f"extracted_sections_{st.session_state.get('pdf_name', 'document')}.txt",
            mime="text/plain",
        )
    
    with col2:
        st.download_button(
            "📥 Download as MD",
            markdown_text,
            file_name=f"extracted_sections_{st.session_state.get('pdf_name', 'document')}.md",
            mime="text/markdown",
        )
    
    with col3:
        json_data = [
            {
                "section": title,
                "content": content,
                "structured_data": structured_data
            }
            for title, content, structured_data in sections
        ]
        
        json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
        
        st.download_button(
            "📥 Download as JSON",
            json_str,
            file_name=f"extracted_sections_{st.session_state.get('pdf_name', 'document')}.json",
            mime="application/json",
        )

def render_excel_export(sections, pdf_name):
    """Render the section for exporting data to Excel."""
    excel_bytes = generate_excel_file(sections, pdf_name)
    
    if excel_bytes:
        st.subheader("📊 Export to Excel")
        excel_file = f"extracted_sections_{pdf_name}.xlsx"
        st.download_button(
            "📥 Download as XLSX",
            excel_bytes,
            file_name=excel_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning("No data available to export to Excel.")
