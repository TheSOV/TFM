from pydantic import BaseModel, Field


class Project(BaseModel):
    """Represents a project or objective in the DevOps flow.
    
    Attributes:
        user_request: The request made by the user in natural language format.
        project_basic_plan: The basic plan of the project.
        project_advanced_plan: The advanced plan of the project.
    """
    user_request: str = Field(
        default="",
        description="The request made by the user, in a natural language format"
    )

    basic_plan: str | None = Field(
        default=None,
        description="The basic plan of the project"
    )

    advanced_plan: str | None = Field(
        default=None,
        description="The advanced plan of the project"
    )
    
