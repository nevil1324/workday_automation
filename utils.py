import os
from typing import List, Any, Optional
from playwright.async_api import Page, Locator

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
        "file": "resume.pdf", # Placeholder filename
        "checkbox": [options[0]] if options else [],
        "radio": options[0] if options else None,
        "multiselect": [options[0]] if options else [],
        "dropdown": options[0] if options else None,
    }
    return data_map.get(field_type, "")

async def handle_resume_upload(page: Page, resume_path: str) -> bool:
    """
    Specifically handles the resume upload process if the relevant section is visible.
    """
    upload_button_selector = 'button[data-automation-id="attachButton"], button[aria-label*="upload resume"], button[data-automation-id="select-files"]'
    upload_button = page.locator(upload_button_selector).first
    
    try:
        await upload_button.wait_for(state="visible", timeout=2000)
        if await upload_button.is_visible():
            async with page.expect_file_chooser() as fc_info:
                await upload_button.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(resume_path)
            await page.wait_for_timeout(5000)
            return True
    except Exception:
        return False

async def close_all_popups(page: Page):
    """Close any open popups by pressing Escape multiple times"""
    for _ in range(3):
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

async def wait_for_popup(page: Page, timeout=5000) -> Optional[Locator]:
    """Wait for and return the first visible popup"""
    try:
        await page.wait_for_selector('div[role="listbox"]:visible, div[data-automation-id="menu"]:visible', timeout=timeout)
        return page.locator('div[role="listbox"]:visible, div[data-automation-id="menu"]:visible').first
    except:
        return None