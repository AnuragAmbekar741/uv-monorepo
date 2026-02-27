# Monorepo Setup Progress

## Completed Phases

### ✅ Phase 1: Repo Skeleton
```bash
git init
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
mkdir -p services/{api,workers,agents,webhooks}/app packages/shared/shared/{db,dto,messaging} infra/postgres scripts
```

### ✅ Phase 2: Infrastructure (Docker)
```bash
# Start Postgres + Redis
cd infra
docker compose up -d
docker compose ps  # Verify running
```

**Folder Structure:**
```
infra/
├── docker-compose.yml     # Services definition
├── postgres/
│   └── init.sql          # Extensions (vector, uuid-ossp)
└── .gitkeep
```

### ✅ Phase 3: Shared Package
```bash
cd packages/shared
uv init --lib
uv add tortoise-orm asyncpg "psycopg[binary,pool]"
uv add pydantic pydantic-settings python-dotenv pytz httpx sentry-sdk
```

**Files Created:**
```
packages/shared/
├── src/shared/
│   ├── __init__.py
│   ├── config.py                  # Settings from .env
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # BaseModel (id, timestamps, soft-delete)
│   │   │   └── users.py           # User model
│   │   ├── repositories/
│   │   │   └── __init__.py
│   │   └── connect.py             # Tortoise ORM config
│   ├── dto/
│   │   └── __init__.py
│   ├── messaging/
│   │   └── __init__.py
│   └── utils/
│       └── __init__.py
├── pyproject.toml
└── uv.lock
```

### ✅ Phase 4: Migrations
```bash
cd packages/shared
uv add aerich tomli-w tomlkit
uv run aerich init -t shared.db.connect.TORTOISE_CONFIG
uv run aerich init-db
uv run aerich upgrade

# Verify tables
docker exec -it infra-postgres-1 psql -U postgres -d monorepo-uv -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"
# Output: basemodel, users, aerich ✓
```

### ✅ Phase 5: FastAPI Service
```bash
cd services/api
uv init
uv add shared --editable ../../packages/shared
uv add fastapi uvicorn gunicorn python-multipart
uv add "strawberry-graphql[fastapi]" aniso8601 aiodataloader
uv add "python-jose[cryptography]" argon2-cffi pyotp authlib

# Test
uv sync
uv run uvicorn app.main:app --reload --port 8000
# Open: http://localhost:8000/graphql
# Query: { ping } → "pong" ✓
```

**Files Created:**
```
services/api/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan, health endpoint
│   └── graphql/
│       ├── __init__.py
│       ├── schema.py              # Strawberry schema (ping query)
│       ├── queries/
│       │   └── __init__.py
│       ├── mutations/
│       │   └── __init__.py
│       └── types/
│           └── __init__.py
├── pyproject.toml
└── uv.lock
```

### ⏳ Phase 6: Workers Service (Basic Setup)
```bash
cd services/workers
uv init
uv add shared --editable ../../packages/shared
uv add "celery[redis]" flower apscheduler cron-descriptor fastapi-mail jinja2
```

**Files Created:**
```
services/workers/
├── app/
│   ├── __init__.py
│   ├── celery_app.py              # Celery config, Redis broker
│   ├── scheduler.py               # Beat schedule definition
│   └── tasks/
│       └── __init__.py
├── pyproject.toml
└── uv.lock
```

---

## Pending Phases

### ⏹️ Phase 6 (Cont): Workers Testing
```bash
# Terminal 1: Start worker
cd services/workers
uv run celery -A app.celery_app worker --loglevel=info -Q default,reminders,emails

# Terminal 2: Start beat scheduler
cd services/workers
uv run celery -A app.scheduler beat --loglevel=info
```

### ⏹️ Phase 7: Agents Service (Quick Init)
```bash
cd services/agents
uv init
uv add shared --editable ../../packages/shared
mkdir -p app && touch app/__init__.py
```

### ⏹️ Phase 8: Webhooks Service (Quick Init)
```bash
cd services/webhooks
uv init
uv add shared --editable ../../packages/shared
mkdir -p app && touch app/__init__.py
```

---

## Testing Commands

**Config loads:**
```bash
cd packages/shared
uv run python -c "from shared.config import settings; print(settings.environment)"
```

**Database connected:**
```bash
cd packages/shared
uv run python -c "from shared.db.models.users import User; print('✓ User model loads')"
```

**API health:**
```bash
curl http://localhost:8000/health
# Output: {"status":"ok"}
```

**GraphQL ping:**
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ ping }"}'
# Output: {"data": {"ping": "pong"}}
```

---

## Environment Setup

**.env file (root):**
```
DATABASE_URL=postgres://postgres:postgres@localhost:5432/monorepo-uv
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development
DEBUG=true
```

---

## Docker Status

```bash
# Check services
docker compose -f infra/docker-compose.yml ps

# Stop services
docker compose -f infra/docker-compose.yml down

# Start services
docker compose -f infra/docker-compose.yml up -d
```

---

## Next Steps

1. ✅ Complete agents/webhooks quick init
2. ⏳ Test workers (celery + beat)
3. ⏳ Create UV workspace config (Phase 8)
4. ⏳ GitLab CI pipelines (Phase 9)
5. 🔄 Commit everything
