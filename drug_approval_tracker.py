# 🚀 Streamlined Drug Approval Tracker

import os
import sys
import subprocess
import importlib
import json
import time
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List
from dataclasses import dataclass
import re
from urllib.parse import urlparse
import tempfile

# 📦 Auto-Installation Helper
def install_package(package_name, import_name=None):
    if import_name is None:
        import_name = package_name.replace("-", "_")
    try:
        importlib.import_module(import_name)
        print(f"✅ {package_name} - already installed")
        return True
    except ImportError:
        print(f"📦 Installing {package_name}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"✅ {package_name} - installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package_name}: {e}")
            return False

# 🔧 Setup Dependencies
def setup_dependencies():
    print("🔧 Checking and installing required dependencies...")
    required_packages = [
        ("PyMuPDF", "fitz"),
        ("requests", "requests"),
        ("pandas", "pandas"),
        ("google-generativeai", "google.generativeai"),
        ("beautifulsoup4", "bs4"),
        ("google-search-results", "serpapi"),
        ("python-dotenv", "dotenv"),
        ("ipywidgets", "ipywidgets")
    ]
    failed = []
    for pkg, imp in required_packages:
        if not install_package(pkg, imp):
            failed.append(pkg)
    if failed:
        print(f"\n❌ Failed to install: {', '.join(failed)}")
        print("Please install them manually.")
        return False
    return True

if not setup_dependencies():
    sys.exit(1)

# Imports after installing
import fitz
import google.generativeai as genai
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

# 🔐 API Keys
def get_api_keys():
    gemini_key = os.getenv('GEMINI_API_KEY')
    serpapi_key = os.getenv('SERPAPI_API_KEY')
    if not gemini_key:
        gemini_key = input("🔑 Enter your Gemini API key: ").strip()
    if not serpapi_key:
        serpapi_key = input("🔑 Enter your SerpAPI key: ").strip()
    return gemini_key, serpapi_key

try:
    gemini_api_key, serpapi_api_key = get_api_keys()
    genai.configure(api_key=gemini_api_key)
except Exception as e:
    print(f"❌ API key setup failed: {e}")
    sys.exit(1)

# 📋 Config
@dataclass
class Config:
    max_results: int = 10
    serpapi_delay: float = 2.0
    gemini_delay: float = 1.5
    max_retries: int = 3
    request_timeout: int = 30
    max_text_length: int = 8000

config = Config()

# 🔧 Logger
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'drug_tracker_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# 🔍 Search Manager
class SearchManager:
    def __init__(self, api_key: str, config: Config, logger: logging.Logger):
        self.api_key = api_key
        self.config = config
        self.logger = logger

    def search_drug_approvals(self, agency_domain='fda.gov', date_range='m', num_results=10):
        if agency_domain == 'fda.gov':
            query = 'site:fda.gov drug approval "approved" -generic'
        elif agency_domain == 'ema.europa.eu':
            query = 'site:ema.europa.eu "marketing authorisation" drug approved'
        elif agency_domain == 'cdsco.gov.in':
            query = 'site:cdsco.gov.in drug approval "approved" license'
        else:
            query = 'drug approval "approved" FDA OR EMA OR CDSCO'
        params = {
            'q': query,
            'api_key': self.api_key,
            'engine': 'google',
            'num': num_results,
            'tbs': f'qdr:{date_range}',
            'safe': 'active'
        }
        try:
            self.logger.info(f"Searching: {query}")
            results = GoogleSearch(params).get_dict()
            time.sleep(self.config.serpapi_delay)
            return results.get('organic_results', [])
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

# 📄 Content Extractor
class ContentExtractor:
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def extract_content(self, url: str) -> str:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=self.config.request_timeout)
            response.raise_for_status()
            if 'pdf' in response.headers.get('content-type', ''):
                return self._extract_pdf_content(response.content)
            return self._extract_html_content(response.text)
        except Exception as e:
            self.logger.error(f"Content extraction failed for {url}: {e}")
            return ""

    def _extract_pdf_content(self, pdf_content: bytes) -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_content)
                tmp_path = tmp.name
            text = ""
            with fitz.open(tmp_path) as doc:
                for page in doc:
                    text += page.get_text()
            os.unlink(tmp_path)
            return text[:self.config.max_text_length]
        except Exception as e:
            self.logger.error(f"PDF parse failed: {e}")
            return ""

    def _extract_html_content(self, html: str) -> str:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(["script", "style"]): tag.decompose()
            text = ' '.join(line.strip() for line in soup.get_text().splitlines() if line.strip())
            return text[:self.config.max_text_length]
        except Exception as e:
            self.logger.error(f"HTML parse failed: {e}")
            return ""

# 🤖 AI Analyzer
class AIAnalyzer:
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def analyze_content(self, content: str, url: str) -> Dict:
        prompt = f"""
Analyze this drug approval document and extract key information in JSON format:

Content: {content[:4000]}

{{
    "drug_name": "",
    "sponsor_company": "",
    "approval_date": "",
    "indication": "",
    "drug_type": "",
    "regulatory_action": "",
    "approval_status": "",
    "therapeutic_area": "",
    "source_agency": "",
    "source_url": "{url}",
    "confidence_score": ""
}}

If information is unavailable, return "Not specified".
"""
        try:
            response = self.model.generate_content(prompt)
            time.sleep(self.config.gemini_delay)
            text = response.text.strip().strip("```json").strip("```")
            result = json.loads(text)
            result['extraction_timestamp'] = datetime.now().isoformat()
            return result
        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            return {
                "drug_name": "Analysis failed",
                "sponsor_company": "Not specified",
                "approval_date": "Not specified",
                "indication": "Not specified",
                "drug_type": "Not specified",
                "regulatory_action": "Not specified",
                "approval_status": "Not specified",
                "therapeutic_area": "Not specified",
                "source_agency": "Not specified",
                "source_url": url,
                "confidence_score": 0.0,
                "extraction_timestamp": datetime.now().isoformat()
            }

# 🎯 Orchestration
class DrugApprovalTracker:
    def __init__(self):
        self.config = config
        self.logger = logger
        self.search_manager = SearchManager(serpapi_api_key, self.config, self.logger)
        self.extractor = ContentExtractor(self.config, self.logger)
        self.analyzer = AIAnalyzer(self.config, self.logger)

    def track_approvals(self, agency_domain='fda.gov', date_range='m', num_results=10) -> List[Dict]:
        results = self.search_manager.search_drug_approvals(agency_domain, date_range, num_results)
        processed = []
        for i, res in enumerate(results):
            url = res.get('link', '')
            content = self.extractor.extract_content(url)
            if not content:
                continue
            analysis = self.analyzer.analyze_content(content, url)
            analysis.update({
                'search_title': res.get('title', ''),
                'search_snippet': res.get('snippet', ''),
                'search_position': i + 1
            })
            processed.append(analysis)
        return processed

    def save_results(self, results: List[Dict], filename=None) -> str:
        if not filename:
            filename = f"drug_approvals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        path = output_dir / filename
        pd.DataFrame(results).to_csv(path, index=False)
        print(f"💾 Saved to: {path}")
        return str(path)

# 🚀 Main
if __name__ == "__main__":
    print("🚀 Starting Drug Approval Tracker")
    tracker = DrugApprovalTracker()
    results = tracker.track_approvals()
    if results:
        tracker.save_results(results)
    else:
        print("❌ No results found.")
