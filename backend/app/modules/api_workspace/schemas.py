from pydantic import BaseModel, Field, field_validator


class ApiRecordInput(BaseModel):
    name: str = Field(min_length=1,max_length=240)
    method: str = Field(default="GET",max_length=20)
    url: str = Field(min_length=1,max_length=2000)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str,str] = Field(default_factory=dict)

    @field_validator("method")
    @classmethod
    def normalize_method(cls,value:str):
        value=value.upper().strip()
        if value not in {"GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"}:
            raise ValueError("不支持的请求方式")
        return value
