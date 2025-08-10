# form_processor.py
from typing import Dict, List, Any, Set
from playwright.async_api import Page, ElementHandle
from config import NEXT_BUTTON_SELECTORS
from field_handlers import handle_resume_upload, handle_multiselect, handle_dropdown
from utils import arbitrary_user_data, get_text_input_value, close_all_popups

async def handle_add_buttons(page: Page, fields: List[Dict[str, Any]], processed_handles: Set[str]) -> List[Dict[str, Any]]:
    """
    Click all *original* Add buttons (snapshot as element handles) to expand
    sections and extract any newly added fields.
    """
    # Snapshot element handles of the original add buttons to avoid index detachment.
    original_button_handles: List[ElementHandle] = await page.query_selector_all('button[data-automation-id="add-button"]')
    print(f"Found {len(original_button_handles)} 'Add' buttons on the page.")
    all_fields: List[Dict[str, Any]] = []

    for idx, handle in enumerate(original_button_handles):
        try:
            # Get visible text (safe guard if text_content is None)
            btn_text = (await handle.text_content() or "").strip().lower()
            if "add another" in btn_text:
                print(f"⏩ Skipping 'Add Another' button at index {idx}")
                continue

            # Get the section label by reading aria-labelledby from the closest group
            aria_labelledby = await handle.evaluate("el => el.closest('div[role=\"group\"]')?.getAttribute('aria-labelledby')")
            main_label = ""
            if aria_labelledby:
                # try to read the element with that id
                label_elem = page.locator(f'#{aria_labelledby}')
                if await label_elem.count() > 0:
                    main_label = (await label_elem.first.text_content() or "").strip()

            print(f"\n🔹 Handling 'Add' button for section: {main_label or '[unknown section]'} (index {idx})")

            # click the original element handle
            await handle.click()
            # small wait to allow new DOM pieces to appear (adjustable)
            await page.wait_for_timeout(750)

            # Extract fields added by clicking this Add button. We pass flag=False to avoid recursion here.
            section_fields = await extract_form_fields_from_page(page, processed_handles, flag=False)

            # Tag each found field with the Add-button section label
            for field in section_fields:
                field["Add Button"] = main_label
            all_fields.extend(section_fields)

        except Exception as e:
            print(f"⚠️ Error handling 'Add' button at index {idx}: {e}")

    return all_fields


