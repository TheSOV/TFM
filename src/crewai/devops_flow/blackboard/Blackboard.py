import os
from pathlib import Path
from pydantic import BaseModel, Field, PrivateAttr
from typing import List, Optional, Dict, Any
from src.crewai.devops_flow.blackboard.utils.Project import Project
from src.crewai.devops_flow.blackboard.utils.Manifest import Manifest
from src.crewai.devops_flow.blackboard.utils.GeneralInfo import GeneralInfo
from src.crewai.devops_flow.blackboard.utils.Record import Record
from src.crewai.devops_flow.blackboard.utils.Issue import Issue
from src.crewai.devops_flow.blackboard.utils.Image import Image
from src.crewai.devops_flow.blackboard.utils.Events import Events
from src.crewai.devops_flow.blackboard.utils.Interaction import Interaction

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
    events: Events = Field(default_factory=Events, exclude=False)
    interaction: Interaction = Field(default_factory=Interaction)
    

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
        self.interaction = Interaction()

    def export_blackboard(
        self,
        *,
        show_advanced_plan: bool = True,
        show_high_issues: bool = True,
        show_medium_issues: bool = False,
        show_low_issues: bool = False,
        show_records: bool = True,
        show_manifests: bool = True,
        last_records: int = 20,
    ) -> dict:
        """
        Returns the blackboard content as a dictionary with filtered and ordered issues.
        
        Args:
            show_advanced_plan: Whether to show the advanced plan in the output
            show_high_issues: Whether to include high severity issues
            show_medium_issues: Whether to include medium severity issues
            show_low_issues: Whether to include low severity issues
            show_records: Whether to include records in the output
            show_manifests: Whether to include manifests in the output
            last_records: If set, include only the most recent N records
            
        Returns:
            dict: The blackboard data with filtered and ordered issues
        """
        # Get the model dump
        # Use JSON mode so datetime objects are serialized as ISO-8601 strings
        data = self.model_dump()
        
        if not show_advanced_plan:
            data['project'].pop('advanced_plan', None)

        # remove events
        data.pop('events', None)

        # remove interaction
        data.pop('interaction', None)

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
        
        # Handle records visibility and trimming
        if not show_records:
            data.pop('records', None)
        else:
            # Trim records list if requested
            if last_records is not None and 'records' in data:
                try:
                    n = int(last_records)
                    if n > 0:
                        data['records'] = data['records'][-n:]
                except (ValueError, TypeError):
                    pass  # ignore invalid values
                    
        # Handle manifests visibility
        if not show_manifests and 'manifests' in data:
            data.pop('manifests', None)

        return data