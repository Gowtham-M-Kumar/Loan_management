"""
Tests for deployment configuration and health check endpoint
"""
from django.test import TestCase, Client
from django.urls import reverse


class DeploymentTestCase(TestCase):
    """Test deployment-related functionality"""

    def setUp(self):
        self.client = Client()

    def test_health_check_endpoint(self):
        """Test that the health check endpoint returns correct response"""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'Gold Loan Management System')

    def test_health_check_endpoint_by_name(self):
        """Test health check endpoint using URL name"""
        url = reverse('health_check')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
