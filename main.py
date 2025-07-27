import asyncio
import json
import os
from playwright.async_api import async_playwright
from datetime import datetime, timedelta # Import datetime and timedelta

from config import get_env_credentials
from auth import login_to_workday
from scraper import traverse_and_process # We will modify traverse_and_process to accept a time limit

async def main():
    """Main function to orchestrate the scraper."""
    os.makedirs("output", exist_ok=True)
    os.makedirs("output/videos", exist_ok=True) # Create a directory for videos
    
    email, password, tenant_url, resume_path = get_env_credentials()
    async with async_playwright() as p:
        # Configure video recording
        browser = await p.chromium.launch(headless=False) # Keep headless=False to see the recording
        context = await browser.new_context(
            record_video_dir="output/videos", # Directory to save videos
            record_video_size={"width": 1280, "height": 720} # Optional: Specify resolution
        )
        page = await context.new_page()

        # Calculate the end time for the 1-minute recording
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=0.51)
        
        try:
            await login_to_workday(page, tenant_url, email, password)
            
            # Pass the end_time to the traversal function
            all_data = await traverse_and_process(page, resume_path=resume_path, end_time=end_time)
            
            if all_data:
                output_path = "output/workday_form_map.json"
                with open(output_path, "w") as f:
                    json.dump(all_data, f, indent=2)
            
            await page.screenshot(path="output/final_page.png")
            
        except Exception as e:
            await page.screenshot(path="output/error_screenshot.png")
            raise e
        finally:
            # Close the context to ensure video is saved
            await context.close() 
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())