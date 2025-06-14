from typing import Literal
from pydantic import BaseModel, Field
from typing import List

class GeneralInfo(BaseModel):
    """Represents general information about the Kubernetes cluster.
    
    Attributes:
        namespaces: The namespaces of the cluster.
    """
    namespaces: List[str] = Field(default=[], description="Namespaces of the cluster")
