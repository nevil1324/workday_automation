from playwright.async_api import Page

async def login_to_workday(page: Page, tenant_url: str, email: str, password: str):
    """Navigates to the Workday tenant and logs in with provided credentials."""
    await page.goto(tenant_url)
    try:
        await page.wait_for_function(
            "url => window.location.href !== url", arg=tenant_url, timeout=8000
        )
    except:
        pass # Still on the same page after clicking Next. Proceeding anyway.
    await page.wait_for_load_state("networkidle", timeout=10000)
    try:
        await page.wait_for_selector('Button[data-automation-id="signInLink"]', timeout=5000)
        await page.click('[data-automation-id="signInLink"]')
    except:
        pass # SignInLink not present, continuing...
    await page.wait_for_selector('input[data-automation-id="email"]', timeout=1000)
    await page.type('input[data-automation-id="email"]', email, delay=50)
    await page.type('input[data-automation-id="password"]', password, delay=50)
    await page.click('div[data-automation-id="click_filter"]')
    await page.wait_for_load_state('networkidle')
    await page.wait_for_timeout(3000)