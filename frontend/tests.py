from django.test import TestCase, Client
from django.urls import reverse

class FrontendTests(TestCase):
    def test_homepage_get(self):
        c = Client()
        response = c.get(reverse('frontend:index'))
        self.assertEqual(response.status_code, 200)
