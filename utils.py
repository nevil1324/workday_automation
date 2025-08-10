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
    
    elif "github" in label_lower or "github" in input_id_lower:
        return "https://github.com/test-user"
    
    elif "portfolio" in label_lower or "portfolio" in input_id_lower:
        return "https://test-user-portfolio.com"
    
    elif "website" in label_lower or "website" in input_id_lower:
        return "https://test-user-website.com"
    
    elif "facebook" in label_lower or "facebook" in input_id_lower:
        return "https://www.facebook.com/test.user"
    
    elif "twitter" in label_lower or "twitter" in input_id_lower:
        return "https://twitter.com/test_user"
    
    elif "url" in label_lower or "website" in label_lower or "link" in label_lower:
        return "https://example.com"
    
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

from typing import Optional, List, Any
def arbitrary_user_data(field_type: str, options: Optional[List[str]] = None, label: Optional[str] = "") -> Any:
    if options is None:
        options = []

    label_lower = label.lower()

    if field_type == "date-mmddyyyy":
        return "08/10/2025"
    if field_type == "date-mmyyyy":
        return "08/2023"

    if "first name" in label_lower or "given name" in label_lower:
        return "John"
    if "last name" in label_lower or "family name" in label_lower:
        return "Doe"
    if "full name" in label_lower or "name" in label_lower:
        return "John Doe"
    if "email" in label_lower:
        return "john.doe@example.com"
    if "phone" in label_lower or "mobile" in label_lower:
        return "+1 555-123-4567"
    if "city" in label_lower:
        return "Pune"
    if "state" in label_lower:
        return "Maharashtra"
    if "country" in label_lower:
        return "India"
    if "zip" in label_lower or "postal" in label_lower:
        return "411001"
    if "address" in label_lower:
        return "123 Main Street"
    if "date of birth" in label_lower or "dob" in label_lower:
        return "08/15/1995"  # MM/DD/YYYY
    if "month" in label_lower and "year" in label_lower:
        return "08/2023"
    if "date" in label_lower:
        return "08/08/2022"
    if "url" in label_lower or "website" in label_lower or "link" in label_lower:
        return "https://example.com"
    

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

    return data_map.get(field_type, "Test Input")
