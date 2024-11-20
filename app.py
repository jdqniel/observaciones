import streamlit as st
import asyncio
from config import PAGE_CONFIG
from utils.pdf_utils import load_pdf, cleanup_temp_files, extract_text_from_pdf, scale_bbox_to_pdf
from utils.image_utils import extract_page_image
from utils.text_utils import split_text_into_sections, process_sections_with_ai, format_sections_for_download
from ui.components import (
    render_excel_export,
    render_prompt_editor,
    render_sidebar,
    render_canvas,
    render_sections,
    render_download_buttons,
    render_auth_section
)

# Must be the first Streamlit command
st.set_page_config(**PAGE_CONFIG) # type: ignore

async def main():
    """Main application function."""
    st.title("📄 PDF Text Extractor")
    
    # First render authentication section
    render_auth_section()
    render_prompt_editor()
    
    st.markdown("""
    ### Instructions:
    1. Upload a PDF file using the sidebar
    2. Select a page to view
    3. Draw a box around the text you want to extract
    4. The extracted text will be split into sections and processed with AI
    """)

    uploaded_pdf, extract_mode = render_sidebar()

    if uploaded_pdf:
        pdf = load_pdf(uploaded_pdf)

        if pdf:
            total_pages = len(pdf.pages)
            page_number = st.sidebar.slider("Select Page", 1, total_pages, 1) - 1

            img_pil, canvas_dims, pdf_dims = extract_page_image(pdf, page_number)
            
            if img_pil:
                st.write(f"📃 Page {page_number + 1} of {total_pages}")
                
                canvas_result = render_canvas(img_pil, canvas_dims, page_number)

                if canvas_result.json_data and canvas_result.json_data["objects"]:
                    last_object = canvas_result.json_data["objects"][-1]
                    x0, y0 = last_object['left'], last_object['top']
                    x1, y1 = x0 + last_object['width'], y0 + last_object['height']
                    
                    scaled_bbox = scale_bbox_to_pdf((x0, y0, x1, y1), canvas_dims, pdf_dims)
                    
                    with st.spinner("Extracting text..."):
                        selected_page = page_number if extract_mode == "Current Page Only" else None
                        extracted_text = extract_text_from_pdf(pdf, scaled_bbox, selected_page)

                    if extracted_text.strip():
                        st.success("Text extracted successfully!")
                        
                        sections = split_text_into_sections(extracted_text)
                        
                        if sections:
                            # Process sections with AI (now with streaming)
                            sections_with_data = await process_sections_with_ai(sections)
                            
                            render_sections(sections_with_data, page_number)
                            render_excel_export(sections_with_data, st.session_state.get('pdf_name', 'document'))

                        else:
                            st.warning("No sections found in the extracted text.")
                            st.text_area(
                                "Raw Extracted Text:",
                                extracted_text,
                                height=300,
                                key=f"text_area_{page_number}"
                            )
                    else:
                        st.warning("No text found in the selected area.")
                else:
                    st.info("Draw a box around the text you want to extract.")
            else:
                st.error("Failed to process the selected page.")
        else:
            st.error("Invalid PDF file. Please try again.")
    else:
        st.info("👆 Upload a PDF file to start extracting text.")

if __name__ == "__main__":
    asyncio.run(main())
