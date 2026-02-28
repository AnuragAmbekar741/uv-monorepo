# Monorepo Development Rules

## 1. Dependency Management (UV Workspace)

### 🎯 Golden Rule: Add Dependencies in SERVICE Directory, NOT Root

```bash
# ✅ CORRECT: Add to the service you're working on
cd services/agents              # Navigate to your service
uv add langchain openai         # Adds to services/agents/pyproject.toml

# ❌ WRONG: Don't add to root
cd /path/to/uv-monorepo
uv add langchain                # ✗ This adds to root (incorrect!)
```

### Root `pyproject.toml` is for Workspace Config ONLY
```toml
# Root pyproject.toml has:
[project]
name = "uv-monorepo"            # ← Workspace name

[tool.uv.workspace]
members = [                      # ← All services listed
    "packages/shared",
    "services/api",
    "services/workers",
    "services/agents",
    "services/webhooks",
]

[tool.ruff]                      # ← Tool configs only
[tool.pytest.ini_options]
```

### ✅ When to run `uv sync`
```bash
# RUN uv sync if you:
# ✓ Added a new dependency to any service/package
# ✓ Removed a dependency
# ✓ Modified pyproject.toml versions

# Command (from root):
cd /path/to/uv-monorepo
uv sync
```

### ❌ When NOT to run `uv sync`
```bash
# SKIP uv sync if you:
# ✗ Only added/modified code files
# ✗ Only added new modules (models, services, etc.)
# ✗ Only updated GraphQL schema
```

### Complete Workflow: Adding Dependencies to a Service

**Example: Working on Agents Service**
```bash
# 1. Navigate to the service directory (NOT root)
cd services/agents

# 2. Add your dependencies
uv add langchain openai pinecone-client

# 3. Verify what was added
cat pyproject.toml
# Output shows:
# [project]
# name = "agents"
# dependencies = [
#     "langchain",
#     "openai",
#     "pinecone-client",
#     "shared",  # ← Already references shared
# ]

# 4. Go back to root
cd ../../

# 5. Sync workspace (updates uv.lock)
uv sync

# 6. Check what changed
git status
# Modified: services/agents/pyproject.toml
# Modified: uv.lock  ← Only this updates from uv sync

# 7. Lint and commit
uv run ruff check --fix .
uv run ruff format .
git add .
git commit -m "feat(agents): add langchain and openai integration"
```

### Per-Service Examples

| Service | Dependencies | Command |
|---------|--------------|---------|
| **Agents** | `langchain, openai` | `cd services/agents && uv add langchain openai` |
| **API** | `fastapi, strawberry-graphql` | `cd services/api && uv add fastapi` |
| **Workers** | `celery, redis` | `cd services/workers && uv add celery redis` |
| **Webhooks** | `httpx` | `cd services/webhooks && uv add httpx` |
| **Shared** | `pydantic, tortoise-orm` | `cd packages/shared && uv add pydantic` |

### Commit Checklist
```bash
# 1. Check what changed
git status

# 2. If uv.lock was modified → dependencies changed
#    If uv.lock NOT modified → only code changed

# 3. Add everything
git add .

# 4. Commit with appropriate message
git commit -m "feat(module-name): description"
```

---

## 2. Module Architecture (Layered Pattern)

### Standard Module Structure
```
When adding a new feature/module (e.g., events):

packages/shared/src/shared/
├── events/                      # New module
│   ├── __init__.py
│   ├── models.py               # Database models (Tortoise ORM)
│   ├── repositories.py         # Data access layer (abstract + concrete)
│   ├── dto.py                  # Data Transfer Objects (Pydantic)
│   ├── services.py             # Business logic (extends BaseService)
│   └── enums.py                # Constants/enums (if needed)

services/{api,workers,agents}/app/
├── graphql/mutations/events.py # API mutations (API service only)
├── services/events.py          # Service-specific logic (if needed)
└── tasks/events.py             # Async tasks (Workers service only)
```

### Layer Responsibilities

| Layer | Location | Responsibility | Example |
|-------|----------|-----------------|---------|
| **Models** | `shared.{module}.models` | Database schema | `Event`, `EventLog` |
| **Repositories** | `shared.{module}.repositories` | Data access (CRUD) | `EventRepository.find_by_id()` |
| **DTOs** | `shared.{module}.dto` | API contracts | `EventCreateDTO`, `EventResponseDTO` |
| **Services** | `shared.{module}.services` | Business logic | `EventService.create_event()` |
| **Enums** | `shared.{module}.enums` | Constants | `EventStatus`, `EventType` |
| **GraphQL** | `services/api/app/graphql/` | API layer | Mutations, Queries, Types |
| **Tasks** | `services/workers/app/tasks/` | Background jobs | Celery tasks |

---

## 3. Shared Package Rules

### What MUST go in `packages/shared/`
- ✅ Database models
- ✅ Repository interfaces and implementations
- ✅ DTOs (Pydantic models)
- ✅ Base/abstract service classes
- ✅ Enums and constants
- ✅ Exceptions
- ✅ Configuration
- ✅ Utilities used by multiple services

