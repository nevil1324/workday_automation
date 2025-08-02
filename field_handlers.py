# field_handlers.py
from typing import Tuple, Optional, List
from playwright.async_api import Locator, Page
from utils import close_all_popups, wait_for_popup, arbitrary_user_data

async def handle_resume_upload(page: Page, resume_path: str) -> bool:
    """Handles the resume upload process."""
    upload_button_selector = 'button[data-automation-id="select-files"]'
    try:
        upload_button = page.locator(upload_button_selector).first
        await upload_button.wait_for(state="visible", timeout=5000)
        
        if await upload_button.is_visible():
            print(f"  -> Found resume upload button. Attaching file: {resume_path}")
            async with page.expect_file_chooser() as fc_info:
                await upload_button.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(resume_path)
            print("  -> Resume file selected successfully.")
            await page.wait_for_timeout(2000)
            return True
    except Exception as e:
        print(f"  -> Resume upload failed or not found: {e}")
    return False

async def handle_multiselect(container: Locator, label_text: str, page: Page) -> Tuple[str, List[str], List[str]]:
    """Handles multi-select fields with possible nested selections."""
    field_type = "multiselect"
    await close_all_popups(page)

    input_field = container.locator('input').first
    try:
        await input_field.click(force=True)
    except Exception as e:
        print(f"⚠️ Initial click failed: {e} — trying scroll and force click")
        await input_field.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        await input_field.click(force=True)

    await page.wait_for_timeout(800)
    popup = await wait_for_popup(page)

    if not popup:
        print("⚠️ No popup appeared after clicking")
        return field_type, [], []

    values_selected = []
    preferred_option = None
    
    if "Phone Code" in label_text:
        preferred_option = "India (+91)"
        await input_field.fill("India")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1000)
        option = popup.locator(f'[role="option"]:has-text("{preferred_option}")').first
        try:
            await option.click()
            values_selected.append(preferred_option)
        except Exception as e:
            print(f"⚠️ Failed to click preferred option '{preferred_option}': {e}")
    else:
        options = await popup.locator('[role="option"]').all_text_contents()
        if options:
            first_option = popup.locator('[role="option"]').first
            option_text = await first_option.text_content()
            try:
                await first_option.click()
                values_selected.append(option_text.strip())
            except Exception as e:
                await first_option.scroll_into_view_if_needed()
                await page.wait_for_timeout(500)
                await first_option.click(force=True)
                values_selected.append(option_text.strip())

            nested_popup = await wait_for_popup(page)
            if nested_popup:
                nested_options = await nested_popup.locator('[role="option"]').all_text_contents()
                if nested_options:
                    try:
                        await nested_popup.locator('[role="option"]').first.click()
                        values_selected.append(nested_options[0])
                    except Exception as e:
                        await nested_popup.locator('[role="option"]').first.scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)
                        await nested_popup.locator('[role="option"]').first.click(force=True)
                        values_selected.append(nested_options[0])

    await page.keyboard.press("Escape")
    return field_type, [preferred_option] if preferred_option else [], values_selected

async def handle_dropdown(container: Locator, label_text: str, page: Page, automation_id: str) -> Tuple[str, List[str], Optional[str]]:
    """Handles dropdown fields."""
    field_type = "dropdown"
    options = []
    selected_value = None

    try:
        await close_all_popups(page)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

        dropdown_button = container.locator('button[aria-haspopup="listbox"]').first
        await dropdown_button.scroll_into_view_if_needed()

        if not await dropdown_button.is_visible():
            await container.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

        await dropdown_button.click()
        await page.wait_for_timeout(500)

        listboxes = page.locator('ul[role="listbox"]')
        count = await listboxes.count()
        if count == 0:
            raise Exception("No listbox found")
        
        listbox = listboxes.nth(count - 1)
        await listbox.wait_for()

        option_items = listbox.locator('li[role="option"], [role="option"]')
        count = await option_items.count()

        for i in range(count):
            item = option_items.nth(i)
            text = (await item.inner_text()).strip()
            if text and text not in options:
                options.append(text)

        if options:
            last_option_text = options[-1]
            await option_items.nth(len(options) - 1).click()
            selected_value = last_option_text

        await page.keyboard.press("Escape")
        await page.wait_for_timeout(200)

        return field_type, options, selected_value

    except Exception as e:
        print(f"⚠️ Dropdown handling failed for '{label_text}': {e}")
        return field_type, [], None