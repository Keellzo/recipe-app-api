# user/api.py

from typing import List
from ninja import NinjaAPI, Schema
from django.contrib.auth import get_user_model
from ninja.responses import Response
from django.contrib.auth import authenticate
from pydantic import Field
from rest_framework_simplejwt.tokens import RefreshToken


# Pydantic schemas
class UserCreateSchema(Schema):
    email: str
    password: str = Field(..., min_length=5)
    name: str


class UserOutSchema(Schema):
    email: str
    name: str


class TokenOutSchema(Schema):
    access: str
    refresh: str


class TokenCreateSchema(Schema):
    email: str
    password: str


# API instance
api = NinjaAPI(version='1.0.0', urls_namespace='user')  # Set unique version and namespace


# API operations

@api.post("/token", response=TokenOutSchema, auth=None)
def create_token(request, payload: TokenCreateSchema):
    user = authenticate(request, username=payload.email, password=payload.password)
    if user is not None:
        # Generate token
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    else:
        return Response({"detail": "Invalid credentials"}, status=400)


@api.post("/users", response=UserOutSchema)
def create_user(request, user_in: UserCreateSchema):
    user_model = get_user_model()
    if user_model.objects.filter(email=user_in.email).exists():
        return Response({"detail": "User with this email already exists."}, status=400)

    user = get_user_model().objects.create_user(
        email=user_in.email,
        password=user_in.password,
        name=user_in.name
    )

    user_data = UserOutSchema.from_orm(user)
    return Response(user_data.dict(), status=201)


@api.get("/users", response=List[UserOutSchema])
def list_users():
    users = get_user_model().objects.all()
    return users
