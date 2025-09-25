import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from langchain.schema import Document
from service.log_helper import LogHelper
from service.hash_helper import HashHelper
from service.html_playwright_loader import HtmlPlaywrightLoader
from config import HTML_MIN_TEXT_CHARS

class WebsiteLoader:
    def __init__(self, url: str):
        self.url = url
        self.logger = LogHelper.get_logger("WebsiteLoader")

    def _auto_title(self) -> str:
        parsed = urlparse(self.url)
        return f"{parsed.netloc}{parsed.path}".replace("/", " ").strip()

    def load_basic(self) -> Document | None:
        """Load webpage content using basic HTTP + BeautifulSoup"""
        try:
            resp = requests.get(self.url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(" ", strip=True)
            
            doc_hash = HashHelper.url_hash(self.url, text)
            title = self._auto_title()
            doc = Document(
                page_content=text, 
                metadata={
                    "url": self.url, 
                    "hash": doc_hash, 
                    "title": title
                }
            )
            return doc
        except Exception as e:
            self.logger.error(f"Failed to load {self.url}: {e}")
            return None

    def load(self) -> Document | None:
        """
        Load webpage content with intelligent fallback:
        1. Try basic HTTP scraping first (fast)
        2. If content is too thin, use Playwright expansion (slower but complete)
        """
        # Try basic loading first
        basic_doc = self.load_basic()
        if not basic_doc:
            return None
            
        # Check if content is sufficient
        if len(basic_doc.page_content.strip()) >= HTML_MIN_TEXT_CHARS:
            self.logger.info(f"Loaded website (basic): {self.url}")
            return basic_doc
        
        # Content too thin - try Playwright expansion
        self.logger.info(f"Content too thin ({len(basic_doc.page_content)} < {HTML_MIN_TEXT_CHARS}), trying Playwright: {self.url}")
        
        try:
            playwright_loader = HtmlPlaywrightLoader()
            docs = playwright_loader.expand_and_extract([self.url])
            
            if docs and len(docs) > 0:
                # Use the first document from Playwright
                playwright_doc = docs[0]
                # Update metadata to match our format
                doc_hash = HashHelper.url_hash(self.url, playwright_doc.page_content)
                title = self._auto_title()
                playwright_doc.metadata.update({
                    "url": self.url,
                    "hash": doc_hash, 
                    "title": title
                })
                self.logger.info(f"Loaded website (playwright): {self.url}")
                return playwright_doc
            else:
                self.logger.warning(f"Playwright returned no content, falling back to basic: {self.url}")
                return basic_doc
                
        except ImportError:
            self.logger.warning(f"Playwright not available, using basic content: {self.url}")
            return basic_doc
        except Exception as e:
            self.logger.error(f"Playwright failed for {self.url}: {e}, falling back to basic content")
            return basic_doc
