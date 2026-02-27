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
