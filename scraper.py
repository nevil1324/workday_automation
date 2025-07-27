from typing import Dict, List, Any
from playwright.async_api import Page, Locator
from datetime import datetime # Import datetime
from utils import arbitrary_user_data, handle_resume_upload, close_all_popups, wait_for_popup
from config import NEXT_BUTTON_SELECTORS

async def extract_form_fields_from_page(page: Page) -> List[Dict[str, Any]]:
    """
    Scans the page for form fields, fills them with test data, and extracts their properties into a structured list.
    """
    fields = []
    processed_handles = set()
    while True:
        field_containers = await page.locator('[data-automation-id^="formField-"]').all()
        new_containers = []
        for container in field_containers:
            container_handle = await container.evaluate_handle("el => el")
            if container_handle not in processed_handles:
                processed_handles.add(container_handle)
                automation_id = await container.get_attribute("data-automation-id")
                new_containers.append((automation_id, container))
        if not new_containers:
            break
        for automation_id, container in new_containers:
            try:
                legend_loc = container.locator("legend").first
                label_loc = container.locator("label").first
                label_text = ""
                if await legend_loc.count() > 0:
                    label_text = await legend_loc.locator("span").first.text_content() or ""
                else:
                    label_text = await label_loc.text_content() or ""
                if not label_text:
                    input_with_label = container.locator('[aria-labelledby]').first
                    if await input_with_label.count() > 0:
                        label_id = await input_with_label.get_attribute("aria-labelledby")
                        if label_id:
                            label_elem = page.locator(f'#{label_id}')
                            label_text = await label_elem.text_content() or ""
                is_required = "*" in label_text
                label_text = label_text.replace("*", "").strip()
                if not label_text:
                    continue
                field_type, options, value_from_page = "unknown", [], ""
                multiselect_container = container.locator('[data-automation-id="multiSelectContainer"]')
                dropdown_button = container.locator('button[aria-haspopup="listbox"]')
                if await container.locator('[data-automation-id="multiSelectContainer"]').count() > 0:
                    field_type = "multiselect"
                    
                    await close_all_popups(page)
                    
                    input_field = container.locator('input').first
                    await input_field.click()
                    await page.wait_for_timeout(1000)
                    
                    popup = await wait_for_popup(page)
                    if popup:
                        options = await popup.locator('[role="option"]').all_text_contents()
                        if options:
                            first_option = popup.locator('[role="option"]').first
                            option_text = await first_option.text_content()
                            await first_option.click()
                            value_from_page = [option_text.strip()]
                            
                            nested_popup = await wait_for_popup(page)
                            if nested_popup:
                                nested_options = await nested_popup.locator('[role="option"]').all_text_contents()
                                if nested_options:
                                    first_nested = nested_popup.locator('[role="option"]').first
                                    await first_nested.click()
                                    value_from_page.append(nested_options[0])
                    await page.keyboard.press("Escape")
                elif await dropdown_button.count() > 0:
                    field_type = "dropdown"
                    element_to_click = dropdown_button.first
                    await container.scroll_into_view_if_needed()
                    await close_all_popups(page)
                    await element_to_click.click()
                    await page.wait_for_timeout(300)
                    listbox_popup = page.locator('div[role="listbox"]:visible').first
                    try:
                        await listbox_popup.wait_for(state="visible", timeout=5000)
                    except Exception as e:
                        raise
                    options = await listbox_popup.locator('[role="option"]').all_text_contents()
                    user_value = arbitrary_user_data(field_type, options, label_text)
                    for option in await listbox_popup.locator('[role="option"]').all():
                        text = (await option.text_content() or "").strip()
                        if text == user_value:
                            await option.scroll_into_view_if_needed()
                            await option.click()
                            value_from_page = user_value
                            break
                    else:
                        pass # Option not found in dropdown options
                    await page.keyboard.press("Escape")
                elif await container.locator('input[type="radio"]').count() > 0:
                    field_type = "radio"
                    radio_inputs = await container.locator('input[type="radio"]').all()
                    for radio in radio_inputs:
                        radio_id = await radio.get_attribute("id")
                        if radio_id:
                            radio_label = await container.locator(f'label[for="{radio_id}"]').text_content()
                            if radio_label:
                                options.append(radio_label.strip())
                    user_value = arbitrary_user_data(field_type, options, label_text)
                    await container.locator(f'label:has-text("{user_value}")').first.click()
                    value_from_page = user_value
                    await page.wait_for_timeout(500)
                elif await container.locator('input[type="checkbox"]').count() > 0:
                    field_type = "checkbox"
                    checkbox_inputs = await container.locator('input[type="checkbox"]').all()
                    for checkbox in checkbox_inputs:
                        checkbox_label = await container.locator(f'label[for="{await checkbox.get_attribute("id")}"]').text_content()
                        if checkbox_label:
                            options.append(checkbox_label.strip())
                    user_value = arbitrary_user_data(field_type, options, label_text)
                    if user_value:
                        await container.locator('input[type="checkbox"]').first.check()
                        value_from_page = user_value
                elif await container.locator('input[data-automation-id*="date"]').count() > 0:
                    field_type = "date"
                    user_value = arbitrary_user_data(field_type, options, label_text)
                    await container.locator('input[data-automation-id*="date"]').first.fill(user_value)
                    value_from_page = user_value
                elif await container.locator('textarea').count() > 0:
                    field_type = "textarea"
                    user_value = arbitrary_user_data(field_type, options, label_text)
                    await container.locator('textarea').first.fill(user_value)
                    value_from_page = user_value
                elif await container.locator('input[type="text"]').count() > 0:
                    field_type = "text"
                    user_value = arbitrary_user_data(field_type, options, label_text)
                    await container.locator('input[type="text"]').first.fill(user_value)
                    value_from_page = user_value
                elif await container.locator('input[type="file"], button[data-automation-id*="upload"], button[data-automation-id="select-files"]').count() > 0:
                    field_type = "file"
                if field_type != "unknown" and automation_id:
                    field_data = {
                        "label": label_text,
                        "id_of_input_component": automation_id,
                        "required": is_required,
                        "type_of_input": field_type,
                        "options": options,
                        "user_data_select_values": value_from_page,
                    }
                    fields.append(field_data)
            except Exception as e:
                pass # Could not parse/fill field
        break
    return fields

