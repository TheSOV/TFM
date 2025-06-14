from pydantic import BaseModel, Field
from typing import Literal

class Record(BaseModel):
    agent: Literal['devops_engineer', 'devops_researcher', 'devops_tester'] = Field(
        ..., 
        description="Agent which completed the task"
    )
    task_name: str = Field(
        ...,
        description="Name of the task completed"
    )
    task_description: str = Field(
        ...,
        description="A description of the task completed, with important information which can be used to complete the next tasks or to debug any failure."
    )
    