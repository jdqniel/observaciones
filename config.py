"""Configuration settings for the PDF Text Extractor."""
from typing import Literal

# Page Configuration with proper literal types
PAGE_CONFIG = {
    "page_title": "PDF Text Extractor",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# PDF Processing Configuration
PDF_CONFIG = {
    "max_image_width": 800,
    "max_image_height": 1000,
    "image_resolution": 150
}

# Regular Expression Pattern
PATTERNS = {
    "observation": r"(\d+\.\s*(?:OBSERVACIÓN|Observación).*?)(?=\d+\.\s*(?:OBSERVACIÓN|Observación)|$)"
}

# UI Configuration
CANVAS_CONFIG = {
    "fill_color": "rgba(255, 0, 0, 0.1)",
    "stroke_width": 2,
    "stroke_color": "#FF0000",
    "drawing_mode": "rect"
}