### What MUST NOT go in `packages/shared/`
- ❌ Service-specific business logic
- ❌ API route handlers
- ❌ Celery task implementations
- ❌ GraphQL mutations/queries
- ❌ Web framework code (FastAPI, etc.)

---

## 4. Git Commit Workflow

### Before Every Commit
```bash
# 1. Check for new dependencies
git status | grep uv.lock

# 2. If uv.lock changed, run sync
# If uv.lock NOT changed, skip to step 3

uv sync

# 3. Run linting/formatting
uv run ruff check --fix .     # Lint + fix
uv run ruff format .          # Format code

# 4. Run tests (if applicable)
# uv run pytest

# 5. Stage changes
git add .

# 6. Commit
git commit -m "type(scope): description"
```

### Commit Message Format
```
feat(events): add event creation and tracking system
fix(api): resolve null pointer in user service
refactor(shared): simplify repository base class
docs(setup): update workspace configuration
test(events): add event service unit tests

Format: type(scope): description
Types: feat, fix, refactor, docs, test, chore, ci
Scope: module name (events, users, auth, etc.)
```

---

## 5. Workspace Dependency Rules

### Referencing Shared Package
```toml
# In any service's pyproject.toml:

[project]
dependencies = [
    "shared",      # ← Add shared as dependency
    "fastapi",
]

[tool.uv.sources]
shared = { workspace = true, editable = true }  # ← This line is required
```

### When to Add to Shared vs Service

**ADD TO SHARED:**
```bash
cd packages/shared
uv add pydantic-extra-validators
```

**ADD TO SERVICE:**
```bash
cd services/api
uv add fastapi-cors
```

---

## 6. Development Workflow Example

### Scenario: Add Events Module
```bash
# Step 1: Create module structure (NO uv sync needed)
mkdir -p packages/shared/src/shared/events
touch packages/shared/src/shared/events/{__init__,models,repositories,dto,services,enums}.py

# Step 2: Implement layers
# - Write models.py (Event model)
# - Write repositories.py (EventRepository)
# - Write dto.py (EventCreateDTO, EventResponseDTO)
# - Write services.py (EventService extends BaseService)
# - Write enums.py (EventStatus enum)

# Step 3: Add to API service (if no new deps)
mkdir -p services/api/app/graphql/mutations
touch services/api/app/graphql/mutations/events.py
# → Write GraphQL mutations

# Step 4: If new dependencies added (e.g., added "python-dateutil")
cd packages/shared
uv add python-dateutil
cd ../../

# Step 5: Run uv sync (from root)
uv sync

# Step 6: Lint and format
uv run ruff check --fix .
uv run ruff format .

# Step 7: Commit
git add .
git commit -m "feat(events): add event creation and tracking system"
```

---

## 7. Quick Reference

### Command Cheatsheet
```bash
# Dependency Management
uv sync                          # Update lock file after adding deps
uv add <package>                 # Add dependency (from service dir)

# Code Quality
uv run ruff check --fix .        # Lint + auto-fix
uv run ruff format .             # Format code
uv run pytest                    # Run tests (when available)

# Running Services
uv run uvicorn app.main:app --reload          # API service
uv run celery -A app.celery_app worker        # Workers
```

### Before Commit Checklist
- [ ] New dependencies added? → `uv sync`
- [ ] Code formatted? → `ruff format`
- [ ] Linting passes? → `ruff check`
- [ ] Tests pass? → `pytest` (when applicable)
- [ ] Commit message follows format? → `type(scope): description`

---

## 8. Architecture Principles

### ✅ DO:
- Keep models, repos, DTOs, and services in **shared**
- Inherit from `BaseService` for common CRUD operations
- Use abstract repositories for consistent data access
- Keep GraphQL mutations thin (delegate to services)
- Use enums for status/state constants

### ❌ DON'T:
- Put business logic in repositories
- Mix service-specific code in shared
- Import GraphQL or FastAPI code in shared
- Bypass repositories (always use them for DB access)
- Hard-code constants (use enums instead)

---

## 9. Directory Structure Rules

### ✅ Correct Structure
```
packages/shared/src/shared/
├── events/
│   ├── __init__.py
│   ├── models.py          # Tortoise ORM models
│   ├── repositories.py    # Data access
│   ├── dto.py             # Pydantic DTOs
│   ├── services.py        # Business logic
│   └── enums.py           # Constants
```

### ❌ Incorrect Structure (Don't Do This)
```
packages/shared/src/shared/
├── events.py              # ✗ All in one file
├── event_models.py        # ✗ Scattered files
├── event_dto.py
├── event_services.py
```

---

## 10. Testing Rules (Future Phase)

```bash
# Run all tests
uv run pytest

# Run tests for specific module
uv run pytest tests/events/

# Run with coverage
uv run pytest --cov=shared

# Test patterns
# - Unit tests: test service logic, repository queries
# - Integration tests: test with actual DB (use fixtures)
# - Don't test GraphQL mutations until services are tested
```

---

## Summary: The Golden Rule

**Before committing code:**
1. Did you add/remove/change dependencies? → Run `uv sync`
2. Did you only add/modify code? → Skip `uv sync`
3. Always run `ruff check --fix` and `ruff format`
4. Commit with descriptive message
5. Never modify `uv.lock` manually
