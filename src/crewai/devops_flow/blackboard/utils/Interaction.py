from pydantic import BaseModel, Field
from typing import Literal

class Interaction(BaseModel):
    """
    Represents the state of user interaction for the DevOps flow.
    """
    mode: Literal['automated', 'assisted'] = Field(
        default="assisted",
        description="The interaction mode. 'automated' runs without pauses, 'assisted' waits for user input."
    )
    status: str = Field(
        default="idle",
        description="The current status of the flow, e.g., 'running', 'waiting_for_input:step_name'."
    )
    is_waiting_for_input: bool = Field(default=False)
    message: str = Field(
        default="",
        description="The feedback message provided by the user to guide the next step."
    )
    step_name: str = Field(
        default="",
        description="The name of the step that is currently waiting for user input."
    )
    user_feedback: str = Field(
        default="",
        description="The feedback message provided by the user to guide the next step."
    )
