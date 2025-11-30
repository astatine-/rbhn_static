#!/usr/bin/env python3
"""
Extract project data from HTML files and create a CSV export.
"""

import re
import csv
from pathlib import Path
from html.parser import HTMLParser

class ProjectHTMLParser(HTMLParser):
    """Parse HTML to extract project information."""

    def __init__(self):
        super().__init__()
        self.projects = []
        self.current_project = None
        self.current_tag_stack = []
        self.current_data = ''
        self.in_project_card = False
        self.current_label = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.current_tag_stack.append((tag, attrs_dict))

        # Check if we're entering a project section or image div
        # Note: image div appears BEFORE the section tag
        if 'id' in attrs_dict:
            if attrs_dict['id'].startswith('image-projectSnapshotDiv-'):
                guid = attrs_dict['id'].replace('image-projectSnapshotDiv-', '')
                # Pre-create or update project entry for this GUID
                if not self.current_project or self.current_project.get('guid') != guid:
                    self.current_project = {
                        'guid': guid,
                        'url': f'https://spc.rotary.org/project?guid={guid}',
                        'title': '',
                        'description': '',
                        'status': '',
                        'start_date': '',
                        'end_date': '',
                        'image': ''
                    }
                    self.in_project_card = True

            elif attrs_dict['id'].startswith('projectSnapshotDiv-'):
                guid = attrs_dict['id'].replace('projectSnapshotDiv-', '')
                # If we already have a project with this GUID (from image div), keep it
                if not self.current_project or self.current_project.get('guid') != guid:
                    self.current_project = {
                        'guid': guid,
                        'url': f'https://spc.rotary.org/project?guid={guid}',
                        'title': '',
                        'description': '',
                        'status': '',
                        'start_date': '',
                        'end_date': '',
                        'image': ''
                    }
                self.in_project_card = True

        # Extract image src
        if tag == 'img' and 'src' in attrs_dict and self.in_project_card:
            if self.current_project and not self.current_project['image']:
                # Check if this is a project image
                classes = attrs_dict.get('class', '')
                if 'imageStyleImg' in classes:
                    self.current_project['image'] = attrs_dict['src']

        # Check for title heading
        if tag == 'h5' and self.in_project_card:
            classes = attrs_dict.get('class', '')
            if 'rotaryui-card__title' in classes:
                self.current_data = ''

        # Check for description
        if tag == 'article' and self.in_project_card:
            classes = attrs_dict.get('class', '')
            if 'rotaryui-card__body' in classes:
                self.current_data = ''

        # Check for labels (Start date, End date, etc.)
        if tag == 'div' and self.in_project_card:
            classes = attrs_dict.get('class', '')
            if 'rotaryui-card__label' in classes:
                self.current_data = ''
                self.current_label = None
            elif 'rotaryui-card__vlaue' in classes:  # Note: typo in original HTML
                self.current_data = ''

    def handle_endtag(self, tag):
        if self.current_tag_stack:
            last_tag, attrs = self.current_tag_stack.pop()

            # Process title
            if tag == 'h5' and 'class' in attrs and 'rotaryui-card__title' in attrs.get('class', ''):
                if self.current_project:
                    self.current_project['title'] = self.current_data.strip()
                    self.current_data = ''

            # Process description
            if tag == 'article' and 'class' in attrs and 'rotaryui-card__body' in attrs.get('class', ''):
                if self.current_project:
                    self.current_project['description'] = self.current_data.strip()
                    self.current_data = ''

            # Process label
            if tag == 'div' and 'class' in attrs and 'rotaryui-card__label' in attrs.get('class', ''):
                self.current_label = self.current_data.strip().lower().replace(':', '')
                self.current_data = ''

            # Process value
            if tag == 'div' and 'class' in attrs and 'rotaryui-card__vlaue' in attrs.get('class', ''):
                value = self.current_data.strip()
                if self.current_project and self.current_label:
                    if 'start date' in self.current_label:
                        self.current_project['start_date'] = value
                    elif 'end date' in self.current_label:
                        self.current_project['end_date'] = value
                self.current_data = ''
                self.current_label = None

            # End of project section
            if tag == 'section' and 'id' in attrs and attrs['id'].startswith('projectSnapshotDiv-'):
                if self.current_project:
                    self.projects.append(self.current_project)
                    self.current_project = None
                    self.in_project_card = False

    def handle_data(self, data):
        data = data.strip()
        if data:
            # Check for status badges
            if data in ['In Progress', 'Completed', 'Active', 'Ongoing']:
                if self.current_project and not self.current_project['status']:
                    self.current_project['status'] = data

            # Accumulate data for current element
            if self.current_data:
                self.current_data += ' '
            self.current_data += data

def extract_projects_from_html(html_file):
    """Extract project data from an HTML file."""
    print(f"Processing {html_file}...")

    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    parser = ProjectHTMLParser()
    parser.feed(content)

    print(f"  Found {len(parser.projects)} projects")
    return parser.projects

def main():
    # Get all HTML files
    html_files = list(Path('.').glob('Service Project Center-nov25-pg*.html'))

    all_projects = []

    for html_file in sorted(html_files):
        projects = extract_projects_from_html(html_file)
        all_projects.extend(projects)

    print(f"\nTotal projects extracted: {len(all_projects)}")

    # Write to CSV
    if all_projects:
        csv_file = 'rotary_projects.csv'
        fieldnames = ['start_date', 'title', 'description', 'status', 'url', 'image']

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()

            for project in all_projects:
                row = {
                    'start_date': project.get('start_date', ''),
                    'title': project.get('title', ''),
                    'description': project.get('description', ''),
                    'status': project.get('status', ''),
                    'url': project.get('url', ''),
                    'image': project.get('image', '')
                }
                writer.writerow(row)

        print(f"\nData exported to {csv_file}")
        print(f"Fields: {', '.join(fieldnames)}")
    else:
        print("No projects found!")

if __name__ == '__main__':
    main()
