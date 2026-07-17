from django.test import TestCase
from django.urls import reverse

from .models import CustomUser


class AccountAuthTests(TestCase):
    def test_home_page_is_available(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NForge')

    def test_register_user_creates_account(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'alice',
                'email': 'alice@example.com',
                'password1': 'StrongPass123',
                'password2': 'StrongPass123',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomUser.objects.filter(username='alice').exists())

    def test_login_user_with_valid_credentials(self):
        CustomUser.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='StrongPass123',
        )

        response = self.client.post(
            reverse('login'),
            {'username': 'bob', 'password': 'StrongPass123'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
