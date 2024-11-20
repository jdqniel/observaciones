"""Image processing utilities."""
import streamlit as st
from PIL import Image
from config import PDF_CONFIG

def extract_page_image(pdf, page_number):
    """Extract and resize the image of a specific page from a PDF."""
    try:
        page = pdf.pages[page_number]
        image = page.to_image(resolution=PDF_CONFIG["image_resolution"])
        img_pil = image.original

        scale_factor = min(
            PDF_CONFIG["max_image_width"] / img_pil.width,
            PDF_CONFIG["max_image_height"] / img_pil.height
        )
        new_width = int(img_pil.width * scale_factor)
        new_height = int(img_pil.height * scale_factor)
        
        img_resized = img_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return img_resized, (new_width, new_height), (page.width, page.height)
    except Exception as e:
        st.error(f"Error processing page image: {str(e)}")
        return None, None, None