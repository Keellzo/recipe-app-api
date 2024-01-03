"""
Tests for the user API.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, Client

CREATE_USER_URL = '/api/user/users'
TOKEN_URL = '/api/user/token'
ME_URL = '/api/user/me'


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

    def test_retrieve_user_unauthorized(self):
        """Test authentication is required for users."""
        results = self.client.get(ME_URL)
        self.assertEqual(results.status_code, 401)

    def test_update_user_name(self):
        """Test updating a user's name."""
        user_details = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Original Name'
        }
        user = create_user(**user_details)
        payload = {'name': 'Updated Name'}

        # Obtain a token for the created user
        response = self.client.post(TOKEN_URL, user_details, content_type='application/json')
        token = response.json().get('access')
        self.assertIsNotNone(token, "Token generation failed, check token endpoint")

        # Attach the token to the headers
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        result = self.client.patch(f'/api/user/users/{user.id}', payload, content_type='application/json')

        self.assertEqual(result.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.name, payload['name'])

    def test_update_user_password(self):
        """Test updating a user's password."""
        user_details = {
            'email': 'test@example.com',
            'password': 'originalpass123',
            'name': 'Test User'
        }
        user = create_user(**user_details)
        payload = {'password': 'newpass123'}

        # Obtain a token for the created user
        response = self.client.post(TOKEN_URL, user_details, content_type='application/json')
        token = response.json().get('access')
        self.assertIsNotNone(token, "Token generation failed, check token endpoint")

        # Attach the token to the headers
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        result = self.client.patch(f'/api/user/users/{user.id}/password', payload, content_type='application/json')

        self.assertEqual(result.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password(payload['password']))

    def test_retrieve_user_authenticated(self):
        """Test retrieving the current user's data when authenticated."""
        user_details = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test User'
        }
        create_user(**user_details)

        response = self.client.post(TOKEN_URL, user_details, content_type='application/json')
        token = response.json().get('access')
        self.assertIsNotNone(token, "Token generation failed, check token endpoint")

        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        results = self.client.get(ME_URL)
        self.assertEqual(results.status_code, 200)

