import os
from dotenv import load_dotenv

# --- Configuration & Constants ---
# Using a set of possible selectors for the "next" button increases robustness.
NEXT_BUTTON_SELECTORS = [
    'button[data-automation-id="pageFooterNextButton"]',
    'button[data-automation-id="saveAndContinueButton"]',
    'button[data-automation-id="nextButton"]',
]

def get_env_credentials():
    """Loads credentials, URL, and resume path from .env file."""
    load_dotenv()
    email = os.getenv("WORKDAY_EMAIL")
    password = os.getenv("WORKDAY_PASSWORD")
    tenant_url = os.getenv("WORKDAY_URL")
    resume_path = os.getenv("RESUME_PATH")
    if not all([email, password, tenant_url, resume_path]):
        raise ValueError(
            "Missing one or more environment variables. "
            "Please create a .env file with WORKDAY_EMAIL, WORKDAY_PASSWORD, WORKDAY_URL, and RESUME_PATH."
        )
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"The resume file was not found at the specified path: {resume_path}")
    return email, password, tenant_url, resume_path