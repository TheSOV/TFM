"""
YAML Coding Agent for CrewAI

This agent is responsible for creating, editing, and reading YAML configuration files using the CrewAI YAML editor tools.
"""
from typing import List, Dict, Any, Optional
from crewai import Agent
from dependency_injector.wiring import inject, Provide

from src.crewai.tools.yaml_editor_tools import (
    YamlCreateTool,
    YamlEditTool,
    YamlReadTool,
)

from src.crewai.tools.rag_tool import RagTool

class YamlCodingAgent(Agent):
    """
    CrewAI Agent responsible for managing YAML files in the CrewAI project.
    Provides methods to create, edit, and read YAML files using CrewAI tools.
    Uses dependency injection for tool management.
    """

    @inject
    def __init__(
        self,
        create_tool: YamlCreateTool = Provide["yaml_create_tool"],
        edit_tool: YamlEditTool = Provide["yaml_edit_tool"],
        read_tool: YamlReadTool = Provide["yaml_read_tool"],
        rag_tool: RagTool = Provide["rag_tool"],
        llm = "openai/gpt-4.1-mini",
        function_calling_llm = "openai/gpt-4.1-nano",
        **kwargs
    ) -> None:
        """
        Initialize the YAML coding agent with injected YAML tools.
        """
        super().__init__(
            role="YAML Coding Agent",
            goal="Efficiently manage YAML configuration files for the CrewAI project.",
            backstory="A specialized agent with expertise in YAML file creation, editing, and reading, ensuring configuration consistency and automation.",
            tools=[create_tool, edit_tool, read_tool, rag_tool],
            llm=llm,
            function_calling_llm=function_calling_llm,
            **kwargs
        )
       