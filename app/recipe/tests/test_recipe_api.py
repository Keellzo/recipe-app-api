"""
Tests for recipe APIs
"""
from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from ninja import UploadedFile

from core.models import Recipe
import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings

RECIPES_URL = '/api/recipe/recipes'


def create_jwt_token(user_id):
    """Utility function for creating JWT tokens for testing."""
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=60)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def detail_url(recipe_id):
    """Create and return a recipe detail URL"""
    return '/api/recipe/' + str(recipe_id)


def image_upload_url(recipe_id):
    """Create and return an image upload URL"""
    return '/api/recipe/' + str(recipe_id) + '/upload-image'


def create_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Test Recipe',
        'time_minutes': 22,
        'price': Decimal('12'),
        'description': 'Test Description',
        'link': 'https://www.example.com/recipe.pdf'
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe API requests"""

    def setUp(self):
        self.client = Client()

    def test_auth_required(self):
        """Test auth is required to call API"""
        res = self.client.get(RECIPES_URL)
        self.assertEqual(res.status_code, 401)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated recipe API requests"""

    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'testpass123'
        )
        token = create_jwt_token(self.user.id)
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user).order_by('id')
        expected_data = [
            {
                'id': r.id,
                'title': r.title,
                'time_minutes': r.time_minutes,
                'price': float(r.price),  # Convert the price to float
                'description': r.description,
                'link': r.link
            } for r in recipes.order_by('id')
        ]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_data)

    def test_recipes_limited_to_user(self):
        """Test retrieving recipes for authenticated user"""
        other_user = create_user(email='other@example.com', password='password123')
        create_recipe(user=other_user)
        created_recipe = create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        expected_data = [
            {
                'id': r.id,
                'title': r.title,
                'time_minutes': r.time_minutes,
                'price': float(r.price),
                'description': r.description,
                'link': r.link
            } for r in recipes.order_by('id')
        ]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_data)

    def test_get_recipe_detail(self):
        """Test getting recipe detail"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        response = self.client.get(url)

        expected_data = {
            'id': recipe.id,
            'title': recipe.title,
            'time_minutes': recipe.time_minutes,
            'price': float(recipe.price),
            'description': recipe.description,
            'link': recipe.link
        }

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_data)

    def test_create_recipe(self):
        """Test creating a recipe"""
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 30,
            'price': 5.99,
            'description': 'Sample description',
            'link': 'http://localhost:'
        }

        response = self.client.post(RECIPES_URL, payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        recipe = Recipe.objects.get(id=response_json['id'])

        # Check each field
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(recipe.description, payload['description'])
        self.assertEqual(recipe.link, payload['link'])
        self.assertEqual(recipe.price, Decimal(str(payload['price'])))
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update of a recipe."""
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link=original_link,
        )

        payload = {'title': 'New recipe title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, data=payload, content_type='application/json')  # Send as JSON

        self.assertEqual(res.status_code, 200)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update_recipe(self):
        """Test full update of a recipe."""
        recipe = create_recipe(
            user=self.user,
            title='Old title',
            time_minutes=10,
            price=5.00,
            description='Old description',
            link='https://old-link.com'
        )

        payload = {
            'title': 'New title',
            'time_minutes': 20,
            'price': 10.00,
            'description': 'New description',
            'link': 'https://new-link.com'
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, data=payload, content_type='application/json')

        self.assertEqual(res.status_code, 200, res.content)  # Add res.content for debugging
        recipe.refresh_from_db()
        for attr, value in payload.items():
            self.assertEqual(getattr(recipe, attr), value)

    def test_delete_recipe(self):
        """Test deleting a recipe."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, 200)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_recipe_other_user(self):
        """Test deleting a recipe that belongs to another user."""
        other_user = create_user(email='other@example.com', password='password123')
        recipe = create_recipe(user=other_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, 404)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_recipe_not_found(self):
        """Test deleting a recipe that doesn't exist."""
        url = detail_url(99999999999999)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, 404)


class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'testpass123'
        )
        self.recipe = create_recipe(user=self.user)
        token = create_jwt_token(self.user.id)
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10), color='white')  # Create a white RGB image
            img.save(image_file, 'JPEG')
            image_file.seek(0)
            payload = {'image': UploadedFile(image_file, name='test.jpg')}
            response = self.client.post(url, data=payload, format='multipart')
        self.recipe.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(os.path.exists(self.recipe.image.path))
        self.assertIsNotNone(self.recipe.image)

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        response = self.client.post(url, data=payload, format='multipart')
        self.assertEqual(response.status_code, 422)

