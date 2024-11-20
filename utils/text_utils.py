import io
import re
import vertexai
from vertexai.generative_models import GenerativeModel
import json
import streamlit as st
from .auth_utils import check_credentials
import pandas as pd

def extract_json_objects(text):
    """Extract all valid JSON objects from text."""
    objects = []
    current = ""
    depth = 0
    
    for char in text:
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        current += char
            
        if depth == 0 and current.strip():
            try:
                json_str = current.strip().replace('\n', ' ')
                json_data = json.loads(json_str)
                objects.append(json_data)
                current = ""
            except:
                pass
            
    return objects

def split_text_into_sections(text):
    sections = []
    pattern = r'\d+\.+\d+\.\s*(?:OBSERVACIÓN|Observación)'
    matches = list(re.finditer(pattern, text, re.MULTILINE))
    
    if not matches:
        return sections
    
    for i in range(len(matches)):
        start_pos = matches[i].start()
        if i == len(matches) - 1:
            section_text = text[start_pos:].strip()
        else:
            next_pos = matches[i + 1].start()
            section_text = text[start_pos:next_pos].strip()
        
        section_number = re.match(r'\d+\.+\d+\.', section_text)
        if section_number:
            title = section_number.group(0)
            sections.append((title, section_text))
    
    return sections

def init_vertex_ai():
    if not check_credentials():
        st.error("Please configure Google Cloud credentials first.")
        return None
        
    try:
        project_id = st.session_state.get('project_id')
        vertexai.init(project=project_id, location="us-central1")
        return GenerativeModel("gemini-1.5-pro")
    except Exception as e:
        st.error(f"Error initializing Vertex AI: {str(e)}")
        return None

DEFAULT_PROMPT = """Eres un experto analizando documentos de auditoría.
Te voy proporcionar un documento que contiene observaciones y sus respuestas a un informe técnico.

Quiero que estructures el contenido de las observaciones y respuestas en un formato JSON.
Reglas:
- El texto debe ser transcrito, no debe ser interpretado, resumido o parafraseado.

Algunas de las observaciones que te voy a dar poseen literales, otras no.

Para las observaciones sin literales usa la siguiente estructura:
Retorna los resultados así:
[
    {{
        "Numero_de_observacion": "número exacto",
        "Descripcion": "descripción principal",
        "Informacion_Complementaria": "información adicional o null",
        "Respuesta": "respuesta encontrada o null",
        "Estado": "Absuelta|No Absuelta|Invalidada"
    }},
    // más objetos si hay más observaciones
]

Si el texto contiene literales usa la siguiente estructura:

Retorna los resultados así:
[
    {{
        "Numero_de_observacion": "número exacto",
        "Descripcion": "descripción de la observación“,
        "Informacion_Complementaria": "información adicional o null",
	“Literal” : “letra del literal”
        "Respuesta": "respuesta del literal encontrada o null",
        "Estado": "Absuelta|No Absuelta|Invalidada"
    }},
    // más objetos si hay literales
]

Texto a analizar: {text}

Instrucciones:
1. Identifica cada observación en el texto
2. Para cada observación:
   - Extrae el número exacto (ej: "1.1", "2.3")
   - Identifica la descripción principal del problema
   - Busca información complementaria que sustente la observación
   - Identifica si hay una respuesta o descargo
   - Determina el estado basado en el contexto

Si solo hay una observación, retorna un único objeto JSON sin lista.
Retorna SOLO el JSON o array de JSONs, sin texto adicional.
"""
async def process_section_with_vertex_stream(model, section_text, placeholder):
    try:
        custom_prompt = st.session_state.get('custom_prompt', DEFAULT_PROMPT)
        prompt = custom_prompt.format(text=section_text)
        
        placeholder.info("Processing...")
        response = model.generate_content(prompt, generation_config={"max_output_tokens": 8192,"temperature": 1,"top_p": 0.95,}, stream=True)
        
        output = ""
        for chunk in response:
            if hasattr(chunk, 'text'):
                output += chunk.text.strip()
                clean_output = output.replace('\n', ' ')
                
                # Try to parse and format as list
                try:
                    if clean_output.startswith('['):
                        json_data = json.loads(clean_output)
                    else:
                        # If it's a valid single object, wrap it in a list
                        single_obj = json.loads(clean_output)
                        json_data = [single_obj]
                    placeholder.json(json_data)
                except:
                    placeholder.code(output)
        
        # Final parsing with list enforcement
        try:
            clean_output = output.replace('\n', ' ').strip()
            if clean_output.startswith('['):
                return json.loads(clean_output)
            elif clean_output.startswith('```'):
                objects = merge_json_responses(clean_output)
                return objects
            else:
                # Ensure single objects are returned as a list
                single_obj = json.loads(clean_output)
                return [single_obj]
        except:
            return create_error_response()
            
    except Exception as e:
        placeholder.error(f"Error: {str(e)}")
        return create_error_response()

def merge_json_responses(text):
    """Merge multiple JSON objects in text into a list."""
    # Find all JSON objects in the text
    json_pattern = r'\{[^{}]*\}'
    matches = re.finditer(json_pattern, text)
    
    json_objects = []
    for match in matches:
        try:
            json_obj = json.loads(match.group())
            json_objects.append(json_obj)
        except:
            continue
    
    return json_objects if json_objects else create_error_response()

def create_error_response():
    """Create a standard error response wrapped in a list."""
    return [{
        "Numero_de_observacion": "Error",
        "Descripcion": "Error al procesar",
        "Informacion_Complementaria": None,
        "Respuesta": None,
        "Estado": "No Absuelta"
    }]

async def process_sections_with_ai(sections):
    model = init_vertex_ai()
    if not model:
        return []
    
    processed_sections = []
    progress_bar = st.progress(0)
    
    for idx, (title, content) in enumerate(sections):
        st.markdown(f"### Processing Section {title}")
        placeholder = st.empty()
        
        result = await process_section_with_vertex_stream(model, content, placeholder)
        
        if isinstance(result, list):
            for i, json_obj in enumerate(result, 1):
                processed_sections.append((f"{title}.{i}", content, json_obj))
        else:
            processed_sections.append((title, content, result))
            
        progress_bar.progress((idx + 1) / len(sections))
    
    progress_bar.empty()
    return processed_sections

def format_sections_for_download(sections, pdf_name):
    data = []
    for title, content, json_data in sections:
        if isinstance(json_data, list):
            for obj in json_data:
                data.append({
                    "Numero_de_observacion": obj["Numero_de_observacion"],
                    "Descripcion": obj["Descripcion"],
                    "Informacion_Complementaria": obj["Informacion_Complementaria"],
                    "Literal": obj.get("Literal", None),
                    "Respuesta": obj["Respuesta"],
                    "Estado": obj["Estado"]
                })
        else:
            data.append({
                "Numero_de_observacion": json_data["Numero_de_observacion"],
                "Descripcion": json_data["Descripcion"],
                "Informacion_Complementaria": json_data["Informacion_Complementaria"],
                "Literal": json_data.get("Literal", None),
                "Respuesta": json_data["Respuesta"],
                "Estado": json_data["Estado"]
            })
    
    return pd.DataFrame(data)

def generate_excel_file(sections, pdf_name):
    """Generate an Excel file from the extracted sections."""
    df = format_sections_for_download(sections, pdf_name)
    
    if df.empty:
        return None
    
    excel_file = io.BytesIO()
    df.to_excel(excel_file, index=False, engine='openpyxl')
    excel_file.seek(0)
    
    return excel_file.read()