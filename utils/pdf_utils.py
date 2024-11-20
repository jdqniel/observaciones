"""PDF processing utilities."""
import streamlit as st
import pdfplumber
import tempfile
import os

@st.cache_resource
def load_pdf(pdf_file):
    """Load a PDF file with pdfplumber and cache the result."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_file_path = tmp_file.name
        
        if 'temp_files' not in st.session_state:
            st.session_state.temp_files = []
        st.session_state.temp_files.append(tmp_file_path)
        
        return pdfplumber.open(tmp_file_path)
    except Exception as e:
        st.error(f"Failed to load PDF: {str(e)}")
        return None

def cleanup_temp_files():
    """Clean up temporary files when the session ends."""
    if 'temp_files' in st.session_state:
        for temp_file in st.session_state.temp_files:
            try:
                os.remove(temp_file)
            except Exception:
                pass
        st.session_state.temp_files = []

def extract_text_from_pdf(pdf, scaled_bbox, selected_page=None):
    """Extract text from PDF within the scaled bounding box."""
    all_text = []
    pages_to_process = [selected_page] if selected_page is not None else range(len(pdf.pages))
    
    for page_number in pages_to_process:
        try:
            page = pdf.pages[page_number]
            text = page.within_bbox(scaled_bbox).extract_text()
            if text.strip():
                all_text.append(f"{text}")
        except Exception as e:
            st.warning(f"Error extracting text from page {page_number + 1}: {str(e)}")
            continue
    
    return "\n\n".join(all_text) if all_text else ""

def scale_bbox_to_pdf(bbox, canvas_dims, pdf_dims):
    """Scale the bounding box coordinates from canvas dimensions to PDF dimensions."""
    canvas_width, canvas_height = canvas_dims
    pdf_width, pdf_height = pdf_dims

    scale_x = pdf_width / canvas_width
    scale_y = pdf_height / canvas_height

    x0, y0, x1, y1 = bbox
    return (x0 * scale_x, y0 * scale_y, x1 * scale_x, y1 * scale_y)