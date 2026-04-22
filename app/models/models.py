from pydantic import BaseModel


class ContentRequest(BaseModel):
    input_content: str
    max_iterations: int = 3


class PlatformContent(BaseModel):
    content: str
    status: str = "ready"


class MetaInfo(BaseModel):
    iterations: int
    overall_score: float
    approved: bool


class ContentResponse(BaseModel):
    linkedin: PlatformContent
    twitter: PlatformContent
    instagram: PlatformContent
    meta: MetaInfo
