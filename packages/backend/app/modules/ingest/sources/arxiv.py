"""
arXiv paper searcher implementation.
"""

import logging
from typing import List
import httpx
from datetime import datetime

from .base import PlatformSearcher, SearchResult, ContentType, SearchError

logger = logging.getLogger(__name__)


class ArxivSearcher(PlatformSearcher):
    """Searcher for arXiv academic papers."""

    ARXIV_API_URL = "https://export.arxiv.org/api/query"

    @property
    def platform_name(self) -> str:
        return "arxiv"

    @property
    def content_type(self) -> ContentType:
        return ContentType.PAPER

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Search arXiv for academic papers.

        Args:
            query: Search query (supports arXiv search syntax)
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects with paper information
        """
        try:
            # Build search parameters
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.ARXIV_API_URL, params=params)
                response.raise_for_status()

            # Parse atom format response
            import xml.etree.ElementTree as ET

            root = ET.fromstring(response.content)

            # Define namespace
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }

            results = []
            for entry in root.findall("atom:entry", ns):
                try:
                    # Extract paper information
                    arxiv_id = entry.find("atom:id", ns).text.split("/")[-1]

                    # Get title
                    title_elem = entry.find("atom:title", ns)
                    title = title_elem.text.strip() if title_elem is not None else "Untitled"

                    # Get summary (abstract)
                    summary_elem = entry.find("atom:summary", ns)
                    description = summary_elem.text.strip() if summary_elem is not None else ""

                    # Get authors
                    authors = []
                    for author in entry.findall("atom:author", ns):
                        name_elem = author.find("atom:name", ns)
                        if name_elem is not None:
                            authors.append(name_elem.text)

                    # Get published date
                    published_elem = entry.find("atom:published", ns)
                    published_at = published_elem.text if published_elem is not None else None

                    # Get PDF URL
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

                    # Get primary category
                    category_elem = entry.find("arxiv:primary_category", ns)
                    category = category_elem.get("term", "") if category_elem is not None else ""

                    results.append(SearchResult(
                        id=f"arxiv_{arxiv_id}",
                        title=title,
                        description=description,
                        url=f"https://arxiv.org/abs/{arxiv_id}",
                        thumbnail=None,
                        duration=None,
                        author=", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""),
                        published_at=published_at,
                        view_count=None,
                        platform=self.platform_name,
                        content_type=ContentType.PAPER,
                        metadata={
                            "arxiv_id": arxiv_id,
                            "pdf_url": pdf_url,
                            "category": category,
                            "authors": authors,
                        }
                    ))

                except Exception as e:
                    logger.warning(f"[ArxivSearcher] Error parsing entry: {e}")
                    continue

            logger.info(f"[ArxivSearcher] Found {len(results)} papers for '{query}'")
            return results

        except httpx.HTTPError as e:
            raise SearchError(f"HTTP error searching arXiv: {e}")
        except Exception as e:
            raise SearchError(f"Error searching arXiv: {e}")

    async def download(self, content_id: str, output_path: str) -> str:
        """
        Download arXiv paper PDF.

        Args:
            content_id: arXiv paper ID (with or without 'arxiv_' prefix)
            output_path: Directory to save the PDF

        Returns:
            Path to downloaded PDF file
        """
        import asyncio
        from pathlib import Path

        # Remove prefix if present
        arxiv_id = content_id.replace("arxiv_", "")

        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = output_dir / f"{arxiv_id}.pdf"

        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                async with client.stream("GET", pdf_url) as response:
                    response.raise_for_status()

                    with open(pdf_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)

            logger.info(f"[ArxivSearcher] Downloaded {arxiv_id}.pdf")
            return str(pdf_path)

        except Exception as e:
            raise SearchError(f"Failed to download arXiv paper: {e}")
