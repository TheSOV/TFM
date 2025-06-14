"""
Stack Exchange API helper class for interacting with Stack Exchange sites like Stack Overflow.
Handles API requests, rate limiting, and response parsing.
"""

import os
import time
from typing import Dict, List, Generator, Optional, Any, Union
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class StackExchangeHelper:
    """
    A helper class for interacting with the Stack Exchange API.
    
    This class provides methods to search for questions and retrieve answers
    from Stack Exchange sites like Stack Overflow.
    
    Attributes:
        api_base_url (str): Base URL for Stack Exchange API
        app_key (str): API key for Stack Exchange (optional but recommended)
        user_agent (str): User agent string for API requests
        timeout (int): Request timeout in seconds
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        user_agent: str = "CrewAI/1.0 (+https://crewai.io)",
        timeout: int = 30
    ) -> None:
        """
        Initialize the StackExchangeHelper.
        
        Args:
            api_key: Stack Exchange API key (optional but recommended for higher rate limits)
            user_agent: User agent string for API requests
            timeout: Request timeout in seconds
        """
        self.api_base_url = "https://api.stackexchange.com/2.3"
        self.app_key = api_key or os.getenv("STACK_EXCHANGE_API_KEY", "")
        self.user_agent = user_agent
        self.timeout = timeout
    
    def _make_request(self, path: str, **params: Any) -> Dict[str, Any]:
        """
        Internal method to make GET requests to the Stack Exchange API.
        
        Args:
            path: API endpoint path
            **params: Query parameters for the request
            
        Returns:
            Dict containing the JSON response
            
        Raises:
            requests.HTTPError: If the API request fails
        """
        if self.app_key:
            params["key"] = self.app_key
            
        headers = {"User-Agent": self.user_agent}
        
        try:
            response = requests.get(
                f"{self.api_base_url}{path}",
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # Handle backoff if specified in the response
            if "backoff" in data and isinstance(data["backoff"], int):
                time.sleep(data["backoff"] + 1)
                
            return data
            
        except requests.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def search_questions(
        self,
        query: str,
        site: str = "stackoverflow",
        pages: int = 1,
        page_size: int = 10,
        min_answers: int = 1,
        title_contains: Optional[str] = None,
        tagged: Optional[str] = None,
        has_accepted_answer: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for questions on Stack Exchange sites.
        
        Args:
            query: Search query string
            site: Stack Exchange site to search (default: stackoverflow)
            pages: Number of pages of results to retrieve
            page_size: Number of results per page (max 100)
            min_answers: Minimum number of answers a question must have
            title_contains: Text that must appear in the question title
            tagged: Semicolon-separated list of tags
            has_accepted_answer: Whether the question has an accepted answer
            
        Returns:
            List of dictionaries containing question data for each matching question
        """
        results = []
        for page in range(1, pages + 1):
            params = {
                "q": query,
                "site": site,
                "order": "desc",
                "sort": "relevance",
                "answers": min_answers,
                "page": page,
                "pagesize": min(page_size, 100),  # API max is 100
                "filter": "default",
            }
            
            if title_contains:
                params["intitle"] = title_contains
            if tagged:
                params["tagged"] = tagged
            if has_accepted_answer is not None:
                params["accepted"] = str(has_accepted_answer).lower()
                
            data = self._make_request("/search/advanced", **params)
            results.extend(data.get("items", []))
            
        return results
    
    def get_question_and_answers(
        self,
        question_id: Union[int, str],
        site: str = "stackoverflow",
        answer_limit: int = 3
    ) -> Dict[str, Any]:
        """
        Get a question and its top answers.
        
        Args:
            question_id: ID of the question to retrieve
            site: Stack Exchange site (default: stackoverflow)
            answer_limit: Maximum number of top answers to retrieve
            
        Returns:
            Dict containing:
                - question: The question data
                - accepted: List containing the accepted answer (if any)
                - top: List of top-voted answers (excluding accepted answer)
        """
        # Get the question with body
        question_data = self._make_request(
            f"/questions/{question_id}",
            site=site,
            filter="withbody"
        )
        
        if not question_data.get("items"):
            raise ValueError(f"Question with ID {question_id} not found")
            
        question = question_data["items"][0]
        
        # Get answers sorted by votes
        answers_data = self._make_request(
            f"/questions/{question_id}/answers",
            site=site,
            sort="votes",
            pagesize=answer_limit + 1,  # +1 to account for possible accepted answer
            filter="withbody"
        )
        
        answers = answers_data.get("items", [])
        accepted_answer_id = question.get("accepted_answer_id")
        
        # Separate accepted answer from top answers
        accepted = [a for a in answers if a["answer_id"] == accepted_answer_id]
        top = [a for a in answers if a["answer_id"] != accepted_answer_id][:answer_limit]
        
        return {
            "question": question,
            "accepted": accepted,
            "top": top
        }