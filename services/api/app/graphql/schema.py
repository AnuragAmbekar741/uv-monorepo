import strawberry

@strawberry.type
class Query:
    @strawberry.field
    async def ping(self) -> str:
        return "pong"

schema = strawberry.Schema(query=Query)