# Corrected traverse_and_process to accept end_time
async def traverse_and_process(page: Page, resume_path: str, end_time: datetime): # ADD end_time here
    """
    Navigates through application pages, uploads resume, fills fields, and extracts data.
    Stops after a specified time limit or when no more 'Next' buttons are found.
    """
    all_fields_data = []
    visited_urls = set()
    
    page_count = 1
    while datetime.now() < end_time: # Check time limit
        current_url = page.url
        visited_urls.add(current_url)
        await page.wait_for_load_state("networkidle", timeout=20000)
        
        if await handle_resume_upload(page, resume_path):
            current_url = page.url
            await page.click('[data-automation-id="pageFooterNextButton"]')
            
            try:
                await page.wait_for_function(
                    "url => window.location.href !== url", arg=current_url, timeout=8000
                )
            except:
                pass # Still on the same page after clicking Next. Proceeding anyway.
            await page.wait_for_load_state("networkidle", timeout=10000)
            page_count += 1
            continue
        
        page_fields = await extract_form_fields_from_page(page)
        all_fields_data.extend(page_fields)
        
        next_button_found = False
        for selector in NEXT_BUTTON_SELECTORS:
            next_button = page.locator(selector).first
            if await next_button.is_enabled():
                await next_button.click()
                next_button_found = True
                break
        
        if not next_button_found:
            break
        try:
            await page.wait_for_function(
                "url => window.location.href !== url", arg=current_url, timeout=8000
            )
        except:
            pass # Still on the same page after clicking Next. Proceeding anyway.
        await page.wait_for_load_state("networkidle", timeout=10000)    
        page_count += 1
        await page.wait_for_load_state("networkidle", timeout=20000)
    return all_fields_data