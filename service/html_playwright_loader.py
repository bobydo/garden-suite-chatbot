import time
from typing import List
from langchain_community.document_loaders import OnlinePDFLoader
from langchain_core.documents import Document
from playwright.sync_api import sync_playwright
from service.log_helper import LogHelper
from config import HTML_MIN_TEXT_CHARS


class HtmlPlaywrightLoader:
    """Render, expand, and extract text from web pages using Playwright.
    """

    def __init__(self, user_agent: str = "Mozilla/5.0") -> None:
        self.user_agent = user_agent
        self.logger = LogHelper.get_logger("HtmlPlaywrightLoader")

    def expand_and_extract(self, urls: List[str]):
        docs = []
        t0 = time.perf_counter()
        self.logger.info("playwright: start render: urls=%d", len(urls) if urls else 0)
        processed = 0
        skipped = 0

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=self.user_agent,
                ignore_https_errors=True,
                service_workers="block",
            )

            # Block heavy assets for speed
            ctx.route(
                "**/*",
                lambda route: route.abort()
                if any(route.request.url.endswith(ext) for ext in (
                    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".woff", ".woff2"
                ))
                else route.continue_(),
            )

            page = ctx.new_page()
            for url in (urls or []):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)

                    # Try to dismiss cookie banners
                    for txt in ("Accept", "I agree", "Got it"):
                        try:
                            page.get_by_role("button", name=txt, exact=False).click(timeout=1500)
                            break
                        except Exception:
                            pass

                    # Click "Open All" if present (bylaw pages)
                    try:
                        page.get_by_text("Open All", exact=False).click(timeout=2500)
                    except Exception:
                        pass

                    # Expand accordions
                    for b in page.locator("button[aria-controls]").all():
                        try:
                            if b.get_attribute("aria-expanded") == "false":
                                b.click()
                        except Exception:
                            pass

                    # Extract text
                    try:
                        page.wait_for_selector("main", timeout=4000)
                        text = page.locator("main").inner_text(timeout=4000)
                    except Exception:
                        text = page.inner_text("body", timeout=4000)

                    text = (text or "").strip()

                    # Fallback to a "Create PDF" link when page is thin
                    if len(text) < HTML_MIN_TEXT_CHARS:
                        try:
                            link = page.get_by_role("link", name="Create PDF", exact=False).first
                            href = link.get_attribute("href")
                            if href and href.startswith("http"):
                                pdf_docs = OnlinePDFLoader(href).load()
                                docs.extend(pdf_docs)
                                self.logger.info(
                                    "playwright: pdf-fallback ok: url=%s added=%d ",
                                    url,
                                    len(pdf_docs)
                                )
                                processed += 1
                                continue
                        except Exception:
                            pass

                    if text:
                        before = len(docs)
                        docs.append(Document(page_content=text, metadata={"source": url}))
                        added = len(docs) - before
                        self.logger.info(
                            "playwright: page ok: url=%s text_len=%d docs_added=%d",
                            url,
                            len(text),
                            added
                        )
                        processed += 1
                except Exception as e:
                    self.logger.warning("playwright: page fail: url=%s err=%s", url, e)

            ctx.close()
            browser.close()

        total = time.perf_counter() - t0
        self.logger.info(
            "playwright: done: processed=%d skipped=%d docs=%d elapsed_s=%.2f",
            processed,
            skipped,
            len(docs),
            total,
        )
        return docs
