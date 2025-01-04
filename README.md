# Docs.rs Scraper

A web application that scrapes and converts docs.rs documentation into a single markdown file. This tool allows you to easily create offline documentation for Rust crates.

## Quick Start with Docker

```bash
git clone https://github.com/toolworks-dev/docsrs-scraper.git
cd docsrs-scraper

docker compose up -d

Access the web interface at http://localhost:8721
```

## Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/toolworks-dev/docsrs-scraper.git
cd docsrs-scraper
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run with Gunicorn:
```bash
gunicorn --bind 0.0.0.0:8721 --workers 4 --timeout 120 wsgi:app
```

## Usage

### Web Interface
1. Navigate to `http://localhost:8721`
2. Enter the crate path (e.g., `wgpu/latest/wgpu`)
3. Enter desired output filename
4. Click "Generate Documentation"
5. Download the generated markdown file

### Command Line
```bash
python docs_scraper.py https://docs.rs/wgpu/latest/wgpu output.md
```
