"""SerpAPI client for live prospect/topic research (free tier: 100 searches/month)."""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"


class WebSearch:
    """Wrapper around SerpAPI for Google search results."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("SERPAPI_KEY", "")
        if not self.api_key:
            raise ValueError("SERPAPI_KEY is required. Set it as an environment variable.")
        self.client = httpx.Client(timeout=30.0)

    def search(self, query: str, count: int = 5) -> list[dict]:
        """
        Run a Google search via SerpAPI and return simplified results.

        Returns a list of dicts with keys: title, url, description.
        Returns an empty list on failure.
        """
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "num": count,
        }

        try:
            resp = self.client.get(SERPAPI_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("SerpAPI search failed for query '%s': %s", query, e)
            return []

        results = []
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "description": item.get("snippet", ""),
            })
        return results

    def research_prospect(self, name: str, company: str) -> str:
        """
        Research a prospect by searching for recent news and activity.

        Returns a plain text summary of findings, or "Not found" if nothing useful.
        """
        queries = [
            f'"{name}" "{company}" site:linkedin.com',
            f'"{name}" "{company}" news OR announcement OR interview',
            f'"{company}" recent news funding launch',
        ]

        all_results = []
        for q in queries:
            results = self.search(q, count=3)
            all_results.extend(results)

        if not all_results:
            return "Not found"

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique: list[dict] = []
        for r in all_results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                unique.append(r)

        lines = []
        for r in unique:
            lines.append(f"- [{r['title']}]({r['url']}): {r['description']}")

        return "\n".join(lines) if lines else "Not found"

    def research_topic(self, topic: str) -> str:
        """
        Research a topic for LinkedIn post content.

        Returns a plain text summary of findings.
        """
        results = self.search(f"{topic} trends insights data 2025 2026", count=5)
        if not results:
            return "Not found"

        lines = []
        for r in results:
            lines.append(f"- [{r['title']}]({r['url']}): {r['description']}")

        return "\n".join(lines) if lines else "Not found"

    def close(self) -> None:
        self.client.close()
