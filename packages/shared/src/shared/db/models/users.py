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
