# Monorepo Setup Plan

> **Stack:** uv · FastAPI · Strawberry GraphQL · Tortoise ORM · Celery · LangGraph · PydanticAI · PostgreSQL + pgvector · Redis  
> **Approach:** Shared lib first → API layer → Agentic layer  
> **Rules:** Do each phase fully before moving to the next. Verify each checkpoint before continuing.

---

## Prerequisites

Before touching any code confirm these are installed and working.

- [ ] **Python 3.12+** — `python --version`
- [ ] **uv** — `uv --version` — install from [docs.astral.sh/uv](https://docs.astral.sh/uv)
- [ ] **Docker Desktop** — `docker --version` — needed for Postgres + Redis
- [ ] **Git** — `git --version`
- [ ] **A Postgres client** — TablePlus, DBeaver, or pgAdmin — to inspect your DB visually

---

## Phase 1 — Repo Skeleton

> Goal: Empty but correctly structured repo committed to Git.

### Steps

1. Create your root project folder and `cd` into it
   ```
   mkdir my-project && cd my-project
   ```

2. Initialise git
   ```
   git init
   ```

3. Create the full folder structure — create each of these as empty directories
   ```
   services/api/app/
   services/workers/app/
   services/agents/app/
   services/webhooks/app/
   packages/shared/shared/db/models/
   packages/shared/shared/db/repositories/
   packages/shared/shared/dto/
   packages/shared/shared/messaging/
   infra/postgres/
   scripts/
   .github/workflows/
   ```

4. Create a root `pyproject.toml` — tooling config only, no dependencies
   ```toml
   [tool.ruff]
   line-length = 120
   target-version = "py312"
   select = ["E", "F", "I", "UP"]
   exclude = [".git", "__pycache__", "migrations", ".venv"]

   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   log_cli_format = "%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)"

   [tool.bandit]
   skips = ["B101", "B311", "B110"]
   ```

5. Create `.gitignore` at the root
   ```
   .venv/
   __pycache__/
   *.pyc
   *.pyo
   .env
   dist/
   build/
   *.egg-info/
   .coverage
   .pytest_cache/
   .ruff_cache/
   ```

6. Create `.env.example` at the root
   ```
   # Database
   DATABASE_URL=postgres://postgres:postgres@localhost:5432/myproject

   # Redis
   REDIS_URL=redis://localhost:6379/0

   # Twilio / Sendify
   TWILIO_ACCOUNT_SID=
   TWILIO_AUTH_TOKEN=
   TWILIO_FROM_NUMBER=

   # Auth
   JWT_SECRET_KEY=
   JWT_ALGORITHM=HS256
   JWT_EXPIRE_MINUTES=60

   # Google OAuth
   GOOGLE_CLIENT_ID=
   GOOGLE_CLIENT_SECRET=

   # Firebase
   FIREBASE_CREDENTIALS_PATH=

   # Stripe
   STRIPE_SECRET_KEY=
   STRIPE_WEBHOOK_SECRET=

   # AWS S3
   AWS_ACCESS_KEY_ID=
   AWS_SECRET_ACCESS_KEY=
   AWS_BUCKET_NAME=
   AWS_REGION=

   # LLM
   ANTHROPIC_API_KEY=
   OPENAI_API_KEY=

   # Sentry
   SENTRY_DSN=

   # App
   ENVIRONMENT=development
   DEBUG=true
   ```

7. Copy `.env.example` to `.env` and fill in values you have locally

8. Create a root `README.md` with the project name and a one-liner

9. Commit everything
   ```
   git add .
   git commit -m "chore: repo skeleton"
   ```

### Checkpoint ✓
- [ ] Folder structure exists
- [ ] `.env` is gitignored, `.env.example` is committed
- [ ] First commit is clean

---

## Phase 2 — Infra (Postgres + Redis)

> Goal: Postgres with pgvector and Redis running locally via Docker.

### Steps

1. Create `infra/postgres/init.sql`
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   ```

2. Create `infra/docker-compose.yml` — just Postgres and Redis for now, no app services yet
   ```yaml
   services:
     postgres:
       image: pgvector/pgvector:pg16
       environment:
         POSTGRES_DB: myproject
         POSTGRES_USER: postgres
         POSTGRES_PASSWORD: postgres
       volumes:
         - postgres_data:/var/lib/postgresql/data
         - ./postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
       ports:
         - "5432:5432"

     redis:
       image: redis:7-alpine
       ports:
         - "6379:6379"

   volumes:
     postgres_data:
   ```

3. Start the services
   ```
   cd infra
   docker compose up -d
   ```

4. Confirm Postgres is running — open your Postgres client and connect with:
   - Host: `localhost`
   - Port: `5432`
   - Database: `myproject`
   - User: `postgres`
   - Password: `postgres`

5. Confirm pgvector extension exists — run this query in your client
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```

6. Confirm Redis is running
   ```
   docker exec -it infra-redis-1 redis-cli ping
   # Expected output: PONG
   ```

### Checkpoint ✓
- [ ] Postgres reachable on localhost:5432
- [ ] pgvector extension confirmed
- [ ] Redis returns PONG

---

## Phase 3 — packages/shared

> Goal: Shared library installable by all services, with DB connection working.  
> This is the most important phase — get it solid before touching any service.

### Steps

#### 3.1 Initialise the package

1. `cd packages/shared`

2. Initialise with uv
   ```
   uv init --lib
   ```
   This creates `pyproject.toml`, `src/` layout, and a default `__init__.py`

3. Rename the generated `src/shared/` to match your structure — uv's `--lib` flag creates a `src` layout. Adjust so your import paths are `from shared.config import settings`

4. Add all shared dependencies
   ```
   uv add tortoise-orm asyncpg aerich "psycopg[binary,pool]"
   uv add pydantic pydantic-settings python-dotenv pytz httpx
   uv add twilio sentry-sdk
   ```

#### 3.2 Create the config

Create `shared/config.py`
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    anthropic_api_key: str = ""
    openai_api_key: str = ""

    sentry_dsn: str = ""
    environment: str = "development"
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

#### 3.3 Create the base model

Create `shared/db/models/__init__.py` — empty  
Create `shared/db/models/base.py`
```python
import uuid
from tortoise import fields
from tortoise.models import Model

class BaseModel(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    is_deleted = fields.BooleanField(default=False)

    class Meta:
        abstract = True
```

#### 3.4 Create DB connection

Create `shared/db/connect.py`
```python
from tortoise import Tortoise
from shared.config import settings

TORTOISE_CONFIG = {
    "connections": {"default": settings.database_url},
    "apps": {
        "models": {
            "models": [
                "shared.db.models.users",
                "shared.db.models.communities",
                "shared.db.models.events",
                "shared.db.models.reminders",
                "shared.db.models.surveys",
                "aerich.models",
            ],
            "default_connection": "default",
        }
    },
}

async def init_db():
    await Tortoise.init(config=TORTOISE_CONFIG)

async def close_db():
    await Tortoise.close_connections()
```

#### 3.5 Create your first real models

Create these files — start minimal, add fields as you build features:

`shared/db/models/users.py`
```python
from tortoise import fields
from .base import BaseModel

class User(BaseModel):
    email = fields.CharField(max_length=255, unique=True)
    phone = fields.CharField(max_length=20, null=True)
    password_hash = fields.CharField(max_length=255, null=True)
    is_active = fields.BooleanField(default=True)
    is_verified = fields.BooleanField(default=False)

    class Meta:
        table = "users"
```

`shared/db/models/communities.py`
```python
from tortoise import fields
from .base import BaseModel

class Community(BaseModel):
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    owner = fields.ForeignKeyField("models.User", related_name="owned_communities")

    class Meta:
        table = "communities"
```

`shared/db/models/events.py`
```python
from tortoise import fields
from .base import BaseModel
from enum import StrEnum

class EventStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"

class Event(BaseModel):
    title = fields.CharField(max_length=255)
    location = fields.CharField(max_length=255, null=True)
    venue = fields.CharField(max_length=255, null=True)
    is_ticketed = fields.BooleanField(default=False)
    is_members_only = fields.BooleanField(default=False)
    starts_at = fields.DatetimeField()
    ends_at = fields.DatetimeField(null=True)
    status = fields.CharEnumField(EventStatus, default=EventStatus.DRAFT)
    community = fields.ForeignKeyField("models.Community", related_name="events")

    class Meta:
        table = "events"
        indexes = [("community_id", "starts_at")]
```

`shared/db/models/reminders.py`
```python
from tortoise import fields
from .base import BaseModel
from enum import StrEnum

class ReminderStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Reminder(BaseModel):
    user = fields.ForeignKeyField("models.User", related_name="reminders")
    event = fields.ForeignKeyField("models.Event", related_name="reminders", null=True)
    message = fields.TextField()
    remind_at = fields.DatetimeField()
    status = fields.CharEnumField(ReminderStatus, default=ReminderStatus.PENDING)
    celery_task_id = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "reminders"
        indexes = [("status", "remind_at")]
```

`shared/db/models/surveys.py`
```python
from tortoise import fields
from .base import BaseModel
from enum import StrEnum

class SurveyStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"

class Survey(BaseModel):
    title = fields.CharField(max_length=255)
    questions = fields.JSONField()
    community = fields.ForeignKeyField("models.Community", related_name="surveys")
    status = fields.CharEnumField(SurveyStatus, default=SurveyStatus.DRAFT)
    scheduled_at = fields.DatetimeField(null=True)
    closes_at = fields.DatetimeField(null=True)

    class Meta:
        table = "surveys"

class SurveyResponse(BaseModel):
    survey = fields.ForeignKeyField("models.Survey", related_name="responses")
    user = fields.ForeignKeyField("models.User", related_name="survey_responses")
    answers = fields.JSONField()

    class Meta:
        table = "survey_responses"
        unique_together = (("survey_id", "user_id"),)
```

#### 3.6 Create stub repositories

Create empty stub files for now — fill in methods as you build each feature:

`shared/db/repositories/__init__.py` — empty  
`shared/db/repositories/user_repo.py`
```python
from shared.db.models.users import User

class UserRepository:
    async def get_by_id(self, user_id: str) -> User | None:
        return await User.get_or_none(id=user_id, is_deleted=False)

    async def get_by_email(self, email: str) -> User | None:
        return await User.get_or_none(email=email, is_deleted=False)

    async def create(self, email: str, password_hash: str) -> User:
        return await User.create(email=email, password_hash=password_hash)
```

`shared/db/repositories/event_repo.py`
```python
from shared.db.models.events import Event

class EventRepository:
    async def get_by_id(self, event_id: str) -> Event | None:
        return await Event.get_or_none(id=event_id, is_deleted=False)
```

#### 3.7 Verify shared installs cleanly

From inside `packages/shared`:
```
uv sync
uv run python -c "from shared.config import settings; print(settings.environment)"
uv run python -c "from shared.db.models.base import BaseModel; print('models ok')"
```

Both should print without errors.

### Checkpoint ✓
- [ ] `uv sync` runs without errors in packages/shared
- [ ] Config imports cleanly
- [ ] Models import cleanly
- [ ] All 5 model files exist

---

## Phase 4 — Migrations

> Goal: All model tables created in your local Postgres via Aerich.

### Steps

1. Aerich is configured from `services/api` but its migration files live in `packages/shared`. First create the aerich config — you'll add this to `services/api/pyproject.toml` in Phase 5, but set it up here to run your first migration.

2. Create a temporary `aerich.ini` in `packages/shared` for init only
   ```ini
   [aerich]
   tortoise_orm = shared.db.connect.TORTOISE_CONFIG
   location = ./shared/db/migrations
   src_folder = .
   ```

3. From `packages/shared`, initialise aerich
   ```
   uv run aerich init -t shared.db.connect.TORTOISE_CONFIG
   uv run aerich init-db
   ```

4. Check your Postgres client — you should see tables:
   - `users`
   - `communities`
   - `events`
   - `reminders`
   - `surveys`
   - `survey_responses`
   - `aerich` (migration tracking table)

5. Every time you add or change a model going forward:
   ```
   uv run aerich migrate --name describe_your_change
   uv run aerich upgrade
   ```

### Checkpoint ✓
- [ ] `aerich init-db` runs without errors
- [ ] All 6 domain tables visible in Postgres client
- [ ] `aerich` tracking table exists
- [ ] Migration file created in `shared/db/migrations/`

---

## Phase 5 — services/api

> Goal: FastAPI + Strawberry GraphQL running, connected to shared DB, first query working.

### Steps

#### 5.1 Initialise the service

1. `cd services/api`

2. Initialise with uv
   ```
   uv init
   ```

3. Add shared as a workspace dependency — in `pyproject.toml` add:
   ```toml
   [tool.uv.workspace]
   members = ["../../packages/shared"]
   ```
   Then add shared as a dependency:
   ```
   uv add shared --editable ../../packages/shared
   ```

4. Add all api dependencies
   ```
   uv add fastapi uvicorn gunicorn python-multipart
   uv add "strawberry-graphql[fastapi]" aniso8601 aiodataloader
   uv add "python-jose[cryptography]" argon2-cffi pyotp authlib
   uv add google-auth google-auth-oauthlib firebase-admin
   uv add stripe boto3 pillow
   uv add fastapi-mail email-validator phonenumbers
   uv add qrcode ua-parser
   uv add opentelemetry-instrumentation-fastapi pyinstrument
   ```

5. Add dev dependencies
   ```
   uv add --dev pytest pytest-asyncio pytest-cov factory-boy faker ruff bandit
   ```

6. Add aerich config to `services/api/pyproject.toml`
   ```toml
   [tool.aerich]
   tortoise_orm = "shared.db.connect.TORTOISE_CONFIG"
   location = "../../packages/shared/shared/db/migrations"
   src_folder = "./."
   ```

#### 5.2 Create the app structure

```
services/api/app/
├── __init__.py
├── main.py
├── core/
│   ├── __init__.py
│   ├── security.py        # JWT encode/decode, password hash/verify
│   └── dependencies.py    # get_current_user FastAPI dep
├── dto/
│   ├── __init__.py
│   └── auth_dto.py        # LoginDTO, RegisterDTO
├── services/
│   ├── __init__.py
│   ├── base.py
│   ├── auth_service.py
│   └── event_service.py
└── graphql/
    ├── __init__.py
    ├── schema.py           # Root schema combining all
    ├── types/
    │   ├── __init__.py
    │   ├── user_type.py
    │   └── event_type.py
    ├── inputs/
    │   ├── __init__.py
    │   └── auth_input.py
    ├── queries/
    │   ├── __init__.py
    │   └── event_queries.py
    └── mutations/
        ├── __init__.py
        └── auth_mutations.py
```

#### 5.3 Create main.py

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from shared.db.connect import init_db, close_db
from app.graphql.schema import schema

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(title="API", lifespan=lifespan)
app.include_router(GraphQLRouter(schema), prefix="/graphql")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

#### 5.4 Wire up a minimal GraphQL schema

Create `app/graphql/schema.py`
```python
import strawberry
from app.graphql.queries.event_queries import EventQuery
from app.graphql.mutations.auth_mutations import AuthMutation

schema = strawberry.Schema(query=EventQuery, mutation=AuthMutation)
```

Create `app/graphql/queries/event_queries.py`
```python
import strawberry
from shared.db.repositories.event_repo import EventRepository

@strawberry.type
class EventQuery:
    @strawberry.field
    async def ping(self) -> str:
        return "pong"
```

#### 5.5 Run it

From `services/api`:
```
uv run uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/graphql` — GraphQL playground should load.

Run the ping query:
```graphql
query {
  ping
}
```

Expected response:
```json
{ "data": { "ping": "pong" } }
```

### Checkpoint ✓
- [ ] `uv sync` in services/api runs without errors
- [ ] `from shared.config import settings` works inside api
- [ ] Server starts on port 8000
- [ ] `/health` returns `{"status": "ok"}`
- [ ] GraphQL playground loads at `/graphql`
- [ ] `ping` query returns `"pong"`

---

## Phase 6 — services/workers

> Goal: Celery worker and beat scheduler running, connected to shared DB.

### Steps

1. `cd services/workers`

2. `uv init`

3. Add shared and dependencies
   ```
   uv add shared --editable ../../packages/shared
   uv add "celery[redis]" flower apscheduler cron-descriptor
   uv add fastapi-mail jinja2
   ```

4. Create `app/celery_app.py`
   ```python
   from celery import Celery
   from celery.signals import worker_init, worker_shutdown
   from shared.config import settings
   import asyncio

   celery_app = Celery(
       "workers",
       broker=settings.redis_url,
       backend=settings.redis_url
   )

   celery_app.conf.task_routes = {
       "tasks.reminders.*": {"queue": "reminders"},
       "tasks.surveys.*":   {"queue": "surveys"},
       "tasks.notifications.*": {"queue": "default"},
   }
   celery_app.conf.timezone = "UTC"

   @worker_init.connect
   def on_start(**_):
       from shared.db.connect import init_db
       asyncio.get_event_loop().run_until_complete(init_db())

   @worker_shutdown.connect
   def on_stop(**_):
       from shared.db.connect import close_db
       asyncio.get_event_loop().run_until_complete(close_db())
   ```

5. Create `app/scheduler.py`
   ```python
   from celery.schedules import crontab
   from app.celery_app import celery_app

   celery_app.conf.beat_schedule = {
       "fire-pending-reminders": {
           "task": "tasks.reminders.fire_pending",
           "schedule": crontab(minute="*/1"),
       },
   }
   ```

6. Create a stub task to verify everything connects
   `app/tasks/reminders.py`
   ```python
   from app.celery_app import celery_app

   @celery_app.task(bind=True, max_retries=3, name="tasks.reminders.fire_pending")
   def fire_pending(self):
       print("reminder task fired")
   ```

7. Start the worker (Redis must be running)
   ```
   uv run celery -A app.celery_app worker --loglevel=info -Q default,reminders,surveys
   ```

8. In a second terminal, start beat
   ```
   uv run celery -A app.celery_app beat --loglevel=info
   ```

### Checkpoint ✓
- [ ] Worker starts without errors
- [ ] Beat starts without errors
- [ ] Beat fires `fire_pending` every minute — visible in worker logs

---

## Phase 7 — services/agents

> Goal: LangGraph and PydanticAI installed, one simple agent working end to end.

### Steps

1. `cd services/agents`

2. `uv init`

3. Add shared and dependencies
   ```
   uv add shared --editable ../../packages/shared
   uv add langgraph langgraph-checkpoint-postgres langchain-postgres langchain-community
   uv add pydantic-ai
   uv add langchain-anthropic langchain-openai
   uv add fastapi uvicorn
   ```

4. Create the folder structure
   ```
   services/agents/app/
   ├── __init__.py
   ├── main.py
   ├── simple/           # PydanticAI — single LLM calls
   │   └── __init__.py
   ├── graphs/           # LangGraph — stateful multi-step agents
   │   └── __init__.py
   ├── tools/            # Shared tools used by both
   │   └── __init__.py
   └── vectorstore/      # pgvector indexing and retrieval
       ├── __init__.py
       ├── indexer.py
       └── retriever.py
   ```

5. Create a simple PydanticAI agent to verify the setup
   `app/simple/classifier.py`
   ```python
   from pydantic import BaseModel
   from pydantic_ai import Agent

   class ClassificationResult(BaseModel):
       category: str
       confidence: float
       reasoning: str

   classifier = Agent(
       "anthropic:claude-3-5-haiku-latest",
       result_type=ClassificationResult,
       system_prompt="Classify the given text into a category."
   )
   ```

6. Create `app/main.py`
   ```python
   from contextlib import asynccontextmanager
   from fastapi import FastAPI
   from shared.db.connect import init_db, close_db

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       await init_db()
       yield
       await close_db()

   app = FastAPI(title="Agents", lifespan=lifespan)

   @app.get("/health")
   async def health():
       return {"status": "ok"}
   ```

7. Run the agents service
   ```
   uv run uvicorn app.main:app --reload --port 8001
   ```

8. Verify the classifier works — create a quick test script `test_classifier.py` in `services/agents`:
   ```python
   import asyncio
   from app.simple.classifier import classifier

   async def main():
       result = await classifier.run("Our event next Friday has been cancelled due to weather")
       print(result.data)

   asyncio.run(main())
   ```
   ```
   uv run python test_classifier.py
   ```

### Checkpoint ✓
- [ ] `uv sync` runs without errors
- [ ] Agents service starts on port 8001
- [ ] `/health` returns ok
- [ ] Classifier agent returns a structured result

---

## Phase 8 — uv Workspace (Tie Everything Together)

> Goal: One `uv sync` from root installs everything. One `docker compose up` runs everything.

### Steps

1. Create a root `pyproject.toml` workspace config
   ```toml
   [tool.uv.workspace]
   members = [
       "packages/shared",
       "services/api",
       "services/workers",
       "services/agents",
       "services/webhooks",
   ]
   ```

2. From the root, run
   ```
   uv sync --all-packages
   ```
   This resolves all dependencies across all services together.

3. Add app services to `infra/docker-compose.yml`
   ```yaml
   api:
     build:
       context: ..
       dockerfile: services/api/Dockerfile
     ports: ["8000:8000"]
     depends_on: [postgres, redis]
     env_file: ../.env

   worker:
     build:
       context: ..
       dockerfile: services/workers/Dockerfile
     command: celery -A app.celery_app worker -l info -Q default,reminders,surveys
     depends_on: [postgres, redis]
     env_file: ../.env

   beat:
     build:
       context: ..
       dockerfile: services/workers/Dockerfile
     command: celery -A app.celery_app beat -l info
     depends_on: [redis]
     env_file: ../.env

   agents:
     build:
       context: ..
       dockerfile: services/agents/Dockerfile
     ports: ["8001:8001"]
     depends_on: [postgres]
     env_file: ../.env
   ```

4. Create a `Dockerfile` for each service — same pattern for all:
   ```dockerfile
   # services/api/Dockerfile
   FROM python:3.12-slim
   WORKDIR /app

   COPY packages/shared /app/packages/shared
   COPY services/api /app/services/api

   WORKDIR /app/services/api
   RUN pip install uv && uv sync --no-dev

   CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

5. Run the full stack
   ```
   cd infra
   docker compose up --build
   ```

### Checkpoint ✓
- [ ] `uv sync --all-packages` from root resolves without conflicts
- [ ] `docker compose up --build` starts all services
- [ ] API reachable at `localhost:8000/graphql`
- [ ] Agents reachable at `localhost:8001/health`
- [ ] Worker and Beat logs show clean startup

---

## Phase 9 — CI/CD

> Goal: GitHub Actions runs tests on every push, scoped per service.

### Steps

1. Create `.github/workflows/shared.yml` — triggers on shared changes, runs tests for all services
   ```yaml
   on:
     push:
       paths: ["packages/shared/**"]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: astral-sh/setup-uv@v3
         - run: cd packages/shared && uv sync && uv run pytest
   ```

2. Create `.github/workflows/api.yml`
   ```yaml
   on:
     push:
       paths:
         - "services/api/**"
         - "packages/shared/**"
   jobs:
     test:
       runs-on: ubuntu-latest
       services:
         postgres:
           image: pgvector/pgvector:pg16
           env: { POSTGRES_PASSWORD: postgres }
           ports: ["5432:5432"]
         redis:
           image: redis:7-alpine
           ports: ["6379:6379"]
       steps:
         - uses: actions/checkout@v4
         - uses: astral-sh/setup-uv@v3
         - run: cd services/api && uv sync && uv run pytest
   ```

3. Repeat `api.yml` pattern for `workers.yml` and `agents.yml` — change paths and run commands

4. Push to GitHub and confirm workflows appear in the Actions tab

5. Make a small change to `packages/shared` and confirm it triggers the shared workflow AND the api workflow

### Checkpoint ✓
- [ ] Workflows visible in GitHub Actions
- [ ] Push to `services/api` triggers only the api workflow
- [ ] Push to `packages/shared` triggers shared + all service workflows
- [ ] At least one test passes in CI

---

## Final Verification — New Engineer Test

Clone the repo fresh into a new directory and try this from scratch:

```bash
git clone <your-repo> fresh-test && cd fresh-test
cp .env.example .env        # fill in values
cd infra && docker compose up -d
cd ../services/api && uv sync
uv run aerich upgrade
uv run uvicorn app.main:app --reload
```

Open `localhost:8000/graphql` — if the playground loads, the setup is solid.

---

## Quick Reference — Commands You'll Use Daily

| Task | Command | Run From |
|---|---|---|
| Start infra | `docker compose up -d` | `infra/` |
| Run api locally | `uv run uvicorn app.main:app --reload` | `services/api/` |
| Run agents locally | `uv run uvicorn app.main:app --reload --port 8001` | `services/agents/` |
| Start celery worker | `uv run celery -A app.celery_app worker -l info` | `services/workers/` |
| Start celery beat | `uv run celery -A app.celery_app beat -l info` | `services/workers/` |
| Create migration | `uv run aerich migrate --name <description>` | `services/api/` |
| Apply migrations | `uv run aerich upgrade` | `services/api/` |
| Add api dependency | `uv add <package>` | `services/api/` |
| Add shared dependency | `uv add <package>` | `packages/shared/` |
| Run tests | `uv run pytest` | any service dir |
| Lint | `uv run ruff check .` | any service dir |
| Full docker stack | `docker compose up --build` | `infra/` |
