from pydantic import BaseModel
from enum import Enum

# Define Enum for action
class ActionEnum(str, Enum):
    RUN = "RUN"
    SUBMIT = "SUBMIT"

# Define Enum for status
class StatusEnum(str, Enum):
    pending = "pending"
    accepted = "accepted"
    wrong_answer = "wrong_answer"
    time_limit_exceeded = "time_limit_exceeded"
    memory_limit_exceeded = "memory_limit_exceeded"
    runtime_error = "runtime_error"
    compilation_error = "compilation_error"

# Define the Submission model
class Submission(BaseModel):
    submission_id: int
    problem_id: int
    user_id: int
    code: str
    language: str
    results: str = None 
    status: StatusEnum = StatusEnum.pending

