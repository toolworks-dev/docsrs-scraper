import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
import time
import argparse

class DocsRsScraper:
    def __init__(self, base_url, progress_callback=None):
        self.base_url = base_url
        self.visited_urls = set()
        self.content = []
        self.progress_callback = progress_callback or (lambda x: None)
        
    def fetch_page(self, url):
        try:
            time.sleep(0.1)
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            self.progress_callback(f"Error fetching {url}: {e}")
            return None

    def parse_content(self, html, url):
        if not html or url in self.visited_urls:
            return
        
        self.progress_callback(f"Parsing content from: {url}")
        
        self.visited_urls.add(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        main_content = (
            soup.find('div', {'id': 'main-content'}) or 
            soup.find('div', class_='rustdoc') or
            soup.find('div', class_='rustdoc mod crate')
        )
        
        if not main_content:
            self.progress_callback("No main content found")
            return

        page_content = []

        page_content.append(f"\n\n{'=' * 80}\n")
        page_content.append(f"Source: {url}\n")

        if title := soup.find('h1', class_='fqn'):
            title_text = title.get_text().strip()
            page_content.append(f"# {title_text}\n")
            self.progress_callback(f"Found title: {title_text}")

        if code_section := main_content.find('pre', class_='rust'):
            if code_block := code_section.find('code'):
                code_text = code_block.get_text().strip()
                if code_text:
                    page_content.append(f"\n```rust\n{code_text}\n```\n")
                    self.progress_callback("Found code block")

        docblock = (
            main_content.find('div', class_='docblock') or
            main_content.find('div', class_='docblock-short') or
            main_content.find('div', class_='docblock docblock-short')
        )
        
        if docblock:
            if short_docblock := docblock.find('p', class_='docblock-short'):
                doc_text = short_docblock.get_text().strip()
                if doc_text:
                    page_content.append(f"\n{doc_text}\n")
            else:
                doc_text = docblock.get_text().strip()
                if doc_text:
                    page_content.append(f"\n{doc_text}\n")
            self.progress_callback("Found docblock")

        if details := main_content.find('details', class_='toggle'):
            if docblock := details.find('div', class_='docblock'):
                doc_text = docblock.get_text().strip()
                if doc_text:
                    page_content.append(f"\n## Details\n\n{doc_text}\n")
                    self.progress_callback("Found detailed documentation")

        section_headings = main_content.find_all(['h2', 'h3'], class_='section-header')
        for heading in section_headings:
            heading_text = heading.get_text().strip()
            page_content.append(f"\n## {heading_text}\n")
            
            section = heading.parent
            if section:
                items = section.find_all(class_=['item-table', 'impl-items'])
                for item in items:
                    item_text = item.get_text().strip()
                    if item_text:
                        page_content.append(f"{item_text}\n")
            
            self.progress_callback(f"Found section: {heading_text}")

        for impl_section in main_content.find_all('section', id=lambda x: x and x.startswith('impl')):
            if impl_title := impl_section.find(['h2', 'h3']):
                title_text = impl_title.get_text().strip()
                page_content.append(f"\n## {title_text}\n")
                
            for impl_item in impl_section.find_all(class_='impl-items'):
                if item_text := impl_item.get_text().strip():
                    page_content.append(f"```rust\n{item_text}\n```\n")

        reexports = main_content.find('div', id='reexports')
        if reexports:
            page_content.append("\n## Re-exports\n")
            for item in reexports.find_all(class_='item'):
                item_text = item.get_text().strip()
                if item_text:
                    page_content.append(f"{item_text}\n")
            self.progress_callback("Found re-exports")

        section_categories = [
            'modules', 'macros', 'structs', 'enums', 'traits', 
            'types', 'functions', 'constants', 'attributes'
        ]
        
        for category in section_categories:
            section = main_content.find('div', id=category)
            if section:
                page_content.append(f"\n## {category.title()}\n")
                
                for item in section.find_all(['div', 'li'], class_=['item', 'struct', 'enum', 'trait', 'fn']):
                    item_text = item.get_text().strip()
                    if item_text:
                        if any(keyword in item_text.lower() for keyword in ['fn ', 'struct ', 'enum ', 'trait ', 'type ', 'impl ']):
                            page_content.append(f"```rust\n{item_text}\n```\n")
                        else:
                            page_content.append(f"{item_text}\n")
                
                self.progress_callback(f"Found {category} section")

        page_content.append("\n")
        
        if page_content:
            self.progress_callback(f"Adding content from {url}")
            self.content.extend(page_content)
        else:
            self.progress_callback(f"No content found for {url}")

    def find_documentation_links(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        crate_path = self.base_url.rstrip('/')
        
        nav_elements = [
            soup.find_all('ul', class_='item-table'),
            soup.find_all('div', class_='sidebar-elems'),
            soup.find_all('nav', class_='sidebar'),
            soup.find_all('section', class_='block'),
        ]
        
        for elements in nav_elements:
            for element in elements:
                for link in element.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('./'):
                        href = href[2:]
                    if href.startswith('#'):
                        continue
                        
                    full_url = f"{crate_path}/{href}"
                    
                    if (full_url.startswith(crate_path) and
                        not 'target-redirect' in full_url and
                        not 'index.html' in full_url and
                        full_url not in self.visited_urls):
                        links.append(full_url)
        
        main_content = (
            soup.find('div', {'id': 'main-content'}) or 
            soup.find('div', class_='rustdoc')
        )
        
        if main_content:
            for link in main_content.find_all('a', href=True):
                href = link['href']
                if href.startswith('./'):
                    href = href[2:]
                if href.startswith('#'):
                    continue
                    
                full_url = f"{crate_path}/{href}"
                
                if (full_url.startswith(crate_path) and
                    not 'target-redirect' in full_url and
                    not 'index.html' in full_url and
                    full_url not in self.visited_urls and
                    full_url not in links):
                    links.append(full_url)
        
        return links

    def scrape(self):
        try:
            self.progress_callback("Starting documentation scraping...")
            main_html = self.fetch_page(self.base_url)
            if not main_html:
                self.progress_callback("ERROR: Failed to fetch main page")
                return False
            
            self.parse_content(main_html, self.base_url)
            
            links_to_visit = self.find_documentation_links(main_html)
            total_links = len(links_to_visit)
            processed_links = 0
            
            self.progress_callback(f"Found {total_links} documentation pages to process")
            
            while links_to_visit:
                link = links_to_visit.pop(0)
                processed_links += 1
                
                if link in self.visited_urls:
                    continue
                    
                self.progress_callback(f"Processing page {processed_links}/{total_links}: {link}")
                html = self.fetch_page(link)
                
                if html:
                    self.parse_content(html, link)
                    new_links = self.find_documentation_links(html)
                    new_links = [l for l in new_links if l not in self.visited_urls and l not in links_to_visit]
                    links_to_visit.extend(new_links)
                    if new_links:
                        total_links = len(links_to_visit) + processed_links
                        self.progress_callback(f"Found {len(new_links)} new pages, total: {total_links}")
            
            self.progress_callback(f"Completed processing {processed_links} pages")
            return True
            
        except Exception as e:
            self.progress_callback(f"ERROR: Scraping failed - {str(e)}")
            return False

    def save_to_file(self, filename):
        self.progress_callback("Saving documentation to file...")
        
        content_text = ''.join(self.content)
        
        if not content_text:
            self.progress_callback("WARNING: No content to save!")
            return False
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content_text)
            self.progress_callback(f"Successfully saved to {filename}")
            return True
        except Exception as e:
            self.progress_callback(f"ERROR: Failed to save file - {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Scrape documentation from docs.rs')
    parser.add_argument('crate_url', help='The docs.rs URL to scrape')
    parser.add_argument('output', help='Output markdown file')
    
    args = parser.parse_args()
    scraper = DocsRsScraper(args.crate_url)
    scraper.scrape()
    scraper.save_to_file(args.output)

if __name__ == "__main__":
    main()