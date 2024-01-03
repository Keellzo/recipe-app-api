# user/api.py

from typing import List

from django.contrib.auth.models import AnonymousUser
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.security import HttpBearer
from ninja.responses import Response
from django.contrib.auth import authenticate, get_user_model
from pydantic import Field
import jwt
from datetime import datetime, timedelta
from django.conf import settings

api = NinjaAPI(version='1.0.0', urls_namespace='user')


# Utility Functions for JWT
def create_jwt_token(user_id):
    """ Generates a JWT token for a given user ID."""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(minutes=30)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def decode_jwt_token(token):
    """  Decodes a JWT token and validates it. """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# Custom JWT Authentication class
class JWTAuth(HttpBearer):
    """
        Custom JWT Authentication class that extends the HttpBearer authentication.

        This class decodes and validates the JWT token and retrieves the associated user.
    """

    def authenticate(self, request, token):
        decoded_token = decode_jwt_token(token)
        if decoded_token:
            user_id = decoded_token.get('user_id')
            return get_user_model().objects.filter(id=user_id).first()
        return None


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
    """ API endpoint to authenticate a user and provide a JWT token. """
    user = authenticate(username=payload.email, password=payload.password)
    if user:
        token = create_jwt_token(user.id)
        return {'access': token}
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


@api.get("/users", response=List[UserOutSchema], auth=JWTAuth())
def list_users(request):
    """
    Endpoint to retrieve a list of users.
    Returns a list of all users in the system.
    """
    users = get_user_model().objects.all()
    return users


@api.patch("/users/{user_id}", response=UserOutSchema, auth=JWTAuth())
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


@api.patch("/users/{user_id}/password", response=UserOutSchema, auth=JWTAuth())
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


@api.get("/me", response=UserOutSchema, auth=JWTAuth())
def retrieve_authenticated_user(request):
    """ API endpoint to retrieve the currently authenticated user's information."""

    user = request.auth
    if user and not isinstance(user, AnonymousUser):
        return UserOutSchema.from_orm(user)
    else:
        raise HttpError(401, "Authentication required")
