# utils.py
import os
from dotenv import load_dotenv
from typing import List, Optional, Any, Dict
from playwright.async_api import Page, Locator

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

def get_text_input_value(label_text: str, input_id: str) -> str:
    label_lower = label_text.lower()
    input_id_lower = input_id.lower()

    if "linkedin" in label_lower or "linkedin" in input_id_lower:
        return "https://www.linkedin.com/in/test-user/"
    elif "email" in label_lower or "@" in label_lower or "e-mail" in label_lower or "email" in input_id_lower:
        return "test@example.com"
    elif "phone" in label_lower or "contact" in label_lower or "mobile" in label_lower or "phone" in input_id_lower:
        return "9345678900"
    elif "name" in label_lower:
        return "John Doe"
    elif "address" in label_lower:
        return "123 Main Street"
    elif "city" in label_lower:
        return "New York"
    elif "zip" in label_lower or "postal" in label_lower:
        return "SW1A 1AA"
    else:
        return "Test Input"

async def close_all_popups(page: Page):
    """Close lingering dropdowns or multiselect panels that block interaction."""
    try:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(100)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(200)
        
        body = page.locator("body")
        await body.click(position={"x": 5, "y": 5})
        await page.wait_for_timeout(300)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
    except Exception as e:
        print(f"[close_all_popups] warning: {e}")

async def wait_for_popup(page: Page, timeout=5000) -> Optional[Locator]:
    """Wait for and return the first visible popup"""
    try:
        await page.wait_for_selector('div[role="listbox"]:visible, div[data-automation-id="menu"]:visible', timeout=timeout)
        return page.locator('div[role="listbox"]:visible, div[data-automation-id="menu"]:visible').first
    except:
        return None

def arbitrary_user_data(field_type: str, options: Optional[List[str]] = None, label: Optional[str] = "") -> Any:
    """Provides arbitrary, valid-looking data for filling forms based on field type."""
    if options is None:
        options = []
    
    label_lower = label.lower()
    if "first name" in label_lower or "given name" in label_lower:
        return "John"
    if "last name" in label_lower or "family name" in label_lower:
        return "Doe"
    if "city" in label_lower:
        return "Pune"

    data_map = {
        "text": "Test Value",
        "textarea": "This is a test paragraph.",
        "date": "2024-01-15",
        "file": "resume.pdf",
        "checkbox": [options[0]] if options else [],
        "radio": options[0] if options else None,
        "multiselect": [options[0]] if options else [],
        "dropdown": options[0] if options else None,
    }
    return data_map.get(field_type, "")