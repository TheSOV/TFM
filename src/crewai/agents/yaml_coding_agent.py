"""
YAML Coding Agent for CrewAI

This agent is responsible for creating, editing, and reading YAML and general files
using the CrewAI YAML editor tools and File edit tools.
"""
from typing import List, Dict, Any, Optional
from crewai import Agent
from dependency_injector.wiring import inject, Provide

# from src.crewai.tools.yaml_editor_tools import (
#     YamlCreateTool,
#     YamlEditTool,
#     YamlReadTool,
# )

from src.crewai.tools.file_edit_tool import (
    FileCreateTool,
    FileEditTool,
    FileReadTool,
)

from src.crewai.tools.rag_tool import RagTool
from src.crewai.tools.config_validator import ConfigValidatorTool

class YamlCodingAgent(Agent):
    """
    CrewAI Agent responsible for managing YAML files and general files in the CrewAI project.
    Provides methods to create, edit, and read YAML files using CrewAI YAML tools.
    Provides methods to create, edit, and read general files using CrewAI File tools.
    Uses dependency injection for tool management.
    """

    @inject
    def __init__(
        self,
        # create_tool: YamlCreateTool = Provide["yaml_create_tool"],
        # edit_tool: YamlEditTool = Provide["yaml_edit_tool"],
        # read_tool: YamlReadTool = Provide["yaml_read_tool"],
        file_create_tool: FileCreateTool = Provide["file_create_tool"],
        file_edit_tool: FileEditTool = Provide["file_edit_tool"],
        file_read_tool: FileReadTool = Provide["file_read_tool"],
        rag_tool: RagTool = Provide["rag_tool"],
        config_validator_tool: ConfigValidatorTool = Provide["config_validator_tool"],
        llm = "openai/gpt-4.1-mini",
        function_calling_llm = "openai/gpt-4.1-nano",
        **kwargs
    ) -> None:
        """
        Initialize the agent with injected YAML, File Edit, and Config Validator tools.
        
        Args:
            create_tool (YamlCreateTool): Tool for creating YAML files
            edit_tool (YamlEditTool): Tool for editing YAML files
            read_tool (YamlReadTool): Tool for reading YAML files
            file_create_tool (FileCreateTool): Tool for creating general files
            file_edit_tool (FileEditTool): Tool for editing general files with line operations
            file_read_tool (FileReadTool): Tool for reading general files
            rag_tool (RagTool): Tool for RAG-based knowledge retrieval
            config_validator_tool (ConfigValidatorTool): Tool for validating configuration files
            llm (str): The language model to use for the agent
            function_calling_llm (str): The language model to use for function calling
            **kwargs: Additional arguments to pass to the parent class
        """
        # Store YAML tools as instance variables
        # self._create_tool = create_tool
        # self._edit_tool = edit_tool
        # self._read_tool = read_tool
        
        # Store File tools as instance variables
        self._file_create_tool = file_create_tool
        self._file_edit_tool = file_edit_tool
        self._file_read_tool = file_read_tool
        
        # Store other tools
        self._rag_tool = rag_tool
        self._config_validator_tool = config_validator_tool
        
        super().__init__(
            role="YAML and File Management Agent",
            goal=(
                "Efficiently manage and secure YAML configuration files and general text files for the CrewAI project, "
                "with a focus on Kubernetes security best practices and compliance."
            ),
            backstory=(
                "A specialized agent with expertise in YAML and general file management. "
                "Skilled in creating, editing, and validating configurations while ensuring "
                "they adhere to best practices and security standards. "
                "Can perform precise line-by-line operations on any text file."
            ),
            tools=[
                file_create_tool, file_edit_tool, file_read_tool,
                rag_tool, config_validator_tool
            ],
            llm=llm,
            function_calling_llm=function_calling_llm,
            **kwargs
        )
       