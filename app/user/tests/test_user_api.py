"""
Tests for the user API.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, Client

CREATE_USER_URL = '/api/user/users'
TOKEN_URL = '/api/user/token'


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Test the public features of the user API."""

    def setUp(self):
        self.client = Client()

    def test_create_user_success(self):
        """Test creating a new user is successful."""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name',
        }

        result = self.client.post(CREATE_USER_URL, payload, content_type='application/json')
        self.assertEqual(result.status_code, 201)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))

        response_data = result.json()
        self.assertNotIn('password', response_data)

    def test_user_with_email_exists_error(self):
        """Test error if returned user with email exists."""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name'
        }

        create_user(**payload)

        result = self.client.post(CREATE_USER_URL, payload, content_type='application/json')
        self.assertEqual(result.status_code, 400)

    def test_password_too_short_error(self):
        """Test an error is returned if password less than 5 characters."""
        payload = {
            'email': 'test@example.com',
            'password': 'pw',
            'name': 'Test Name'
        }

        result = self.client.post(CREATE_USER_URL, payload, content_type='application/json')
        self.assertEqual(result.status_code, 422)
        user_exists = get_user_model().objects.filter(email=payload['email']).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test creating token for user."""
        user_details = {
            'name': 'Test Name',
            'email': 'test@example.com',
            'password': 'test-user-password123',
        }

        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': user_details['password']
        }

        results = self.client.post(TOKEN_URL, payload, content_type='application/json')
        self.assertIn('access', results.json())
        self.assertEqual(results.status_code, 200)

    def test_create_token_bad_credentials(self):
        """Test returns error if credentials invalid"""
        create_user(email='test@example.com', password='goodpass')
        payload = {'email': 'test@example.com', 'password': 'badpass'}

        results = self.client.post(TOKEN_URL, payload, content_type='application')

        self.assertNotIn('access', results.json())
        self.assertEqual(results.status_code, 400)

    def test_create_token_blank_password(self):
        """Test posting a blank password returns an error"""
        payload = {'email': 'test@example', 'password': ''}
        results = self.client.post(TOKEN_URL, payload, content_type='application/json')

        self.assertNotIn('access', results.json())
        self.assertEqual(results.status_code, 400)
