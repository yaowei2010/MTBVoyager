from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import UserProfile


@override_settings(ROOT_URLCONF="accounts.test_urls")
class RbacApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin_test", password="Strong-test-pass-529!", is_superuser=True)
        self.viewer = User.objects.create_user("viewer_test", password="Strong-test-pass-529!")
        UserProfile.objects.create(user=self.viewer, role=UserProfile.Role.VIEWER)

    def test_me_returns_role_and_permissions(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.get("/ncku_hospital/accounts/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "viewer")
        self.assertNotIn("analysis.run", response.data["permissions"])

    def test_viewer_cannot_manage_users(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.get("/ncku_hospital/accounts/users/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_viewer(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/ncku_hospital/accounts/users/",
            {"username": "new_viewer", "password": "Strong-test-pass-529!", "role": "viewer"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["role"], "viewer")

    def test_admin_cannot_disable_self(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/ncku_hospital/accounts/users/{self.admin.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(response.status_code, 400)
