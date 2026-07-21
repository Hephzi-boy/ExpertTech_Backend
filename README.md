# Tech Assess Backend

Small FastAPI backend for a social feed with posts, comments, likes, and realtime feed events.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Optional environment setup:

- Copy `.env.example` to `.env`
- Set `DATABASE_URL` if you want Postgres
- If `DATABASE_URL` is not set, the app uses SQLite at `./tech_assess_backend.db`

The app creates tables and seeds sample data on startup.

## Endpoints

- `GET /` or `HEAD /` - health check
- `GET /posts?limit=10&offset=0` - list posts
- `POST /posts/{post_id}/like` - like a post
- `GET /posts/{post_id}/comments?limit=20&offset=0` - list comments for a post
- `POST /posts/{post_id}/comments` - create a comment for a post
- `WS /ws/feed` - websocket for realtime feed events

Swagger docs are available at `/docs`.

## Request bodies

`POST /posts/{post_id}/like`

```json
{
  "user_id": 1
}
```

`POST /posts/{post_id}/comments`

```json
{
  "user_id": 1,
  "content": "Nice update."
}
```

## Schema

Database tables:

- `users`: `id`, `username`, `display_name`, `created_at`
- `posts`: `id`, `user_id`, `content`, `image_url`, `created_at`
- `comments`: `id`, `post_id`, `user_id`, `content`, `created_at`
- `likes`: `id`, `post_id`, `user_id`, `created_at`

Relationships:

- A user has many posts, comments, and likes
- A post belongs to a user and has many comments and likes
- A comment belongs to a post and a user
- A like belongs to a post and a user
- `likes` has a unique constraint on `(post_id, user_id)` so one user can like a post only once

Main API response shapes:

- `UserSummary`: `id`, `username`, `display_name`
- `PostResponse`: `id`, `content`, `image_url`, `created_at`, `author`, `likes_count`, `comments_count`
- `CommentResponse`: `id`, `post_id`, `content`, `created_at`, `author`
- Paginated list responses include: `items`, `limit`, `offset`, `next_offset`, `total`
