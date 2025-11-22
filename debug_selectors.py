#!/usr/bin/env python3
"""
Debug script to identify correct selectors on SPC page
"""

import asyncio
from playwright.async_api import async_playwright

BASE_URL = "https://spc.rotary.org/projects"

async def debug_page():
    """Debug function to identify selectors"""

    async with async_playwright() as p:
        # Launch browser
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to the projects page
        print(f"Navigating to {BASE_URL}...")
        await page.goto(BASE_URL, wait_until="networkidle")

        # Wait for page to load
        await page.wait_for_timeout(5000)

        # Take initial screenshot
        await page.screenshot(path="screenshot_initial.png", full_page=True)
        print("Screenshot saved: screenshot_initial.png")

        # Find all buttons with text containing "view" or "criteria"
        print("\n=== Looking for 'View all search criteria' button ===")
        buttons = await page.query_selector_all("button, a, div[role='button'], span[class*='link']")
        for i, btn in enumerate(buttons):
            text = await btn.text_content()
            if text and ('view' in text.lower() or 'criteria' in text.lower() or 'search' in text.lower()):
                print(f"Button {i}: {text.strip()}")
                # Print the button's selector
                tag = await btn.evaluate("el => el.tagName")
                class_name = await btn.get_attribute("class")
                id_attr = await btn.get_attribute("id")
                print(f"  Tag: {tag}, Class: {class_name}, ID: {id_attr}")

        # Find all input fields
        print("\n=== Looking for input fields ===")
        inputs = await page.query_selector_all("input, select, textarea")
        for i, inp in enumerate(inputs):
            tag = await inp.evaluate("el => el.tagName")
            input_type = await inp.get_attribute("type")
            placeholder = await inp.get_attribute("placeholder")
            name = await inp.get_attribute("name")
            id_attr = await inp.get_attribute("id")
            class_name = await inp.get_attribute("class")
            print(f"Input {i}: Tag={tag}, Type={input_type}, Placeholder={placeholder}")
            print(f"  Name={name}, ID={id_attr}, Class={class_name}")

        # Print page title
        title = await page.title()
        print(f"\n=== Page Title: {title} ===")

        # Keep browser open for manual inspection
        print("\n=== Browser will stay open for 60 seconds for manual inspection ===")
        print("Please inspect the page and note down the correct selectors.")
        await page.wait_for_timeout(60000)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page())
