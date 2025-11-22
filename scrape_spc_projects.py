#!/usr/bin/env python3
"""
Scrape Rotary SPC projects for club 87115, Rotary year 2025-26
Extracts project details and saves to CSV
"""

import csv
import asyncio
import re
from playwright.async_api import async_playwright
from datetime import datetime
import os

# Configuration
CLUB_ID = "87115"
ROTARY_YEAR = "2025-26"
BASE_URL = "https://spc.rotary.org/projects"
OUTPUT_FILE = "spc_projects.csv"
IMAGES_DIR = "project_images"

async def scrape_projects():
    """Main scraping function"""

    # Create images directory if it doesn't exist
    os.makedirs(IMAGES_DIR, exist_ok=True)

    async with async_playwright() as p:
        # Launch browser
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)  # Set to True for headless mode
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to the projects page
        print(f"Navigating to {BASE_URL}...")
        await page.goto(BASE_URL, wait_until="networkidle")

        # Wait for page to load
        await page.wait_for_timeout(3000)

        # Click on "View all search criteria" to expand filters
        print("Expanding search criteria...")
        try:
            # Try different possible selectors for the expand button
            expand_button = await page.wait_for_selector(
                "text=/View all search criteria/i",
                timeout=10000
            )
            await expand_button.click()
            await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Could not find 'View all search criteria' button: {e}")
            print("Continuing anyway...")

        # Fill in club ID
        print(f"Setting Club ID to {CLUB_ID}...")
        try:
            # Try to find club ID input field
            club_input = await page.wait_for_selector(
                "input[placeholder*='Club' i], input[id*='clubID' i], input[name*='clubID' i]",
                timeout=5000
            )
            await club_input.fill(CLUB_ID)
            await page.wait_for_timeout(500)
        except Exception as e:
            print(f"Could not find Club ID input: {e}")

        # Set Rotary Year
        print(f"Setting Rotary Year to {ROTARY_YEAR}...")
        try:
            # Try to find rotary year dropdown or input
            year_selector = await page.wait_for_selector(
                "select[id*='year' i], input[id*='rotaryYear-2025-26' i], select[name*='year' i]",
                timeout=5000
            )
            await year_selector.select_option(label=ROTARY_YEAR)
            await page.wait_for_timeout(500)
        except Exception as e:
            print(f"Could not set Rotary Year: {e}")

        # Click search/submit button
        print("Submitting search...")
        try:
            search_button = await page.wait_for_selector(
                "button:has-text('Search'), button:has-text('Submit'), input[type='submit']",
                timeout=5000
            )
            await search_button.click()
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Could not find search button: {e}")

        # Wait for results to load
        print("Waiting for results...")
        await page.wait_for_timeout(3000)

        # Collect all projects across all pages
        all_projects = []
        page_num = 1

        while True:
            print(f"\nProcessing page {page_num}...")

            # Extract projects from current page
            projects = await extract_projects_from_page(page)
            print(f"Found {len(projects)} projects on page {page_num}")
            all_projects.extend(projects)

            # Check if there's a next page
            try:
                # Look for next page button
                next_button = await page.query_selector(
                    "a:has-text('Next'), button:has-text('Next'), a.next, button.next, "
                    "a[aria-label*='Next'], li.next:not(.disabled) a"
                )

                if next_button:
                    # Check if button is disabled
                    is_disabled = await next_button.evaluate("el => el.disabled || el.classList.contains('disabled')")

                    if not is_disabled:
                        print("Navigating to next page...")
                        await next_button.click()
                        await page.wait_for_timeout(3000)
                        page_num += 1
                    else:
                        print("Next button is disabled, no more pages.")
                        break
                else:
                    print("No next button found, assuming last page.")
                    break
            except Exception as e:
                print(f"Error checking for next page: {e}")
                break

        await browser.close()

        # Save to CSV
        print(f"\n\nSaving {len(all_projects)} projects to {OUTPUT_FILE}...")
        save_to_csv(all_projects)

        print("\nDone!")
        return all_projects