async def extract_form_fields_from_page(page: Page, processed_handles: Set[str], flag: bool) -> List[Dict[str, Any]]:
    """
    Extract all form fields currently on the page that haven't been processed,
    try to fill them (where appropriate), and return structured metadata.
    """
    fields: List[Dict[str, Any]] = []

    while True:
        print("\n---------------\n")

        field_containers = await page.locator('[data-automation-id^="formField-"]').all()
        new_containers: List[tuple[str, Any]] = []

        for container in field_containers:
            automation_id = await container.get_attribute("data-automation-id") or ""
            if automation_id and automation_id not in processed_handles:
                processed_handles.add(automation_id)
                new_containers.append((automation_id, container))

        if not new_containers:
            break

        print("pending containers:", len(new_containers))
        for automation_id, _ in new_containers:
            print(f"Processing container with automation ID: {automation_id}")

        for automation_id, container in new_containers:
            try:
                file_input = container.locator('input[data-automation-id="file-upload-input-ref"]')
                if await file_input.count() > 0:
                    print("Found file upload input in container")
                    field_type = "file"
                    
                    label_text = ""

                    # 1) Check aria-labelledby in parent role=group or file upload container
                    aria_elem = container.locator("xpath=ancestor-or-self::*[@aria-labelledby][1]")
                    if await aria_elem.count() > 0:
                        aria_id = await aria_elem.first.get_attribute("aria-labelledby")
                        if aria_id:
                            # ✅ Use XPath to avoid CSS escaping issues with `/` and other characters
                            linked_elem = page.locator(f"xpath=//*[@id='{aria_id}']")
                            if await linked_elem.count() > 0:
                                label_text = (await linked_elem.first.text_content() or "").strip()

                    # 2) If still empty, nearest preceding heading
                    if not label_text:
                        heading = container.locator(
                            "xpath=preceding::*[self::h1 or self::h2 or self::h3][1]"
                        )
                        if await heading.count() > 0:
                            label_text = (await heading.first.text_content() or "").strip()

                    # 3) If still empty, try <label> in container
                    if not label_text:
                        label_loc = container.locator("label")
                        if await label_loc.count() > 0:
                            label_text = (await label_loc.first.text_content() or "").strip()

                    # 4) Fallback
                    if not label_text:
                        label_text = "File upload"

                    # Get component id from button or parent formField
                    comp_id = await container.get_attribute("data-fkit-id") \
                        or await container.get_attribute("id")
                    if not comp_id:
                        select_button = container.locator("button[data-automation-id='select-files']")
                        if await select_button.count() > 0:
                            comp_id = await select_button.first.get_attribute("id")
                    
                    try:
                        await file_input.first.set_input_files("dummy_file.pdf")
                        value_from_page = "dummy_file.pdf"
                    except Exception as e:
                        print(f"⚠️ File upload failed: {e}")
                        value_from_page = ""

                    field_data = {
                        "label": label_text or "File upload",
                        "id_of_input_component": comp_id or "",
                        "required": False,
                        "type_of_input": field_type,
                        "options": [],
                        "user_data_select_values": value_from_page,
                    }
                    print("  -> Filled and extracted file upload field:", field_data)
                    fields.append(field_data)
                    continue



                # Re-query container first element to be safe
                container = page.locator(f'[data-automation-id="{automation_id}"]').first

                # Label extraction
                label_text = ""
                legend_loc = container.locator("legend")
                if await legend_loc.count() > 0:
                    # 1) legend > richText > p
                    richtext_p = legend_loc.locator('[data-automation-id="richText"] p')
                    if await richtext_p.count() > 0:
                        label_text = (await richtext_p.first.text_content()) or ""
                    else:
                        # 2) legend > span
                        span = legend_loc.locator("span")
                        if await span.count() > 0:
                            label_text = (await span.first.text_content()) or ""
                        else:
                            # 3) legend > label
                            label_in_legend = legend_loc.locator("label")
                            if await label_in_legend.count() > 0:
                                label_text = (await label_in_legend.first.text_content()) or ""
                else:
                    # direct <label> inside the container
                    label_loc = container.locator("label")
                    if await label_loc.count() > 0:
                        label_text = (await label_loc.first.text_content()) or ""

                # fallback: aria-labelledby
                if not label_text:
                    input_with_label = container.locator('[aria-labelledby]')
                    if await input_with_label.count() > 0:
                        label_id = await input_with_label.first.get_attribute("aria-labelledby")
                        if label_id and not label_id.startswith("hiddenDateValueId"):
                            label_elem = page.locator(f'#{label_id}')
                            if await label_elem.count() > 0:
                                label_text = (await label_elem.first.text_content()) or ""

                # cleanup
                is_required = "*" in (label_text or "")
                label_text = (label_text or "").replace("*", "").strip()

                if not label_text:
                    # skip unlabeled containers
                    continue

                field_type = "unknown"
                options: List[str] = []
                value_from_page = ""

                # detect multi-select
                multiselect_container = container.locator('[data-automation-id="multiSelectContainer"]')
                dropdown_button = container.locator('button[aria-haspopup="listbox"]')

                if await multiselect_container.count() > 0:
                    print("inside multi-select")
                    field_type, options, value_from_page = await handle_multiselect(container, label_text, page)
                    await close_all_popups(page)

                elif await dropdown_button.count() > 0:
                    print("inside dropdown")
                    field_type, options, value_from_page = await handle_dropdown(container, label_text, page, automation_id)
                    await close_all_popups(page)

                # radio inputs
                elif await container.locator('input[type="radio"]').count() > 0:
                    print("inside radio")
                    field_type = "radio"
                    radio_inputs = await container.locator('input[type="radio"]').all()
                    for radio in radio_inputs:
                        radio_id = await radio.get_attribute("id")
                        if radio_id:
                            lbl = container.locator(f'label[for="{radio_id}"]')
                            if await lbl.count() > 0:
                                radio_label = (await lbl.first.text_content()) or ""
                                if radio_label:
                                    options.append(radio_label.strip())
                    user_value = arbitrary_user_data(field_type, options, label_text)
                    if user_value:
                        # click label with this text, fallback to clicking the input if label not found
                        label_click_loc = container.locator(f'label:has-text("{user_value}")')
                        if await label_click_loc.count() > 0:
                            await label_click_loc.first.click()
                        else:
                            # fallback: click first radio input that matches the option index
                            radios = container.locator('input[type="radio"]')
                            if await radios.count() > 0:
                                await radios.first.check()
                        value_from_page = user_value
                        await page.wait_for_timeout(300)

                # checkbox inputs
                elif await container.locator('input[type="checkbox"]').count() > 0:
                    print("inside checkbox")
                    field_type = "checkbox"
                    options = []  # reset per field
                    
                    checkbox_inputs = await container.locator('input[type="checkbox"]').all()
                    for checkbox in checkbox_inputs:
                        c_id = await checkbox.get_attribute("id")
                        checkbox_label = ""
                        if c_id:
                            lbl = container.locator(f'label[for="{c_id}"]')
                            if await lbl.count() > 0:
                                checkbox_label = (await lbl.first.text_content()) or ""
                        
                        # Fallback: label wrapping the checkbox
                        if not checkbox_label:
                            parent_label = checkbox.locator("xpath=ancestor::label[1]")
                            if await parent_label.count() > 0:
                                checkbox_label = (await parent_label.first.text_content()) or ""

                        if checkbox_label.strip():
                            options.append(checkbox_label.strip())
                    
                    user_value = arbitrary_user_data(field_type, options, label_text)
                    if user_value:
                        # Try to match by label
                        matched_checkbox = container.locator(
                            f'xpath=.//label[contains(normalize-space(.), "{user_value}")]/input[@type="checkbox"]'
                        )
                        if await matched_checkbox.count() > 0:
                            await matched_checkbox.first.check()
                        else:
                            await container.locator('input[type="checkbox"]').first.check()
                        
                        value_from_page = user_value


                # date fields (MM/DD/YYYY or MM/YYYY)
                elif await container.locator('input[data-automation-id*="date"]').count() > 0:
                    print("inside date")
                    month_input = container.locator('input[data-automation-id="dateSectionMonth-input"]')
                    day_input = container.locator('input[data-automation-id="dateSectionDay-input"]')
                    year_input = container.locator('input[data-automation-id="dateSectionYear-input"]')

                    try:
                        if await day_input.count() > 0:
                            field_type = "date-mmddyyyy"
                            user_value = arbitrary_user_data(field_type, options, label_text)
                            mm, dd, yyyy = user_value.split('/')
                            if is_required:
                                await month_input.fill(mm)
                                await day_input.fill(dd)
                                await year_input.fill(yyyy)
                            value_from_page = f"{mm}/{dd}/{yyyy}"
                        else:
                            field_type = "date-mmyyyy"
                            user_value = arbitrary_user_data(field_type, options, label_text)
                            mm, yyyy = user_value.split('/')
                            if is_required:
                                await month_input.fill(mm)
                                await year_input.fill(yyyy)
                            value_from_page = f"{mm}/{yyyy}"
                    except Exception as e:
                        print(f"⚠️ Could not parse/fill date field. Error: {e}")

                # textarea
                elif await container.locator('textarea').count() > 0:
                    print("inside textarea")
                    field_type = "textarea"
                    user_value = arbitrary_user_data(field_type, options, label_text)
                    await container.locator('textarea').first.fill(user_value)
                    value_from_page = user_value

                # text input (not readonly)
                elif await container.locator('input[type="text"], input[type="number"]').count() > 0:
                    print("inside text/number")
                    input_loc = container.locator('input[type="text"], input[type="number"]').first
                    input_id = await input_loc.get_attribute("id") or ""
                    input_type_attr = (await input_loc.get_attribute("type") or "").lower()
                    input_mode_attr = (await input_loc.get_attribute("inputmode") or "").lower()
                    pattern_attr = await input_loc.get_attribute("pattern") or ""
                    
                    # detect readonly/disabled outputs
                    readonly_attr = await input_loc.get_attribute("readonly")
                    disabled_attr = await input_loc.get_attribute("disabled")
                    if readonly_attr is not None or disabled_attr is not None:
                        field_type = "output-text"
                        try:
                            value_from_page = await input_loc.input_value()
                        except Exception:
                            value_from_page = ""
                    else:
                        # Check if this is numeric input
                        numeric_labels = ["salary", "compensation", "amount", "number", "age", "years", "experience", "zip", "postal"]
                        is_numeric = (
                            input_type_attr == "number"
                            or input_mode_attr == "numeric"
                            or pattern_attr.isdigit()
                            or any(word in label_text.lower() for word in numeric_labels)
                        )

                        if is_numeric:
                            field_type = "number"
                            user_value = "100000"  # Example default salary
                        else:
                            field_type = "text"
                            user_value = get_text_input_value(label_text, input_id)

                        value_from_page = user_value
                        if is_required or user_value:
                            await input_loc.fill(user_value)


                # other input types you may want to support (number, email etc.)
                elif await container.locator('input[type="number"]').count() > 0:
                    field_type = "number"
                    input_loc = container.locator('input[type="number"]').first
                    is_readonly = await input_loc.get_attribute("readonly") is not None
                    if is_readonly:
                        value_from_page = await input_loc.input_value()
                    else:
                        user_value = arbitrary_user_data("number", [], label_text)
                        value_from_page = user_value
                        await input_loc.fill(str(user_value))

                # if we identified a non-unknown field, append
                if field_type != "unknown" and automation_id:
                    field_data = {
                        "label": label_text,
                        "id_of_input_component": automation_id,
                        "required": bool(is_required),
                        "type_of_input": field_type,
                        "options": options,
                        "user_data_select_values": value_from_page,
                    }
                    fields.append(field_data)
                    print(f"  -> Filled and extracted: '{label_text}' (Type: {field_type})")

            except Exception as e:
                print(f"⚠️ Could not parse/fill field {automation_id}. Error: {e}")

    # If flag True, also click any Add buttons that add more fields (to capture them)
    if flag:
        more_fields = await handle_add_buttons(page, fields, processed_handles)
        if more_fields:
            fields.extend(more_fields)

    return fields


