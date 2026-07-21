from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserSummary(BaseModel):
    id: int
    username: str
    display_name: str

    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    user_id: int = Field(gt=0)
    content: str = Field(min_length=1, max_length=500)


class LikeCreate(BaseModel):
    user_id: int = Field(gt=0)


class CommentResponse(BaseModel):
    id: int
    post_id: int
    content: str
    created_at: datetime
    author: UserSummary

    model_config = ConfigDict(from_attributes=True)


class PostResponse(BaseModel):
    id: int
    content: str
    image_url: str | None
    created_at: datetime
    author: UserSummary
    likes_count: int
    comments_count: int

    model_config = ConfigDict(from_attributes=True)


class PaginatedPostsResponse(BaseModel):
    items: list[PostResponse]
    limit: int
    offset: int
    next_offset: int | None
    total: int


class PaginatedCommentsResponse(BaseModel):
    items: list[CommentResponse]
    limit: int
    offset: int
    next_offset: int | None
    total: int


class MutationResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    message: str
