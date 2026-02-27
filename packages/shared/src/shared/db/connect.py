from tortoise import Tortoise
from shared.config import settings
TORTOISE_CONFIG = {
    "connections": {"default": settings.database_url},
    "apps": {
        "models": {
            "models": [
                "shared.db.models.users",
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