async def traverse_and_process(page: Page, resume_path: str):
    """
    Navigates through application pages, uploads resume (if needed), fills fields, and extracts data.
    """
    all_fields_data: List[Dict[str, Any]] = []
    visited_urls = set()

    print("\n--- Starting Application Traversal ---")

    try:
        # safe attempt to count pages in a progress list; fallback on exception
        progress_list = page.get_by_label("Application Progress")
        number_of_pages = await progress_list.get_by_role("listitem").count()
        print(f"🔢 Total Pages in Application: {number_of_pages}")
    except Exception as e:
        print(f"⚠️ Could not determine number of pages: {e}")
        number_of_pages = 3  # fallback

    for page_count in range(1, max(2, number_of_pages + 1)):
        current_url = page.url
        visited_urls.add(current_url)

        try:
            heading = page.locator("h2").first
            await heading.wait_for(timeout=10000)
            page_name = (await heading.inner_text()) or f"Page {page_count}"
            print(f"✅ Page Title: {page_name}")
        except Exception as e:
            print(f"⚠️ Failed to extract page name: {e}")
            page_name = f"Page {page_count}"

        processed_handles: Set[str] = set()

        page_fields = await extract_form_fields_from_page(page, processed_handles, flag=False)
        for field in page_fields:
            field["page_name"] = page_name
            print(f"Page: {page_name} | Field: {field['label']} | Required: {field['required']} | Type: {field['type_of_input']} | Value: {field.get('user_data_select_values')}")

        all_fields_data.extend(page_fields)

        # find and click an enabled Next button
        next_button_found = False
        for selector in NEXT_BUTTON_SELECTORS:
            next_button = page.locator(selector)
            if await next_button.count() == 0:
                continue
            # use first matching instance
            btn = next_button.first
            try:
                if await btn.is_enabled():
                    print(f"\n➡️ Found and clicking 'Next' button with selector: {selector}")
                    await btn.click()
                    next_button_found = True
                    break
            except Exception as e:
                print(f"⚠️ Error checking/clicking next button: {e}")
                continue

        if not next_button_found:
            print("\n--- No enabled 'Next' button found. Traversal finished. ---")
            break

        # wait for URL change or network idle
        try:
            await page.wait_for_function("url => window.location.href !== url", arg=current_url, timeout=10000)
            print("✅ Successfully navigated to the next page")
        except Exception:   
            # print("⚠️ Still on the same page after clicking Next. Proceeding anyway.")
            pass

        # ensure network idle to allow dynamic content
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            # ignore load-state timeout but continue
            pass

    return all_fields_data
