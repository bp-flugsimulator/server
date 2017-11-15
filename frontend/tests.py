from django.test import TestCase, Client
from django.urls import reverse

class FrontendTests(TestCase):
    def test_welcome_get(self):
        c = Client()
        response = c.get(reverse('frontend:welcome'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "welcome")

    def test_slaves_get(self):
        c = Client()
        response = c.get(reverse('frontend:slaves'))
        self.assertEqual(response.status_code, 200)