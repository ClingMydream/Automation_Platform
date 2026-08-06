from pydantic import BaseModel, Field


class CommandInput(BaseModel):
    category: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=160)
    command: str = Field(min_length=1)
    description: str = ""
    usage_example: str = ""
    interview_note: str = ""
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool = False
