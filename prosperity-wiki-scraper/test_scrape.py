import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://imc-prosperity.notion.site/what-is-prosperity?pvs=25", wait_until="networkidle")
        await page.wait_for_timeout(10000)
        await page.screenshot(path="notion_test.png")
        print(await page.content())
        await browser.close()

asyncio.run(main())
