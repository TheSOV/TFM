from __future__ import annotations

# Standard library imports
import asyncio
import json
import logging
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

logger = logging.getLogger(__name__)

class WebBrowserToolInput(BaseModel):
    """Input schema for :class:`WebBrowserTool`."""

    queries: List[str] = Field(..., description="Initial queries provided by the user.")
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
        "and highlighting related topics. You can search multiple,different topics "
        "and will receive a report for each topic."
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
        logger.info("WebBrowserTool initialized.")

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
            logger.info(f"Generating queries for original query: '{query}'")
            response = self._llm.call(prompt)
            logger.info(f"LLM response for query generation: {response}")

            improved: List[str] = json.loads(response)

            if not isinstance(improved, list) or len(improved) != 2:
                raise ValueError("LLM did not return two improved queries")
            return [query, *improved]
        except Exception as exc:
            logger.error(f"Failed to generate queries: {exc}", exc_info=True)
            if feedback is not None:
                feedback["value"] = f"Failed to generate queries: {exc}"
            raise

    # ------------------------------------------------------------------
    # Step 2 – Run Brave Search
    # ------------------------------------------------------------------
    async def _search_queries_async(self, queries: List[str]) -> str:
        """Run BraveSearch for each query concurrently and concatenate raw results."""
        logger.info(f"Performing async search for queries: {queries}")

        async def _run_search(q: str) -> str:
            try:
                logger.info(f"Running search for query: '{q}'")
                result = self._brave_search.run(query=q)  # type: ignore[no-any-return]
                logger.info(f"Search for '{q}' returned {len(result)} characters.")
                return result
            except Exception as exc:
                logger.error(f"Error during search for query '{q}': {exc}", exc_info=True)
                return ""

        results = await asyncio.gather(*[_run_search(q) for q in queries])
        logger.info("Async search finished.")
        return "\n\n".join(r for r in results if r)

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
            - "reason": short justification (one sentence)
            - "url": the page URL

        Example response:\n{json_example}

        Return *only* valid JSON, no additional text, do not include any additional text like 
        json at the begining or end of the response.

        If the section <feedback> is provided, it will contain information about an error during a previous execution of the task.
        <feedback>
        {feedback}
        </feedback>
        """
        try:
            logger.info("Selecting top results from raw search output.")
            logger.info("Calling LLM to select top results.")
            response = self._llm.call(prompt)
            logger.info(f"LLM response for top results selection: {response}")

            parsed: List[Dict[str, str]] = json.loads(response)
            urls = [itm["url"] for itm in parsed][:10]

            if not isinstance(urls, list) or not all(isinstance(u, str) for u in urls):
                raise ValueError("LLM did not return a list of URLs")
            logger.info(f"Selected top URLs: {urls}")
            return urls
        except Exception as exc:
            logger.error(f"Failed to select top results: {exc}", exc_info=True)
            if feedback is not None:
                feedback["value"] = f"Failed to select top results: {exc}"
            raise

    # ------------------------------------------------------------------
    # Step 4 – Async scraping helpers
    # ------------------------------------------------------------------
    async def _scrape_async(self, urls: List[str]) -> Dict[str, str]:
        """Scrape URLs concurrently using crawl4ai's AsyncWebCrawler."""
        logger.info(f"Scraping URLs: {urls}")
        async with AsyncWebCrawler() as crawler:
            tasks = [crawler.arun(url=u) for u in urls]
            results = await asyncio.gather(*tasks, return_exceptions=False)

        logger.info("Async scraping finished.")
        contents: Dict[str, str] = {}
        for url, res in zip(urls, results):
            try:
                content = res.markdown if hasattr(res, "markdown") else str(res)
                if content:
                    contents[url] = content
                    logger.info(f"Successfully scraped {url} ({len(content)} chars).")
                else:
                    logger.warning(f"Scraping {url} returned no content.")
            except Exception as exc:
                logger.error(f"Error scraping {url}: {exc}", exc_info=True)
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
          • Answer the question concisely, in a clear and precise way.
          • Reference insights from the documents (cite URLs).
          • Mention (only mention) related topics that might be relevant to the question.
          • Format the output as **Markdown** with clear headings, code blocks, etc. Do not
          create an extensive report.

        If the section <feedback> is provided, it will contain information about an error during a previous execution of the task.
        <feedback>
        {feedback}
        </feedback>
        """
        try:
            logger.info(f"Generating report for query: '{query}'")
            report = self._llm.call(prompt)
            logger.info("LLM call for report generation finished.")
            return report
        except Exception as exc:
            logger.error(f"Failed to generate report: {exc}", exc_info=True)
            if feedback is not None:
                feedback["value"] = f"Failed to generate report: {exc}"
            raise

    # ------------------------------------------------------------------
    # Public entrypoint – orchestrate everything
    # ------------------------------------------------------------------
    async def async_one_run(self, query: str, detailed: bool = True) -> str:
        """Run the full pipeline and return a markdown report."""

        feedback: Dict[str, str] = {"value": ""}
        logger.info(f"Starting web search for query: '{query}'")

        # Step 1 – Generate alternative queries
        try:
            logger.info("Step 1: Generating queries...")
            queries = await asyncio.to_thread(self._generate_queries, query, feedback=feedback)
            logger.info(f"Generated queries: {queries}")
        except Exception as exc:
            logger.error(f"Error in _generate_queries: {exc}", exc_info=True)
            return f"Error in _generate_queries: {exc}\n{feedback['value']}"

        # Step 2 – Search the web (async)
        try:
            logger.info("Step 2: Searching queries...")
            raw_results = await self._search_queries_async(queries)
            logger.info(f"Search returned {len(raw_results)} characters.")
        except Exception as exc:
            logger.error(f"Error in _search_queries_async: {exc}", exc_info=True)
            return f"Error in _search_queries_async: {exc}\n{feedback['value']}"

        # Step 3 – Select top URLs
        try:
            logger.info("Step 3: Selecting top results...")
            top_urls = await asyncio.to_thread(self._select_top_results, raw_results, query, feedback=feedback)
            if not top_urls:
                logger.warning("No relevant results were found.")
                return "No relevant results were found for the given query."
            logger.info(f"Selected top URLs: {top_urls}")
        except Exception as exc:
            logger.error(f"Error in _select_top_results: {exc}", exc_info=True)
            return f"Error in _select_top_results: {exc}\n{feedback['value']}"

        # Step 4 – Scrape selected URLs
        try:
            logger.info("Step 4: Scraping URLs...")
            documents = await self._scrape_async(top_urls)
            if not documents:
                logger.warning("Failed to retrieve content from selected URLs.")
                return "Failed to retrieve content from selected URLs."
            logger.info(f"Scraped {len(documents)} documents.")
        except Exception as exc:
            logger.error(f"Error in _scrape_async: {exc}", exc_info=True)
            return f"Error in _scrape_async: {exc}\n{feedback['value']}"

        # Step 5 – Generate final report
        try:
            logger.info("Step 5: Generating final report...")
            report = await asyncio.to_thread(self._generate_report, query, documents, feedback=feedback)
            logger.info("Report generated successfully.")
            return report
        except Exception as exc:
            logger.error(f"Error in _generate_report: {exc}", exc_info=True)
            return f"Error in _generate_report: {exc}\n{feedback['value']}"

    def one_run(self, query: str, detailed: bool = True) -> str:
        """Run the full pipeline for a single query."""
        return asyncio.run(self.async_one_run(query, detailed))

    def _run(self, queries: List[str], detailed: bool = True) -> str:  # type: ignore[override]
        """Run the full pipeline for multiple queries concurrently and return a markdown report."""

        async def _run_async_tasks():
            tasks = [self.async_one_run(query, detailed) for query in queries]
            return await asyncio.gather(*tasks)

        answers = asyncio.run(_run_async_tasks())
        results = [f"Question: {q}\n\n{a}" for q, a in zip(queries, answers)]
        return "\n\n**************************\n\n".join(results)