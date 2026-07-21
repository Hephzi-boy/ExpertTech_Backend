from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.cache import feed_cache
from app.database import get_db
from app.models import Comment, Like, Post, User
from app.realtime import feed_events
from app.schemas import (
    CommentCreate,
    CommentResponse,
    LikeCreate,
    MutationResponse,
    PaginatedCommentsResponse,
    PaginatedPostsResponse,
    PostResponse,
    UserSummary,
)

router = APIRouter(prefix="/posts", tags=["posts"])


def _base_post_query() -> Select[tuple[Post, int, int]]:
    likes_subquery = (
        select(Like.post_id, func.count(Like.id).label("likes_count"))
        .group_by(Like.post_id)
        .subquery()
    )
    comments_subquery = (
        select(Comment.post_id, func.count(Comment.id).label("comments_count"))
        .group_by(Comment.post_id)
        .subquery()
    )

    return (
        select(
            Post,
            func.coalesce(likes_subquery.c.likes_count, 0),
            func.coalesce(comments_subquery.c.comments_count, 0),
        )
        .options(joinedload(Post.author))
        .outerjoin(likes_subquery, likes_subquery.c.post_id == Post.id)
        .outerjoin(comments_subquery, comments_subquery.c.post_id == Post.id)
        .order_by(Post.created_at.desc(), Post.id.desc())
    )


def _serialize_post(post: Post, likes_count: int, comments_count: int) -> PostResponse:
    return PostResponse(
        id=post.id,
        content=post.content,
        image_url=post.image_url,
        created_at=post.created_at,
        author=UserSummary.model_validate(post.author),
        likes_count=likes_count,
        comments_count=comments_count,
    )


def _get_post_or_404(db: Session, post_id: int) -> Post:
    post = (
        db.execute(select(Post).options(joinedload(Post.author)).where(Post.id == post_id))
        .unique()
        .scalar_one_or_none()
    )
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("", response_model=PaginatedPostsResponse)
def list_posts(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedPostsResponse:
    cache_key = f"posts:{limit}:{offset}"
    cached = feed_cache.get(cache_key)
    if cached is not None:
        return cached

    total = db.scalar(select(func.count()).select_from(Post)) or 0
    rows = db.execute(_base_post_query().limit(limit).offset(offset)).unique().all()
    items = [_serialize_post(post, likes_count, comments_count) for post, likes_count, comments_count in rows]
    next_offset = offset + limit if offset + limit < total else None

    response = PaginatedPostsResponse(
        items=items,
        limit=limit,
        offset=offset,
        next_offset=next_offset,
        total=total,
    )
    feed_cache.set(cache_key, response)
    return response


@router.post("/{post_id}/like", response_model=MutationResponse)
async def like_post(
    post_id: int,
    payload: LikeCreate,
    db: Session = Depends(get_db),
) -> MutationResponse:
    _get_post_or_404(db, post_id)
    _get_user_or_404(db, payload.user_id)

    like = Like(post_id=post_id, user_id=payload.user_id)
    db.add(like)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already liked this post",
        ) from None

    feed_cache.clear()

    likes_count = db.scalar(select(func.count()).select_from(Like).where(Like.post_id == post_id)) or 0
    await feed_events.broadcast(
        "post_liked",
        {"post_id": post_id, "user_id": payload.user_id, "likes_count": likes_count},
    )
    return MutationResponse(message="Post liked successfully")


@router.get("/{post_id}/comments", response_model=PaginatedCommentsResponse)
def list_comments(
    post_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedCommentsResponse:
    _get_post_or_404(db, post_id)

    total = db.scalar(
        select(func.count()).select_from(Comment).where(Comment.post_id == post_id)
    ) or 0

    comments = (
        db.execute(
            select(Comment)
            .options(joinedload(Comment.author))
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
            .limit(limit)
            .offset(offset)
        )
        .unique()
        .scalars()
        .all()
    )

    items = [
        CommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            content=comment.content,
            created_at=comment.created_at,
            author=UserSummary.model_validate(comment.author),
        )
        for comment in comments
    ]

    next_offset = offset + limit if offset + limit < total else None
    return PaginatedCommentsResponse(
        items=items,
        limit=limit,
        offset=offset,
        next_offset=next_offset,
        total=total,
    )


@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    post_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
) -> CommentResponse:
    _get_post_or_404(db, post_id)
    user = _get_user_or_404(db, payload.user_id)
    content = payload.content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Comment content cannot be blank",
        )

    comment = Comment(post_id=post_id, user_id=payload.user_id, content=content)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    feed_cache.clear()

    await feed_events.broadcast(
        "comment_created",
        {
            "post_id": post_id,
            "comment_id": comment.id,
            "user_id": payload.user_id,
        },
    )
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        content=comment.content,
        created_at=comment.created_at,
        author=UserSummary.model_validate(user),
    )
