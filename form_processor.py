# form_processor.py
from typing import Dict, List, Any, Optional
from playwright.async_api import Page, Locator
from config import NEXT_BUTTON_SELECTORS
from field_handlers import handle_resume_upload, handle_multiselect, handle_dropdown
from utils import arbitrary_user_data, get_text_input_value, close_all_popups

async def extract_form_fields_from_page(page: Page) -> List[Dict[str, Any]]:
    fields = []
    processed_handles: set[str] = set()

    while True:
        print("\n---------------\n")
        should_restart = False

        field_containers = await page.locator('[data-automation-id^="formField-"]').all()
        new_containers = []

        for container in field_containers:
            automation_id = await container.get_attribute("data-automation-id")
            if automation_id and automation_id not in processed_handles:
                processed_handles.add(automation_id)
                new_containers.append((automation_id, container))

        if not new_containers:
            break

        print("pending containers:", len(new_containers))
        for automation_id, container in new_containers:
            print(f"Processing container with automation ID: {automation_id}")

        for automation_id, container in new_containers:
            try:
                if automation_id == "formField-":
                    field_type = "file"
                    file_input = container.locator('input[type="file"]')
                    if await file_input.count() > 0:
                        await file_input.set_input_files("dummy_file.pdf")
                        value_from_page = "dummy_file.pdf"
                    
                    field_data = {
                        "label": "File upload",
                        "id_of_input_component": automation_id,
                        "required": "False",
                        "type_of_input": field_type,
                        "options": "",
                        "user_data_select_values": value_from_page,
                    }
                    fields.append(field_data)
                    continue
            
                container = page.locator(f'[data-automation-id="{automation_id}"]').first
                legend_loc = container.locator("legend").first
                label_loc = container.locator("label")
                label_text = ""

                if await legend_loc.count() > 0:
                    richtext_p = legend_loc.locator('[data-automation-id="richText"] p')
                    if await richtext_p.count() > 0:
                        label_text = await richtext_p.first.text_content() or ""
                    else:
                        span = legend_loc.locator("span")
                        if await span.count() > 0:
                            label_text = await span.first.text_content() or ""
                elif await label_loc.count() > 0:
                    label_text = await label_loc.first.text_content() or ""

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

                if await multiselect_container.count() > 0:
                    container = page.locator(f'[data-automation-id="{automation_id}"]').first
                    print("inside multi-select")
                    field_type, options, value_from_page = await handle_multiselect(container, label_text, page)

                elif await dropdown_button.count() > 0:
                    print("inside dropdown")
                    print("label_text:", label_text)
                    field_type, options, value_from_page = await handle_dropdown(container, label_text, page, automation_id)

                elif await container.locator('input[type="radio"]').count() > 0:
                    print("inside radio")
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
                    should_restart = True

                elif await container.locator('input[type="checkbox"]').count() > 0:
                    print("inside checkbox")
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
                    print("inside date")
                    field_type = "date"
                    user_value = arbitrary_user_data(field_type, options, label_text)
                    await container.locator('input[data-automation-id*="date"]').first.fill(user_value)
                    value_from_page = user_value

                elif await container.locator('textarea').count() > 0:
                    print("inside textarea")
                    field_type = "textarea"
                    user_value = arbitrary_user_data(field_type, options, label_text)
                    await container.locator('textarea').first.fill(user_value)
                    value_from_page = user_value

                elif await container.locator('input[type="text"]').count() > 0:
                    print("inside text")
                    field_type = "text"
                    input_id = await container.locator('input[type="text"]').first.get_attribute("id")
                    user_value = get_text_input_value(label_text, input_id or "")
                    await container.locator('input[type="text"]').first.fill(user_value)
                    value_from_page = user_value

                elif automation_id == "formField-":
                    print("inside file")
                    field_type = "file"
                    file_input = container.locator('input[type="file"]')
                    if await file_input.count() > 0:
                        await file_input.set_input_files("dummy_file.pdf")
                        value_from_page = "dummy_file.pdf"

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
                    print(f"  -> Filled and extracted: '{label_text}' (Type: {field_type})")

            except Exception as e:
                print(f"⚠️ Could not parse/fill field. Error: {e}")

        if should_restart:
            continue

    return fields

async def traverse_and_process(page: Page, resume_path: str):
    """
    Navigates through application pages, uploads resume, fills fields, and extracts data.
    """
    all_fields_data = []
    visited_urls = set()
    
    print("\n--- Starting Application Traversal ---")
  
    page_count = 1
    while True:
        if page_count == 6:
            break
        current_url = page.url
        visited_urls.add(current_url)

        print(f"\n--- Processing Page {page_count}: {await page.title()} ---")
        await page.wait_for_load_state("networkidle", timeout=2000)

        page_fields = await extract_form_fields_from_page(page)
        for field in page_fields:
            print(f"Field: {field['label']} | Required: {field['required']} | Type: {field['type_of_input']} | Value: {field.get('user_data_select_values')}")
        all_fields_data.extend(page_fields)
        
        next_button_found = False
        for selector in NEXT_BUTTON_SELECTORS:
            next_button = page.locator(selector).first
            if await next_button.is_enabled():
                print(f"\nFound and clicking 'Next' button with selector: {selector}")
                await next_button.click()
                next_button_found = True
                break
        
        if not next_button_found:
            print("\n--- No enabled 'Next' button found. Traversal finished. ---")
            break
        try:
            await page.wait_for_function(
                "url => window.location.href !== url", arg=current_url, timeout=8000
            )
            print("✅ Successfully navigated to the next page")
        except:
            print("⚠️ Still on the same page after clicking Next. Proceeding anyway.")

        await page.wait_for_load_state("networkidle", timeout=10000)    
        page_count += 1
        await page.wait_for_load_state("networkidle", timeout=20000)
    return all_fields_data