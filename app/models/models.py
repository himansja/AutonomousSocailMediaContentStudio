from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


class ContentRequest(BaseModel):
    # At least one of input_content, source_url, or uploaded_file_path must be provided
    input_content: Optional[str] = None
    max_iterations: int = 3
    source_url: Optional[str] = None
    uploaded_file_path: Optional[str] = None

    @field_validator("input_content", "source_url", "uploaded_file_path", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        """Treat blank strings as absent so Swagger placeholder values are ignored."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @model_validator(mode="after")
    def check_at_least_one_source(self) -> "ContentRequest":
        if not any([self.input_content, self.source_url, self.uploaded_file_path]):
            raise ValueError(
                "At least one of 'input_content', 'source_url', or "
                "'uploaded_file_path' must be provided."
            )
        return self


class PlatformContent(BaseModel):
    content: str
    status: str = "ready"


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


class MetaInfo(BaseModel):
    iterations: int
    overall_score: float
    approved: bool
    token_usage: TokenUsage = TokenUsage()


class ContentResponse(BaseModel):
    linkedin: PlatformContent
    twitter: PlatformContent
    instagram: PlatformContent
    meta: MetaInfo
