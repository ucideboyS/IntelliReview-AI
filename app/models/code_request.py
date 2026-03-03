from pydantic import BaseModel, Field


class CodeRequest(BaseModel):
    code: str = Field(..., description="The code to be reviewed", min_length=1, max_length=8000)
    language: str = Field(default="Python", description="Programming language of the code")