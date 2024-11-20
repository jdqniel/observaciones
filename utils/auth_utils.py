"""Authentication utilities for Google Cloud."""
import streamlit as st
import json
import os
from pathlib import Path

def parse_credentials_file(uploaded_file):
    """Parse uploaded credentials file and set up authentication."""
    try:
        credentials_json = json.load(uploaded_file)
        
        # Create a temporary credentials directory if it doesn't exist
        temp_dir = Path("temp_credentials")
        temp_dir.mkdir(exist_ok=True)
        
        # Save credentials to a temporary file
        credentials_path = temp_dir / "credentials.json"
        with open(credentials_path, "w") as f:
            json.dump(credentials_json, f)
        
        # Set environment variable
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
        
        # Store project ID in session state
        if 'project_id' in credentials_json:
            st.session_state['project_id'] = credentials_json['project_id']
        
        return True
    except Exception as e:
        st.error(f"Error processing credentials: {str(e)}")
        return False

def check_credentials():
    """Check if credentials are set up."""
    return (
        "GOOGLE_APPLICATION_CREDENTIALS" in os.environ and
        os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]) and
        'project_id' in st.session_state
    )

def clear_credentials():
    """Clear stored credentials."""
    try:
        if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            cred_path = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
            if cred_path.exists():
                cred_path.unlink()
            if cred_path.parent.name == "temp_credentials":
                try:
                    cred_path.parent.rmdir()
                except:
                    pass  # Directory might not be empty
        
        # Clear environment variables and session state
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        st.session_state.pop('project_id', None)
        return True
    except Exception as e:
        st.error(f"Error clearing credentials: {str(e)}")
        return False

def get_credentials_status():
    """Get current credentials status information."""
    if check_credentials():
        return {
            "status": "configured",
            "project_id": st.session_state.get('project_id', 'Unknown'),
            "credentials_path": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "Not set")
        }
    return {
        "status": "not_configured",
        "project_id": None,
        "credentials_path": None
    }
