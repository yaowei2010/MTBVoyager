from django.contrib.auth.models import User
from django.test import override_settings
from unittest.mock import patch
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from .models import AnalysisAccess, UserProfile


@override_settings(ROOT_URLCONF="accounts.test_urls")
class RbacApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin_test", password="Strong-test-pass-529!", is_superuser=True)
        self.viewer = User.objects.create_user("viewer_test", password="Strong-test-pass-529!")
        UserProfile.objects.create(user=self.viewer, role=UserProfile.Role.VIEWER)
        self.user = User.objects.create_user("user_test", password="Strong-test-pass-529!")
        UserProfile.objects.create(user=self.user, role=UserProfile.Role.USER)
        self.case = AnalysisAccess.objects.create(analysis_id="case-owned", owner=self.user)
        self.assigned_case = AnalysisAccess.objects.create(analysis_id="case-assigned", owner=self.user)
        self.assigned_case.assigned_users.add(self.viewer)

    def bearer(self, user):
        return {"HTTP_AUTHORIZATION": f"Bearer {AccessToken.for_user(user)}"}

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

    def test_user_can_run_job(self):
        response = self.client.post("/ncku_hospital/test/run-job", **self.bearer(self.user))
        self.assertEqual(response.status_code, 202)

    def test_viewer_cannot_run_job(self):
        response = self.client.post("/ncku_hospital/test/run-job", **self.bearer(self.viewer))
        self.assertEqual(response.status_code, 403)

    def test_owner_and_assigned_viewer_can_read_result(self):
        owner_response = self.client.get(
            "/ncku_hospital/test/results/case-owned", **self.bearer(self.user)
        )
        viewer_response = self.client.get(
            "/ncku_hospital/test/results/case-assigned", **self.bearer(self.viewer)
        )
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(viewer_response.status_code, 200)

    def test_unassigned_viewer_cannot_read_result(self):
        response = self.client.get(
            "/ncku_hospital/test/results/case-owned", **self.bearer(self.viewer)
        )
        self.assertEqual(response.status_code, 404)

    def test_admin_can_assign_case(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            "/ncku_hospital/accounts/cases/case-owned/access/",
            {"assigned_user_ids": [self.viewer.id]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["assigned_users"][0]["username"], "viewer_test")

    @patch("accounts.views.sync_account")
    def test_user_can_change_own_password(self, sync_account):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/ncku_hospital/accounts/me/password/",
            {"current_password": "Strong-test-pass-529!", "new_password": "Different-strong-pass-731!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Different-strong-pass-731!"))
        sync_account.assert_called_once()

    @patch("accounts.token_views.sync_account")
    @patch("accounts.token_views.record_login")
    def test_successful_login_is_audited(self, record_login, sync_account):
        response = self.client.post(
            "/ncku_hospital/accounts/token/",
            {"username": "user_test", "password": "Strong-test-pass-529!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(record_login.call_args.kwargs["success"])
        sync_account.assert_called_once()

    @patch("accounts.token_views.record_login")
    def test_failed_login_is_audited(self, record_login):
        response = self.client.post(
            "/ncku_hospital/accounts/token/",
            {"username": "user_test", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(record_login.call_args.kwargs["success"])
