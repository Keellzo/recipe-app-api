from typing import List, Optional

from ninja.errors import HttpError
from ninja.security import HttpBearer
from ninja import NinjaAPI, Schema
from django.contrib.auth import get_user_model
import jwt
from django.conf import settings

from core.models import Recipe


# JWT Authentication class
class JWTAuth(HttpBearer):

    def authenticate(self, request, token):
        """ Authenticate the user using a JWT token.  """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            return get_user_model().objects.get(id=user_id)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except get_user_model().DoesNotExist:
            return None


api = NinjaAPI(auth=JWTAuth())


class RecipeSchema(Schema):
    title: str
    time_minutes: int
    price: float
    description: str = ""
    link: str = ''


class RecipeOutSchema(RecipeSchema):
    id: int


class RecipePartialUpdateSchema(Schema):
    title: Optional[str] = None
    time_minutes: Optional[int] = None
    price: Optional[float] = None
    description: Optional[str] = None
    link: Optional[str] = None


@api.get("/recipes", response=List[RecipeOutSchema])
def list_recipes(request):
    """ Get a list of recipes for the authenticated user. """
    user = request.auth
    if user is None:
        return []  # Or handle unauthenticated access as needed
    return Recipe.objects.filter(user=user)


@api.post("/recipes", response=RecipeOutSchema)
def create_recipe(request, payload: RecipeSchema):
    """ Create a new recipe for the authenticated user. """
    user = request.auth
    if user is None:
        raise HttpError(401, 'Authentication required')

    if not payload.title or payload.time_minutes < 0 or payload.price < 0:
        raise HttpError(400, 'Invalid payload')

    recipe = Recipe.objects.create(user=user, **payload.dict())
    return RecipeOutSchema.from_orm(recipe)


@api.get("/{recipe_id}", response=RecipeOutSchema)
def get_recipe_detail(request, recipe_id: int):
    """ Get details of a specific recipe for the authenticated user."""
    user = request.auth
    if user is None:
        # Handle unauthenticated access
        raise HttpError(401, 'Authentication required')

    try:
        recipe = Recipe.objects.get(id=recipe_id, user=user)
        return recipe
    except Recipe.DoesNotExist:
        raise HttpError(404, 'Recipe not found')


@api.patch("/{recipe_id}", response=RecipeOutSchema)
def update_recipe(request, recipe_id: int, payload: RecipePartialUpdateSchema):
    """ Update a specific recipe for the authenticated user."""
    user = request.auth
    if user is None:
        raise HttpError(401, 'Authentication required')

    try:
        recipe = Recipe.objects.get(id=recipe_id, user=user)
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(recipe, attr, value)
        recipe.save()
        return RecipeOutSchema.from_orm(recipe)
    except Recipe.DoesNotExist:
        raise HttpError(404, 'Recipe not found')


@api.delete("/{recipe_id}")
def delete_recipe(request, recipe_id: int):
    """ Delete a specific recipe for the authenticated user."""
    user = request.auth
    if user is None:
        raise HttpError(401, 'Authentication required')

    try:
        recipe = Recipe.objects.get(id=recipe_id, user=user)
        recipe.delete()
    except Recipe.DoesNotExist:
        raise HttpError(404, 'Recipe not found')
