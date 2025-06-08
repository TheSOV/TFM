from pydantic import BaseModel, Field
from src.crewai.devops_flow.crews.devops_crew.outputs.outputs import CreateK8sConfigOutput, ImagesDataRetrievalOutput, TestK8sConfigOutput

## Main State, used to track the progress and results of the DevOps flow execution
class MainState(BaseModel):
    """
    Represents the state of the DevOps flow execution.
    Tracks the progress and results of the Kubernetes configuration process.
    """
    # Basic information required for most operations
    task: str | None = Field(
        default=None,
        description="The task or objective to be accomplished by the DevOps flow"
    )
    
    base_information: CreateK8sConfigOutput | None = Field(
        default=None,
        description="Base information required for most operations"
    )

    ## Images data retrieved from the cluster
    images_data: ImagesDataRetrievalOutput | None = Field(
        default=None,
        description="Images data retrieved from the cluster"
    )
    
    ## Results from the apply step
    apply_succeeded: bool = Field(
        default=False,
        description="Indicates whether the last Kubernetes apply operation was successful"
    )
    apply_result: str | None = Field(
        default=None,
        description="Detailed result or error message from the last apply operation"
    )
    
    ## Results from the test step
    cluster_test_result: TestK8sConfigOutput | None = Field(
        default=None,
        description="Results from the test step"
    )