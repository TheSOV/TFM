import datetime
from typing import Any
from pydantic import BaseModel, Field
from typing import Literal

SEVERITY_LOW: str = "LOW"
SEVERITY_MEDIUM: str = "MEDIUM"
SEVERITY_HIGH: str = "HIGH"
SEVERITY_TYPE = Literal[SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH]


class Issue(BaseModel):
    """Represents a problem detected during the DevOps flow.

    The class extends Pydantic's ``BaseModel`` to provide validation and
    automatic documentation generation.
    timestamp is stored as a ``datetime`` object (UTC). When the model is
    serialised (``mode="json"``), it is automatically converted to an
    ISO-8601 string thanks to the custom ``json_encoders`` defined below.
    """
    issue: str = Field(..., description="Brief and ilustrative title of the issue")
    severity: SEVERITY_TYPE = Field(..., description=f"Severity of the issue (must be one of: {SEVERITY_TYPE}).")
    problem_description: str = Field(..., description="Complete description of the issue, with all the details and context")
    possible_manifest_file_path: str = Field(..., description="Path to the manifest file that might be the cause of the issue")
    observations: str = Field(..., description="Any additional observations or comments")
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"),
        description="Time when the issue was created (HH:MM:SS UTC)"
    )