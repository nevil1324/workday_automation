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



from typing import Tuple, List, Dict
from playwright.async_api import Page, Locator


async def extract_all_multiselect_options(popup: Locator, page: Page) -> List[str]:
    """Scrolls through a virtualized dropdown and extracts all available options."""
    seen = set()
    scroll_attempts = 0

    while True:
        options = await popup.locator('[role="option"]').all_text_contents()
        new_options = [opt.strip() for opt in options if opt.strip() and opt.strip() not in seen]

        if not new_options:
            scroll_attempts += 1
        else:
            scroll_attempts = 0

        seen.update(new_options)

        if scroll_attempts >= 5:
            break

        count = await popup.locator('[role="option"]').count()
        if count == 0:
            break

        last_option = popup.locator('[role="option"]').nth(count - 1)
        try:
            await last_option.scroll_into_view_if_needed()
            await page.wait_for_timeout(200)
        except:
            break

    return sorted(seen)

async def scroll_to_option(popup: Locator, target_option: str, page: Page, max_scrolls: int = 30) -> Optional[Locator]:
    """Scrolls through a virtualized multiselect until the desired option is visible and returns its locator."""
    for _ in range(max_scrolls):
        try:
            locator = popup.locator(f'[data-automation-id="promptOption"]:has-text("{target_option}")').first
            if await locator.is_visible():
                return locator
        except:
            pass

        # Scroll down by scrolling to the last visible item
        count = await popup.locator('[data-automation-id="promptOption"]').count()
        if count == 0:
            return None

        last = popup.locator('[data-automation-id="promptOption"]').nth(count - 1)
        try:
            await last.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)
        except:
            return None

    return None


async def handle_multiselect(container: Locator, label_text: str, page: Page) -> Tuple[str, List[str], List[str], Dict[str, List[str]]]:
    """Extracts all top-level and nested multiselect options with mapping."""
    field_type = "multiselect"
    await close_all_popups(page)

    input_field = container.locator('input').first
    try:
        await input_field.click(force=True)
    except:
        await input_field.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        await input_field.click(force=True)

    await page.wait_for_timeout(800)
    popup = await wait_for_popup(page)

    if not popup:
        print("⚠️ No popup appeared after clicking")
        return field_type, [], [], {}

    selected_values = []
    nested_options_dict = {}


    if "Phone Code" in label_text:
        preferred_option = "India (+91)"
        
        # Trigger all options to render
        await input_field.fill("")
        await page.wait_for_timeout(1000)

        # Extract all phone code options
        top_level_options = await extract_all_multiselect_options(popup, page)
        print("Phone code options found:", top_level_options)

        # Try selecting preferred option
        if preferred_option in top_level_options:
            await input_field.fill("India")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(1000)
            option = popup.locator(f'[role="option"]:has-text("{preferred_option}")').first
            try:
                await option.click()
                selected_values.append(preferred_option)
            except Exception as e:
                print(f"⚠️ Failed to click preferred option '{preferred_option}': {e}")
        else:
            print(f"⚠️ Preferred option '{preferred_option}' not in list")

        return field_type, [nested_options_dict], selected_values


    # Step 1: Extract all top-level options
    top_level_options = await extract_all_multiselect_options(popup, page)

    print("Top-level options found:", top_level_options)
    selected_values = ["", ""]
    idx = 0

    # Step 2: Loop through each top-level option text (not locator)
    for top_opt in top_level_options:
        # Reopen dropdown every time
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

        try:
            await input_field.click(force=True)
            await page.wait_for_timeout(600)
        except:
            print(f"⚠️ Couldn't reopen multiselect for option '{top_opt}'")
            continue

        popup = await wait_for_popup(page)
        if not popup:
            print("⚠️ Popup not found on reopen.")
            continue

        # Now get the option element for the current visible popup
        option_locator = await scroll_to_option(popup, top_opt, page)
        if option_locator:
            try:
                await option_locator.click()
                selected_values[idx] = top_opt
            except Exception as e:
                print(f"⚠️ Failed to click option '{top_opt}': {e}")
        else:
            print(f"⚠️ Option '{top_opt}' not found after scrolling")


        # Handle nested popup
        # selected_values.append(top_opt)
        idx += 1
        nested_popup = await wait_for_popup(page, timeout=1500)
        if nested_popup:
            try:
                nested_opts = await extract_all_multiselect_options(nested_popup, page)
                if nested_opts:
                    nested_options_dict[top_opt] = nested_opts

                # Optionally click first nested option
                try:
                    first_nested = nested_popup.locator('[role="option"]').first
                    await first_nested.click()
                    selected_values[idx] = nested_opts[0]
                except:
                    pass
            except Exception as e:
                print(f"⚠️ Failed extracting nested options for '{top_opt}': {e}")

        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

        if not nested_popup:
            break
        idx = 0

    await page.keyboard.press("Escape")
    return field_type, [nested_options_dict], selected_values

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