import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from src.crewai.devops_flow.blackboard.utils.Project import Project
from src.crewai.devops_flow.blackboard.utils.Manifest import Manifest
from src.crewai.devops_flow.blackboard.utils.GeneralInfo import GeneralInfo
from src.crewai.devops_flow.blackboard.utils.Record import Record
from src.crewai.devops_flow.blackboard.utils.Issue import Issue
from src.crewai.devops_flow.blackboard.utils.Image import Image

## Main State, used to track the progress and results of the DevOps flow execution
class Blackboard(BaseModel):
    """
    Represents the state of the DevOps flow execution.
    Tracks the progress and results of the Kubernetes configuration process.
    """
    # Configure Pydantic model behavior
    # model_config = {
    #     "extra": "allow",  # Allow extra fields
    #     "validate_assignment": True  # Validate when attributes are assigned
    # }
    
    # Define fields with default values
    project: Project = Field(default_factory=lambda: Project())
    general_info: GeneralInfo = Field(default_factory=GeneralInfo)
    manifests: List[Manifest] = []
    images: List[Image] = []
    issues: List[Issue] = []
    records: List[Record] = []
    iterations: int = 0
    phase: str = "Waiting for kickoff"
    
    def __init__(self, user_request: str = "", **data):
        """
        Initialize a Blackboard instance.
        
        Args:
            user_request: The request made by the user in natural language format.
                          Defaults to an empty string for empty initialization.
            **data: Additional data for the model.
        """
        # Initialize with default values
        super().__init__(**data)
        
        # Set project with user_request if provided
        if user_request:
            self.project = Project(user_request=user_request)

    def reset(self) -> None:
        """
        Resets the blackboard to its initial state.
        """
        self.project = Project()  # Re-initialize project
        self.general_info = GeneralInfo()  # Re-initialize general info
        self.manifests = []
        self.images = []
        self.issues = []
        self.records = []
        self.iterations = 0
        self.phase = "Waiting for kickoff"

    def export_blackboard(
        self,
        *,
        hide_advanced_plan: bool = True,
        hide_basic_plan: bool = False,
        show_high_issues: bool = True,
        show_medium_issues: bool = False,
        show_low_issues: bool = False,
        last_records: int = 20,
    ) -> dict:
        """
        Returns the blackboard content as a dictionary with filtered and ordered issues.
        
        Args:
            hide_advanced_plan: Whether to hide the advanced plan from the output
            hide_basic_plan: Whether to hide the basic plan from the output
            show_high_issues: Whether to include high severity issues
            show_medium_issues: Whether to include medium severity issues
            show_low_issues: Whether to include low severity issues
            last_records: If set, include only the most recent N records
            
        Returns:
            dict: The blackboard data with filtered and ordered issues
        """
        # Get the model dump
        data = self.model_dump()
        
        if hide_advanced_plan:
            data['project'].pop('advanced_plan', None)
        
        if hide_basic_plan:
            data['project'].pop('basic_plan', None)
        
        # Filter and order issues by severity
        if 'issues' in data:
            severity_order = {
                'HIGH': 0,
                'MEDIUM': 1,
                'LOW': 2
            }
            
            filtered_issues = []
            for issue in data['issues']:
                severity = issue.get('severity', 'LOW')
                if (severity == 'HIGH' and show_high_issues) or \
                   (severity == 'MEDIUM' and show_medium_issues) or \
                   (severity == 'LOW' and show_low_issues):
                    filtered_issues.append(issue)
            
            # Sort issues by severity (HIGH > MEDIUM > LOW)
            data['issues'] = sorted(
                filtered_issues,
                key=lambda x: severity_order.get(x.get('severity', 'LOW'), 2)
            )
        
        # Trim records list if requested
        if last_records is not None and 'records' in data:
            try:
                n = int(last_records)
                if n > 0:
                    data['records'] = data['records'][-n:]
            except (ValueError, TypeError):
                pass  # ignore invalid values

        return data