async def extract_projects_from_page(page):
    """Extract all projects from the current page"""
    projects = []

    # Try to find project links/cards
    # This will need to be adjusted based on actual page structure
    project_elements = await page.query_selector_all(
        "a[href*='/projects/'], .project-card, .project-item, [data-guid], article"
    )

    print(f"Found {len(project_elements)} potential project elements")

    for idx, element in enumerate(project_elements):
        try:
            project_data = await extract_project_data(page, element)
            if project_data:
                projects.append(project_data)
        except Exception as e:
            print(f"Error extracting project {idx}: {e}")

    return projects


async def extract_project_data(page, element):
    """Extract data for a single project"""
    project = {}

    # Extract GUID from href or data attribute
    guid = None
    try:
        href = await element.get_attribute("href")
        if href:
            # Extract GUID from URL (common patterns)
            guid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', href, re.I)
            if guid_match:
                guid = guid_match.group(1)
            project['url'] = href if href.startswith('http') else f"https://spc.rotary.org{href}"
    except:
        pass

    # Try data-guid attribute
    if not guid:
        try:
            guid = await element.get_attribute("data-guid")
        except:
            pass

    project['guid'] = guid or 'N/A'

    # Extract project name
    try:
        name_elem = await element.query_selector("h1, h2, h3, h4, .project-name, .title")
        if name_elem:
            project['name'] = (await name_elem.text_content()).strip()
        else:
            project['name'] = (await element.text_content()).strip()[:100]
    except:
        project['name'] = 'N/A'

    # Extract start date
    try:
        date_elem = await element.query_selector("[class*='date'], .start-date, time")
        if date_elem:
            project['start_date'] = (await date_elem.text_content()).strip()
        else:
            project['start_date'] = 'N/A'
    except:
        project['start_date'] = 'N/A'

    # Extract status
    try:
        status_elem = await element.query_selector("[class*='status'], .badge, .label")
        if status_elem:
            project['status'] = (await status_elem.text_content()).strip()
        else:
            project['status'] = 'N/A'
    except:
        project['status'] = 'N/A'

    # Extract amount
    try:
        amount_elem = await element.query_selector("[class*='amount'], [class*='budget'], .currency")
        if amount_elem:
            project['amount'] = (await amount_elem.text_content()).strip()
        else:
            project['amount'] = 'N/A'
    except:
        project['amount'] = 'N/A'

    # Extract domains
    try:
        domains_elem = await element.query_selector_all("[class*='domain'], [class*='category'], .tag")
        if domains_elem:
            domains = [await d.text_content() for d in domains_elem]
            project['domains'] = ', '.join([d.strip() for d in domains])
        else:
            project['domains'] = 'N/A'
    except:
        project['domains'] = 'N/A'

    # Extract summary
    try:
        summary_elem = await element.query_selector("p, .description, .summary")
        if summary_elem:
            project['summary'] = (await summary_elem.text_content()).strip()[:500]
        else:
            project['summary'] = 'N/A'
    except:
        project['summary'] = 'N/A'

    # Extract image URL
    try:
        img_elem = await element.query_selector("img")
        if img_elem:
            img_src = await img_elem.get_attribute("src")
            if img_src:
                project['image_url'] = img_src if img_src.startswith('http') else f"https://spc.rotary.org{img_src}"
            else:
                project['image_url'] = 'N/A'
        else:
            project['image_url'] = 'N/A'
    except:
        project['image_url'] = 'N/A'

    # Only return if we have meaningful data
    if project.get('name') and project['name'] != 'N/A':
        return project

    return None


def save_to_csv(projects):
    """Save projects to CSV file"""
    if not projects:
        print("No projects to save!")
        return

    fieldnames = ['guid', 'name', 'start_date', 'status', 'amount', 'domains', 'url', 'summary', 'image_url']

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for project in projects:
            # Ensure all fields exist
            row = {field: project.get(field, 'N/A') for field in fieldnames}
            writer.writerow(row)

    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(scrape_projects())
