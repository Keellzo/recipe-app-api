# user/api.py

from typing import List
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.responses import Response
from django.contrib.auth import authenticate, get_user_model
from pydantic import Field
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

api = NinjaAPI(version='1.0.0', urls_namespace='user')


# Pydantic schemas for request and response data structures
class UserCreateSchema(Schema):
    """Schema for creating a new user."""
    email: str
    password: str = Field(..., min_length=5)
    name: str


class UserOutSchema(Schema):
    """Schema for user output."""
    email: str
    name: str


class TokenOutSchema(Schema):
    """Schema for JWT token output."""
    access: str
    refresh: str


class TokenCreateSchema(Schema):
    """Schema for creating a JWT token."""
    email: str
    password: str


class UserUpdateSchema(Schema):
    """Schema for updating user's name."""
    name: str


class UserPasswordUpdateSchema(Schema):
    """Schema for updating user's password."""
    password: str = Field(..., min_length=5)


@api.post("/token", response=TokenOutSchema, auth=None)
def create_token(request, payload: TokenCreateSchema):
    """
    Endpoint for creating a JWT token.
    Authenticates the user and generates a token upon successful authentication.
    """
    user = authenticate(request, username=payload.email, password=payload.password)
    if user is not None:
        refresh = RefreshToken.for_user(user)
        return {'refresh': str(refresh), 'access': str(refresh.access_token)}
    else:
        return Response({"detail": "Invalid credentials"}, status=400)


@api.post("/users", response=UserOutSchema)
def create_user(request, user_in: UserCreateSchema):
    """
    Endpoint for creating a new user.
    Checks if the user already exists and returns an error if so, otherwise creates a new user.
    """
    user_model = get_user_model()
    if user_model.objects.filter(email=user_in.email).exists():
        return Response({"detail": "User with this email already exists."}, status=400)

    user = user_model.objects.create_user(email=user_in.email, password=user_in.password, name=user_in.name)
    user_data = UserOutSchema.from_orm(user)
    return Response(user_data.dict(), status=201)


@api.get("/users", response=List[UserOutSchema])
def list_users():
    """
    Endpoint to retrieve a list of users.
    Returns a list of all users in the system.
    """
    users = get_user_model().objects.all()
    return users


@api.patch("/users/{user_id}", response=UserOutSchema)
def update_user_name(request, user_id: int, data: UserUpdateSchema):
    """
    Endpoint to update a user's name.
    """
    user_model = get_user_model()
    try:
        user = user_model.objects.get(id=user_id)
        user.name = data.name
        user.save()
        return UserOutSchema.from_orm(user)
    except user_model.DoesNotExist:
        return Response({"detail": "User not found"}, status=404)


@api.patch("/users/{user_id}/password", response=UserOutSchema)
def update_user_password(request, user_id: int, data: UserPasswordUpdateSchema):
    """
    Endpoint to update a user's password.
    """
    user_model = get_user_model()
    try:
        user = user_model.objects.get(id=user_id)
        user.set_password(data.password)
        user.save()
        return UserOutSchema.from_orm(user)
    except user_model.DoesNotExist:
        return Response({"detail": "User not found"}, status=404)


@api.get("/me", response=UserOutSchema)
def retrieve_authenticated_user(request):
    jwt_auth = JWTAuthentication()
    header = jwt_auth.get_header(request)
    if header is None:
        raise HttpError(401, "Authentication required")

    raw_token = jwt_auth.get_raw_token(header)
    if raw_token is None:
        raise HttpError(401, "Authentication required")

    validated_token = jwt_auth.get_validated_token(raw_token)
    user = jwt_auth.get_user(validated_token)

    if user and user.is_authenticated:
        return UserOutSchema.from_orm(user)
    else:
        raise HttpError(401, "Authentication required")
