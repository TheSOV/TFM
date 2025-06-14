from typing import List, Dict, Any, Optional, Type, Union
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from src.crewai.tools.utils.stack.stack import StackExchangeHelper
from src.retry_mechanism.retry import retry_with_feedback
import json
from crewai import LLM
import os
from pydantic import PrivateAttr
from crewai_tools import BraveSearchTool

class StackOverflowSearchInput(BaseModel):
    """Input schema for StackOverflowSearchTool."""
    query: str = Field(..., description="Search query for Stack Overflow.")
    max_questions: int = Field(20, description="Maximum number of questions to retrieve and analyze.")
    top_answers: int = Field(3, description="Number of top answers to retrieve per question.")
    min_answers: int = Field(1, description="Minimum number of answers a question must have.")
    detailed: bool = Field(True, description="Whether to generate a detailed report with LLM analysis.")
    use_brave_search: bool = Field(True, description="Whether to use Brave Search for better results. If disabled, falls back to direct Stack Overflow search.")

class QuestionSelection(BaseModel):
    """Model for selected question IDs."""
    selected_question_ids: List[Union[int, str]] = Field(..., 
        description="List of selected question IDs. Must be a list of integers or strings that can be converted to integers."
    )
    reasoning: str = Field(..., 
        description="Brief explanation of why these questions were selected based on the query."
    )

