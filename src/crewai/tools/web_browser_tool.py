from __future__ import annotations

# Standard library imports
import asyncio
import json
import os

from typing import Any, Dict, List, Optional, Type

# Third-party imports
from crawl4ai import AsyncWebCrawler
from pydantic import BaseModel, Field, PrivateAttr

# CrewAI imports
from crewai.tools import BaseTool
from crewai import LLM
from crewai_tools import BraveSearchTool

# Local utilities
from src.retry_mechanism.retry import retry_with_feedback

__all__ = ["WebBrowserToolInput", "WebBrowserTool"]


class WebBrowserToolInput(BaseModel):
    """Input schema for :class:`WebBrowserTool`."""

    query: str = Field(..., description="Initial query provided by the user.")
    detailed: bool = Field(
        True,
        description="Whether to generate a detailed markdown report (uses more tokens).",
    )


class WebBrowserTool(BaseTool):
    """Searches the web, scrapes results and builds a markdown report.

    Pipeline (each step implemented as a private helper method):

    1. ``_generate_queries`` – Improve the original query using the LLM.
    2. ``_search_queries`` – Run Brave Search for each query.
    3. ``_select_top_results`` – Ask the LLM to pick the 10 best matching URLs.
    4. ``_scrape_async`` – Download & extract text from the selected URLs in parallel.
    5. ``_generate_report`` – Create the final markdown report.

    All heavy LLM calls are wrapped with :func:`retry_with_feedback` for resilience.
    """

    name: str = "web_browser_tool"
    args_schema: Type[BaseModel] = WebBrowserToolInput
    description: str = (
        "Search the web using multiple refined queries, scrape the top-matching "
        "pages, and return a structured markdown report answering the question "
        "and highlighting related topics."
    )

    _llm: Any = PrivateAttr()
    _brave_search: BraveSearchTool = PrivateAttr()

    # ---------------------------------------------------------------------
    # Construction helpers
    # ---------------------------------------------------------------------
    def __init__(self, brave_search: BraveSearchTool, **kwargs) -> None:  # noqa: D401
        """Instantiate the tool with its external dependencies."""
        super().__init__(**kwargs)
        self._brave_search = brave_search
        self._llm = LLM(model=os.getenv("TOOL_MODEL", "gpt-4.1-mini"), temperature=0)

    # ------------------------------------------------------------------
    # Step 1 – Generate improved queries
    # ------------------------------------------------------------------
    @retry_with_feedback(max_attempts=3, delay=1.0)
    def _generate_queries(
        self, query: str, *, feedback: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """Return the original query plus two LLM-improved versions."""

        prompt = f"""
        You are an expert search strategist. Your task is to improve a user query so that
        web search engines return the most relevant, high-quality technical content.

        ORIGINAL QUERY: "{query}"

        Produce exactly two *different* improved queries. Each should retain the intent
        but use alternative wording or additional keywords that increase precision.
        Respond with a JSON list of *two* strings. Do not include any other text.

        Return *only* valid JSON list of two strings, do not include any additional text like 
        json at the begining or end of the response.

        If the section <feedback> is provided, it will contain information about an error during a previous execution of the task.
        <feedback>
        {feedback}
        </feedback>
        """
        try:
            response = self._llm.call(prompt)

            improved: List[str] = json.loads(response)

            if not isinstance(improved, list) or len(improved) != 2:
                raise ValueError("LLM did not return two improved queries")
            return [query, *improved]
        except Exception as exc:
            if feedback is not None:
                feedback["value"] = f"Failed to generate queries: {exc}"
            raise

    # ------------------------------------------------------------------
    # Step 2 – Run Brave Search
    # ------------------------------------------------------------------
    async def _search_queries_async(self, queries: List[str]) -> str:
        """Run BraveSearch for each query concurrently and concatenate raw results."""

        loop = asyncio.get_running_loop()

        async def _run_search(q: str) -> str:
            try:
                # BraveSearchTool is sync; execute in thread pool to avoid blocking.
                raw = await loop.run_in_executor(None, self._brave_search._run, q)
                return f"\n=== Results for: {q} ===\n{raw}"
            except Exception as exc:
                return f"\n=== Results for: {q} (FAILED: {exc}) ===\n"

        gathered = await asyncio.gather(*[_run_search(q) for q in queries])
        return "\n".join(gathered)

    # ------------------------------------------------------------------
    # Step 3 – Select best matches
    # ------------------------------------------------------------------
    @retry_with_feedback(max_attempts=3, delay=1.0)
    def _select_top_results(
        self,
        raw_results: str,
        query: str,
        *,
        feedback: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """Use the LLM to pick up to 10 URLs ranked by relevance."""

        json_example = json.dumps(
            [
                {
                    "url": "https://example.com/path",
                    "reason": "Explains the topic in depth and directly answers the question.",
                }
            ],
            indent=4,
        )

        prompt = f"""
        You are a senior technical researcher. Analyse the following raw search output
        and pick the ten most relevant URLs for the user's query.

        USER QUERY: {query}
        RAW SEARCH OUTPUT:\n{raw_results}

        Respond with a JSON array where each object contains:
          - "url": the page URL
          - "reason": short justification (one sentence)

        Example response:\n{json_example}

        Return *only* valid JSON, no additional text, do not include any additional text like 
        json at the begining or end of the response.

        If the section <feedback> is provided, it will contain information about an error during a previous execution of the task.
        <feedback>
        {feedback}
        </feedback>
        """
        try:
            response = self._llm.call(prompt)
            parsed: List[Dict[str, str]] = json.loads(response)
            urls = [itm["url"] for itm in parsed][:10]
            return urls
        except Exception as exc:
            if feedback is not None:
                feedback["value"] = f"Failed to select top results: {exc}"
            raise

    # ------------------------------------------------------------------
    # Step 4 – Async scraping helpers
    # ------------------------------------------------------------------
    async def _scrape_async(self, urls: List[str]) -> Dict[str, str]:
        """Scrape URLs concurrently using crawl4ai's AsyncWebCrawler."""

        async with AsyncWebCrawler() as crawler:
            tasks = [crawler.arun(url=u) for u in urls]
            results = await asyncio.gather(*tasks, return_exceptions=False)

        contents: Dict[str, str] = {}
        for url, res in zip(urls, results):
            try:
                contents[url] = res.markdown if hasattr(res, "markdown") else str(res)
            except Exception:
                continue
        return {k: v for k, v in contents.items() if v}

    # ------------------------------------------------------------------
    # Step 5 – Generate final report
    # ------------------------------------------------------------------
    @retry_with_feedback(max_attempts=3, delay=1.0)
    def _generate_report(
        self,
        query: str,
        documents: Dict[str, str],
        *,
        feedback: Optional[Dict[str, str]] = None,
    ) -> str:
        """Ask the LLM to build a high-quality markdown report."""

        prompt = f"""
        You are writing a comprehensive technical report for DevOps engineers.

        QUESTION: {query}
        SOURCE DOCUMENTS (mapping URL -> content):\n{json.dumps(documents)[:8000]}  # limit to remain within context

        TASK:
          • Answer the question thoroughly.
          • Reference insights from the documents (cite URLs).
          • Highlight related topics that appear in the sources.
          • Format the output as **Markdown** with clear headings, code blocks, etc.

        If the section <feedback> is provided, it will contain information about an error during a previous execution of the task.
        <feedback>
        {feedback}
        </feedback>
        """
        try:
            return self._llm.call(prompt)
        except Exception as exc:
            if feedback is not None:
                feedback["value"] = f"Failed to generate report: {exc}"
            raise

    # ------------------------------------------------------------------
    # Public entrypoint – orchestrate everything
    # ------------------------------------------------------------------
    def _run(self, query: str, detailed: bool = True) -> str:  # type: ignore[override]
        """Run the full pipeline and return a markdown report."""

        feedback: Dict[str, str] = {"value": ""}

        # Step 1 – Generate alternative queries
        try:
            queries = self._generate_queries(query, feedback=feedback)
        except Exception as exc:
            return f"Error in _generate_queries: {exc}\n{feedback['value']}"

        # Step 2 – Search the web (async)
        try:
            raw_results = asyncio.run(self._search_queries_async(queries))
        except Exception as exc:
            return f"Error in _search_queries_async: {exc}\n{feedback['value']}"

        # Step 3 – Select top URLs
        try:
            top_urls = self._select_top_results(raw_results, query, feedback=feedback)
            if not top_urls:
                return "No relevant results were found for the given query."
        except Exception as exc:
            return f"Error in _select_top_results: {exc}\n{feedback['value']}"

        # Step 4 – Scrape selected URLs
        try:
            documents = asyncio.run(self._scrape_async(top_urls))
            if not documents:
                return "Failed to retrieve content from selected URLs."
        except Exception as exc:
            return f"Error in _scrape_async: {exc}\n{feedback['value']}"

        # Step 5 – Generate final report
        try:
            return self._generate_report(query, documents, feedback=feedback)
        except Exception as exc:
            return f"Error in _generate_report: {exc}\n{feedback['value']}"