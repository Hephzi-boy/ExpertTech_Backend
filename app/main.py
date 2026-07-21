from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Comment, Post, User
from app.realtime import feed_events
from app.routes import posts_router
from app.schemas import HealthResponse


def seed_data() -> None:
    with SessionLocal() as db:
        has_users = db.scalar(select(User.id).limit(1))
        if has_users is not None:
            return

        users = [
            User(username="ada", display_name="Ada Lovelace"),
            User(username="grace", display_name="Grace Hopper"),
            User(username="linus", display_name="Linus Torvalds"),
        ]
        db.add_all(users)
        db.flush()

        posts = [
            Post(
                user_id=users[0].id,
                content="Shipping the first version of the feed API today.",
                image_url=None,
            ),
            Post(
                user_id=users[1].id,
                content="Database schema is in place. Next stop: comments and likes.",
                image_url=None,
            ),
            Post(
                user_id=users[2].id,
                content="Frontend can call this backend directly once CORS is enabled.",
                image_url="https://images.unsplash.com/photo-1518770660439-4636190af475",
            ),
        ]
        db.add_all(posts)
        db.flush()

        comments = [
            Comment(
                post_id=posts[0].id,
                user_id=users[1].id,
                content="Looks good. Add pagination before the frontend integration.",
            ),
            Comment(
                post_id=posts[1].id,
                user_id=users[2].id,
                content="A websocket event for likes would be a nice extra.",
            ),
        ]
        db.add_all(comments)
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_data()
    yield


app = FastAPI(
    title="Tech Assess Backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts_router)


@app.api_route("/", methods=["GET", "HEAD"], response_model=HealthResponse)
def home() -> HealthResponse:
    return HealthResponse(message="Backend is working!")


@app.websocket("/ws/feed")
async def feed_socket(websocket: WebSocket) -> None:
    await feed_events.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        feed_events.disconnect(websocket)