class StackOverflowSearchTool(BaseTool):
    """
    Tool for searching and analyzing Stack Overflow content.
    Uses LLM to filter and select the most relevant questions and answers.
    """
    name: str = "stackoverflow_search"
    args_schema: Type[BaseModel] = StackOverflowSearchInput
    description: str = "Search and analyze Stack Overflow for technical questions and answers. Useful for debugging and getting information about a specific topic. Use short and simple queries."

    _stack_helper: StackExchangeHelper = PrivateAttr()
    _llm: Any = PrivateAttr()

    def __init__(
        self,
        brave_search: BraveSearchTool,
        **kwargs
    ) -> None:
        """
        Initialize the StackOverflow search tool.
        
        Args:
            brave_search: BraveSearchTool instance
        """
        super().__init__(**kwargs)
        self._stack_helper = StackExchangeHelper()
        self._brave_search = brave_search
        self._llm = LLM(
            model=os.getenv("TOOL_MODEL", "gpt-4.1-mini"),
            temperature=0
        )

    @retry_with_feedback(max_attempts=3, delay=1.0)
    def _select_relevant_questions(
        self,
        questions: List[Dict[str, Any]],
        query: str,
        feedback: Optional[Dict[str, str]] = None
    ) -> List[Union[int, str]]:
        """
        Use LLM to select the most relevant questions for the given query.
        
        Args:
            questions: List of question dictionaries from Stack Exchange API
            query: Original search query
            max_select: Maximum number of questions to select
            feedback: Optional feedback dict for retry mechanism
            
        Returns:
            List of selected question IDs
        """
        prompt = f"""
        You are an expert at analyzing technical questions and determining their relevance to a search query.
        
        TASK:
        - Analyze the following Stack Overflow questions
        - Select the most relevant questions for this query: "{query}"
        - Return a JSON object with 'selected_question_ids' and 'reasoning'
        
        GUIDELINES:
        1. Only select questions that directly address the query
        2. Prefer questions with higher scores (indicates quality/helpfulness)
        3. Ensure all returned IDs exist in the provided questions
        4. If no questions are relevant, return an empty list with reasoning
        
        Available Questions (format: [id] score - title):
        {questions}
        
        Your response must be valid JSON with this structure:
        {{
            "reasoning": "Brief explanation of your selection",
            "selected_question_ids": [123, 456, ...]
        }}

        Only respond with the JSON object, do not add any additional text or explanation or a JSON
        str at the begining or end of the response.

        If the section <feedback> is provided, it will contain information about an error during a previous execution of the task.

        <feedback>
        {feedback}
        </feedback>
        """
        
        try:
            response = self._llm.call(prompt)
            result = json.loads(response)
                        
            # Convert all IDs to strings for consistency
            selected_ids = result.get('selected_question_ids')
            
            # Log the reasoning
            if feedback:
                feedback["value"] = f"Selection reasoning: {result.get('reasoning', 'No reasoning provided')}"
            
            return selected_ids
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse LLM response: {str(e)}"
            if feedback:
                feedback["value"] = error_msg
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error in question selection: {str(e)}"
            if feedback:
                feedback["value"] = error_msg
            raise

    @retry_with_feedback(max_attempts=3, delay=1.0)
    def _generate_llm_report(
        self,
        query: str,
        questions_answers: List[str],
        feedback: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate a comprehensive markdown report using LLM.
        
        Args:
            query: Original search query
            questions_answers: List of question-answer dictionaries
            feedback: Optional feedback dict for retry mechanism
            
        Returns:
            Formatted markdown string
        """
        # Prepare the context for the LLM
        context = questions_answers
        
        
        prompt = f"""
        You are a technical documentation expert creating a comprehensive report from Stack Overflow questions and answers.
        
        TASK:
        Create a detailed, well-structured markdown report based on the following query and Stack Overflow content.
        
        QUERY: {query}
        
        INSTRUCTIONS:
        1. Start with an executive summary of the key findings
        2. For each question:
           - Include the question title and link
           - Provide context about why it's relevant to the query
           - Summarize the best answers
           - Include important code snippets
        3. End with key takeaways and recommendations
        4. Format everything in clean, readable markdown
        5. Include section headers and proper formatting
        6. Ensure all technical details are accurate
        
        STACK OVERFLOW CONTENT:
        {context}
        
        Please generate the report now, focusing on clarity, accuracy, and usefulness for a technical audience.
        """
        
        try:
            report = self._llm.call(prompt)
            return report
        except Exception as e:
            error_msg = f"Failed to generate LLM report (inner error): {str(e)}"
            if feedback:
                feedback["value"] = error_msg
            raise

    @retry_with_feedback(max_attempts=3, delay=1.0)
    def _analyze_brave_results_with_llm(self, results: str, query: str, feedback: Optional[Dict[str, Any]] = None) -> List[str]:
        """Use LLM to analyze and select the most relevant search results."""
        try:
            # Prepare the context for the LLM
            context = results
            
            # Create a properly formatted JSON example
            json_example = json.dumps([
                {
                    "title": "How to run Nginx as non-root user",
                    "reason": "Directly addresses running Nginx with non-root permissions",
                    "relevant": True
                }
            ], indent=4)
            
            prompt = f"""
            You are an expert at analyzing technical search results. Your task is to identify the most relevant Stack Overflow questions from the search results based on the user's query.
            
            USER QUERY: {query}
            
            SEARCH RESULTS:
            {context}
            
            INSTRUCTIONS:
            1. Carefully analyze each result and its relevance to the query
            2. Identify the most relevant Stack Overflow question titles
            3. For each selected title, provide a brief reason for its relevance
            4. Return a JSON array of objects with 'title', 'reason' fields

            IMPORTANT:
            The title is after at "Title: some_text - " and before "- Stack Overflow"
            for example and the extraction must exclude especial characters:
                for 'Title: python - Catching a 500 server error in Flask - Stack Overflow' 
                the title is 'Catching a 500 server error in Flask'

                for 'Title: Problem about 500 Internal Server Error in Python Flask - Stack Overflow'
                the title is 'Problem about 500 Internal Server Error in Python Flask'

                for 'Title: python - (500 Internal Server Error])Flask Post request is causing the server Error [Flask] - Stack Overflow\n'
                the title is '500 Internal Server Error Flask Post request is causing the server Error'

                for '"Openshift Nginx permission problem [nginx: [emerg] mkdir() \"/var/cache/nginx/client_temp\" failed (13: Permission denied)]" - Stack Overflow'
                the title is 'Openshift Nginx permission problem nginx emerg mkdir var cache nginx client_temp failed 13 Permission denied'
                
            
            EXAMPLE RESPONSE:
            {json_example}

            Responed only with the JSON object, do not add any additional text or explanation or a JSON
            str at the begining or end of the response.

            IMPORTANT:
            If feedback is provided, it means that the previous attempt failed and it is retrying.
            <feedback>
            {feedback}
            </feedback>
            """
            
            response = self._llm.call(prompt)

            selected_results = json.loads(response)
           
            final_result = []

            # Return just the titles
            for result in selected_results:
                final_result.append(result['title'])
           
            return final_result
            
        except Exception as e:
            # If LLM analysis fails, fall back to simple title extraction
            raise ValueError(f"Failed to analyze results with LLM: {str(e)}")
    
    def _run(
        self,
        query: str,
        max_questions: int = 20,
        top_answers: int = 3,
        min_answers: int = 1,
    ) -> str:
        """
        Search Stack Overflow and generate a comprehensive report.
        
        Args:
            query: Search query
            max_questions: Maximum number of questions to retrieve and analyze
            top_answers: Number of top answers to retrieve per question
            min_answers: Minimum number of answers a question must have
            
        Returns:
            Markdown formatted report with questions and answers
        """
        feedback = {"value": ""}
        
        try:
            questions_answers = []
            
            # Step 1: Search for relevant questions using preferred method
            try:
                # Use Brave Search to find relevant questions
                search_query = f"{query} site:stackoverflow.com"
                brave_results = self._brave_search._run(search_query=search_query)
                   
                # Get details for each selected question
                for title in self._analyze_brave_results_with_llm(brave_results, query)[:max_questions]:
                    try:
                        stack_questions = self._stack_helper.search_questions(
                            query=title,
                            pages=1,
                            page_size=10,
                            min_answers=min_answers
                        )

                        selected_ids = self._select_relevant_questions(stack_questions, query)

                        for selected_id in selected_ids:
                            # Get full question and answers
                            full_qa = self._stack_helper.get_question_and_answers(
                                question_id=selected_id,
                                answer_limit=top_answers
                            )
                            questions_answers.append(full_qa)
                    except Exception as e:
                        feedback["value"] += f"\nSkipping question '{title}': {str(e)}"
                        continue
            except Exception as e:
                feedback["value"] += f"\nBrave search failed, falling back to direct search: {str(e)}"
            

            if not questions_answers:
                error_msg = "No questions found matching your query."
                if feedback["value"]:
                    error_msg = f"{feedback['value']}\n{error_msg}"
                return error_msg
            
            # Step 2: Generate report
            try:
                return self._generate_llm_report(query, questions_answers, feedback=feedback)
            except Exception as e:
                return f"Failed to generate LLM report (outer error): {str(e)}"
            
        except Exception as e:
            error_msg = f"An error occurred while searching Stack Overflow (outer error): {str(e)}"
            if feedback["value"]:
                error_msg += f"\nAdditional context: {feedback['value']}"
            return error_msg