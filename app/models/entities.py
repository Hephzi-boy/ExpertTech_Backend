from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    posts: Mapped[list["Post"]] = relationship(back_populates="author")
    comments: Mapped[list["Comment"]] = relationship(back_populates="author")
    likes: Mapped[list["Like"]] = relationship(back_populates="user")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    author: Mapped["User"] = relationship(back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    likes: Mapped[list["Like"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    post: Mapped["Post"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="comments")


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_post_like_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    post: Mapped["Post"] = relationship(back_populates="likes")
    user: Mapped["User"] = relationship(back_populates="likes")
