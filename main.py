# main.py
import asyncio
import json
import os
from typing import Dict, List, Any
from playwright.async_api import async_playwright
from utils import get_env_credentials
from login import login_to_workday
from form_processor import traverse_and_process

async def main():
    """Main function to orchestrate the scraper."""
    os.makedirs("output", exist_ok=True)
    email, password, tenant_url, resume_path = get_env_credentials()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            record_video_dir="output/video",
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        try:
            await login_to_workday(page, tenant_url, email, password)

            try:
                await page.wait_for_function(
                    "url => window.location.href !== url", arg=tenant_url, timeout=8000
                )
                print("✅ Successfully navigated to the next page after resume upload.")
            except:
                print("⚠️ Still on the same page after clicking Next. Proceeding anyway.")
            
            print("\nStarting data extraction and filling process...")
            all_data = await traverse_and_process(page, resume_path=resume_path)
            
            if all_data:
                output_path = "output/workday_form_map.json"
                print(f"\n✅ Process complete. Writing {len(all_data)} fields to {output_path}")
                with open(output_path, "w") as f:
                    json.dump(all_data, f, indent=2)
            else:
                print("\n⚠️ No data was extracted.")
            
            await page.screenshot(path="output/final_page.png")

        except Exception as e:
            print(f"\n❌ An unexpected error occurred: {e}")
            await page.screenshot(path="output/error_screenshot.png")
            print("A screenshot of the error page has been saved to 'output/error_screenshot.png'.")
        finally:
            print("Closing browser.")
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())