from datetime import datetime, timedelta, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from .models import GeneratedLicense, LicenseRuntimeConfig
from .services import (
    generate_machine_license_key,
    is_browser_style_machine_id,
    is_machine_id_valid,
    normalize_machine_id,
)


class LicenseServiceTests(TestCase):
    def test_normalize_machine_id_trims_whitespace_uppercases_and_removes_inner_spaces(self):
        self.assertEqual(normalize_machine_id("  desk top - 123  "), "DESKTOP-123")

    def test_machine_id_validation_accepts_supported_characters(self):
        self.assertTrue(is_machine_id_valid("DESKTOP-ABC_123.XYZ"))

    def test_machine_id_validation_rejects_invalid_values(self):
        self.assertFalse(is_machine_id_valid("ab"))
        self.assertFalse(is_machine_id_valid("DESKTOP#123"))

    def test_browser_style_machine_id_detection(self):
        self.assertTrue(
            is_browser_style_machine_id("pos-123e4567-e89b-12d3-a456-426614174000")
        )
        self.assertFalse(is_browser_style_machine_id("DESKTOP-12345"))

    def test_license_key_generation_is_deterministic_and_has_expected_shape(self):
        fixed_generated_at = datetime(2026, 2, 13, 12, 0, tzinfo=datetime_timezone.utc)
        key_one = generate_machine_license_key("desktop-123", generated_at=fixed_generated_at)
        key_two = generate_machine_license_key("DESKTOP-123", generated_at=fixed_generated_at)

        self.assertEqual(key_one, key_two)
        self.assertEqual(len(key_one), 32)
        self.assertRegex(key_one, r"^[A-Za-z0-9@#$%&*!?]{32}$")
        self.assertIn(key_one[10], "@#$%&*!?")
        self.assertIn(key_one[21], "@#$%&*!?")

    def test_license_key_changes_when_10_minute_window_changes(self):
        key_one = generate_machine_license_key(
            "DESKTOP-123",
            generated_at=datetime(2026, 2, 13, 12, 0, tzinfo=datetime_timezone.utc),
        )
        key_two = generate_machine_license_key(
            "DESKTOP-123",
            generated_at=datetime(2026, 2, 13, 12, 10, tzinfo=datetime_timezone.utc),
        )

        self.assertNotEqual(key_one, key_two)

    @override_settings(LICENSE_KEY_SEED_MODE="pos_static")
    def test_license_key_is_stable_across_time_windows_in_pos_static_mode(self):
        key_one = generate_machine_license_key(
            "DESKTOP-123",
            generated_at=datetime(2026, 2, 13, 12, 0, tzinfo=datetime_timezone.utc),
        )
        key_two = generate_machine_license_key(
            "DESKTOP-123",
            generated_at=datetime(2026, 2, 13, 12, 10, tzinfo=datetime_timezone.utc),
        )

        self.assertEqual(key_one, key_two)


class AuthWorkflowTests(TestCase):
    def setUp(self):
        self.login_url = reverse("licenses:login")
        self.setup_url = reverse("licenses:initial_admin_setup")
        self.dashboard_url = reverse("licenses:dashboard")
        self.user_model = get_user_model()

    def test_login_redirects_to_admin_setup_when_superuser_missing(self):
        response = self.client.get(self.login_url)
        self.assertRedirects(response, self.setup_url)

    def test_first_admin_setup_creates_superuser_and_redirects_login(self):
        response = self.client.post(
            self.setup_url,
            {
                "username": "admin_one",
                "email": "admin@example.com",
                "password": "secure-pass-123",
                "confirm_password": "secure-pass-123",
            },
            follow=True,
        )

        self.assertTrue(
            self.user_model.objects.filter(
                username="admin_one",
                is_superuser=True,
            ).exists()
        )
        self.assertEqual(response.redirect_chain[-1][0], self.login_url)

    def test_admin_setup_redirects_to_login_after_superuser_exists(self):
        self.user_model.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="secure-pass-123",
        )
        response = self.client.get(self.setup_url)
        self.assertRedirects(response, self.login_url)

    def test_login_with_valid_credentials_redirects_dashboard(self):
        self.user_model.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="secure-pass-123",
        )
        response = self.client.post(
            self.login_url,
            {"username": "root", "password": "secure-pass-123"},
        )
        self.assertRedirects(response, self.dashboard_url)

    def test_dashboard_requires_login(self):
        self.user_model.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="secure-pass-123",
        )
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("licenses:login"), response["Location"])


class DashboardViewTests(TestCase):
    def setUp(self):
        self.url = reverse("licenses:dashboard")
        self.user = get_user_model().objects.create_user(
            username="operator_one",
            password="strong-password-123",
        )
        self.client.force_login(self.user)

    def _messages(self, response):
        return [message.message for message in get_messages(response.wsgi_request)]

    @patch("licenses.views.fetch_recent_mongo_licenses", return_value=[])
    def test_get_dashboard_with_empty_state(self, _mongo_fetch_mock):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_keys"], 0)
        self.assertEqual(response.context["today_keys"], 0)
        self.assertEqual(response.context["unique_machines"], 0)
        self.assertIsNone(response.context["last_generated"])

    def test_post_invalid_machine_id_shows_error_without_creating_license(self):
        response = self.client.post(self.url, {"machine_id": "ab!"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(GeneratedLicense.objects.count(), 0)
        self.assertTrue(
            any(
                "Enter valid Machine ID" in message
                for message in self._messages(response)
            )
        )

    def test_post_browser_style_machine_id_is_rejected(self):
        response = self.client.post(
            self.url,
            {"machine_id": "pos-123e4567-e89b-12d3-a456-426614174000"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(GeneratedLicense.objects.count(), 0)
        self.assertTrue(
            any(
                "POS browser UUID not allowed" in message
                for message in self._messages(response)
            )
        )

    @patch("licenses.views.sync_to_mongo", return_value=(True, "Saved to MongoDB."))
    def test_post_valid_machine_creates_license_with_normalized_data(self, sync_mock):
        response = self.client.post(
            self.url,
            {
                "machine_id": " desktop-123 ",
                "customer_name": "  Alice  ",
                "contact_email": "ALICE@EXAMPLE.COM ",
                "note": "  first generation  ",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(GeneratedLicense.objects.count(), 1)

        license_obj = GeneratedLicense.objects.get()
        self.assertEqual(license_obj.machine_id, "DESKTOP-123")
        self.assertEqual(license_obj.customer_name, "Alice")
        self.assertEqual(license_obj.contact_email, "alice@example.com")
        self.assertEqual(license_obj.note, "first generation")
        self.assertEqual(license_obj.generated_by, "operator_one")
        self.assertEqual(license_obj.status, "valid")
        self.assertEqual(license_obj.source, "license_manager_page")
        self.assertIsNotNone(license_obj.valid_until)
        self.assertGreater(license_obj.valid_until, license_obj.generated_at)

        self.assertEqual(response.context["generated_machine"], "DESKTOP-123")
        self.assertEqual(response.context["generated_key"], license_obj.license_key)
        self.assertTrue(
            any("License generated:" in message for message in self._messages(response))
        )

        sync_mock.assert_called_once()

    @patch("licenses.views.generate_machine_license_key", return_value="FixedKey123@abc")
    @patch("licenses.views.sync_to_mongo", return_value=(True, "Saved to MongoDB."))
    def test_reposting_same_machine_updates_existing_license_record(
        self, _sync_mock, _key_mock
    ):
        self.client.post(
            self.url, {"machine_id": "desktop-123", "note": "first"}, follow=True
        )
        self.client.post(
            self.url, {"machine_id": "DESKTOP-123", "note": "second"}, follow=True
        )

        self.assertEqual(GeneratedLicense.objects.count(), 1)
        self.assertEqual(GeneratedLicense.objects.get().note, "second")

    @patch(
        "licenses.views.generate_machine_license_key",
        side_effect=["FixedKey123@abc", "NextKey456@abc"],
    )
    @patch("licenses.views.sync_to_mongo", return_value=(True, "Saved to MongoDB."))
    def test_reposting_same_machine_with_new_key_rewrites_single_row(
        self, _sync_mock, _key_mock
    ):
        self.client.post(
            self.url, {"machine_id": "desktop-123", "note": "first"}, follow=True
        )
        self.client.post(
            self.url, {"machine_id": "DESKTOP-123", "note": "second"}, follow=True
        )

        self.assertEqual(GeneratedLicense.objects.count(), 1)
        current_license = GeneratedLicense.objects.get()
        self.assertEqual(current_license.license_key, "NextKey456@abc")
        self.assertEqual(current_license.note, "second")

    def test_superuser_can_update_mongo_settings_from_dashboard(self):
        admin_user = get_user_model().objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="admin-password-123",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            self.url,
            {
                "form_action": "save_mongo_settings",
                "mongo_uri": "mongodb://localhost:27017",
                "mongo_db": "license_custom",
                "mongo_collection": "keys_custom",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        runtime_config = LicenseRuntimeConfig.get_singleton()
        self.assertIsNotNone(runtime_config)
        self.assertEqual(runtime_config.mongo_uri, "mongodb://localhost:27017")
        self.assertEqual(runtime_config.mongo_db, "license_custom")
        self.assertEqual(runtime_config.mongo_collection, "keys_custom")
        self.assertEqual(runtime_config.updated_by, "admin_user")
        self.assertTrue(
            any(
                "MongoDB settings updated successfully." in message
                for message in self._messages(response)
            )
        )

    def test_non_superuser_cannot_update_mongo_settings_from_dashboard(self):
        response = self.client.post(
            self.url,
            {
                "form_action": "save_mongo_settings",
                "mongo_uri": "mongodb://localhost:27017",
                "mongo_db": "license_custom",
                "mongo_collection": "keys_custom",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(LicenseRuntimeConfig.objects.count(), 0)
        self.assertTrue(
            any(
                "Only admin can change MongoDB settings." in message
                for message in self._messages(response)
            )
        )

    @patch(
        "licenses.views.sync_to_mongo",
        return_value=(False, "Mongo URI empty. Saved only in local Django database."),
    )
    def test_sync_warning_is_added_when_mongo_sync_fails(self, _sync_mock):
        response = self.client.post(self.url, {"machine_id": "desktop-123"}, follow=True)

        messages = self._messages(response)
        self.assertTrue(any("License generated:" in message for message in messages))
        self.assertTrue(
            any(
                "Mongo URI empty. Saved only in local Django database." in message
                for message in messages
            )
        )

    @patch("licenses.views.fetch_recent_mongo_licenses")
    def test_dashboard_uses_mongo_records_when_local_is_empty(self, mongo_fetch_mock):
        mongo_fetch_mock.return_value = [
            {
                "license_key": "AbC123@xyZ9",
                "machine_id": "DESKTOP-REMOTE1",
                "customer_name": "Remote User",
                "contact_email": "remote@example.com",
                "note": "from atlas",
                "generated_by": "Admin01",
                "generated_at": timezone.now(),
                "status": "generated",
                "source": "license_manager_page",
            }
        ]

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_keys"], 1)
        self.assertEqual(response.context["today_keys"], 1)
        self.assertEqual(response.context["unique_machines"], 1)
        self.assertEqual(
            response.context["recent_licenses"][0]["machine_id"], "DESKTOP-REMOTE1"
        )
        mongo_fetch_mock.assert_called_once_with(limit=100)

    @patch("licenses.views.fetch_recent_mongo_licenses")
    def test_dashboard_combines_local_and_mongo_records(self, mongo_fetch_mock):
        GeneratedLicense.objects.create(
            machine_id="DESKTOP-LOCAL1",
            license_key="LocalKey123@abc",
            customer_name="Local User",
            contact_email="local@example.com",
            note="local",
            generated_by="web_user",
            status="generated",
            source="license_manager_page",
        )
        mongo_fetch_mock.return_value = [
            {
                "license_key": "MongoKey123@xyz",
                "machine_id": "DESKTOP-REMOTE1",
                "customer_name": "Remote User",
                "contact_email": "remote@example.com",
                "note": "remote",
                "generated_by": "Admin01",
                "generated_at": timezone.now() - timedelta(minutes=1),
                "status": "generated",
                "source": "license_manager_page",
            }
        ]

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_keys"], 2)
        machines = {
            item["machine_id"] if isinstance(item, dict) else item.machine_id
            for item in response.context["recent_licenses"]
        }
        self.assertIn("DESKTOP-LOCAL1", machines)
        self.assertIn("DESKTOP-REMOTE1", machines)
        mongo_fetch_mock.assert_called_once_with(limit=100)

    @patch("licenses.views.fetch_recent_mongo_licenses")
    def test_dashboard_deduplicates_same_license_key_between_local_and_mongo(
        self, mongo_fetch_mock
    ):
        GeneratedLicense.objects.create(
            machine_id="DESKTOP-LOCAL1",
            license_key="SameKey123@abc",
            customer_name="Local User",
            contact_email="local@example.com",
            note="local",
            generated_by="web_user",
            status="generated",
            source="license_manager_page",
        )
        mongo_fetch_mock.return_value = [
            {
                "license_key": "SameKey123@abc",
                "machine_id": "DESKTOP-REMOTE1",
                "customer_name": "Remote User",
                "contact_email": "remote@example.com",
                "note": "remote",
                "generated_by": "Admin01",
                "generated_at": timezone.now() + timedelta(minutes=1),
                "status": "generated",
                "source": "license_manager_page",
            }
        ]

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_keys"], 1)
        mongo_fetch_mock.assert_called_once_with(limit=100)

    @patch("licenses.views.fetch_recent_mongo_licenses", return_value=[])
    def test_dashboard_marks_expired_status_when_validity_window_passed(
        self, _mongo_fetch_mock
    ):
        item = GeneratedLicense.objects.create(
            machine_id="DESKTOP-OLD1",
            license_key="ExpiredKey123@abc",
            customer_name="Expired User",
            contact_email="expired@example.com",
            note="expired",
            generated_by="web_user",
            status="valid",
            source="license_manager_page",
        )
        GeneratedLicense.objects.filter(id=item.id).update(
            generated_at=timezone.now() - timedelta(minutes=30),
            valid_until=timezone.now() - timedelta(minutes=20),
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        first_item = response.context["recent_licenses"][0]
        status = first_item.status if hasattr(first_item, "status") else first_item["status"]
        self.assertEqual(status, "expired")


class UserManagementTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin_user = self.user_model.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="secure-pass-123",
        )
        self.client.force_login(self.admin_user)
        self.list_url = reverse("licenses:user_list")
        self.create_url = reverse("licenses:user_create")

    def test_superuser_can_view_user_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Users")

    def test_superuser_can_create_user_with_role(self):
        response = self.client.post(
            self.create_url,
            {
                "username": "cashier_1",
                "email": "cashier@example.com",
                "password": "secure-pass-123",
                "confirm_password": "secure-pass-123",
                "role": "cashier",
                "is_active": "on",
            },
            follow=True,
        )

        created_user = self.user_model.objects.get(username="cashier_1")
        self.assertTrue(created_user.is_active)
        self.assertFalse(created_user.is_staff)
        self.assertFalse(created_user.is_superuser)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], self.list_url)

    def test_superuser_can_edit_user(self):
        edited_user = self.user_model.objects.create_user(
            username="employee_one",
            password="old-pass-123",
        )
        edit_url = reverse("licenses:user_edit", args=[edited_user.id])

        response = self.client.post(
            edit_url,
            {
                "username": "employee_updated",
                "email": "employee@example.com",
                "password": "new-pass-123",
                "confirm_password": "new-pass-123",
                "role": "supervisor",
                "is_active": "on",
            },
            follow=True,
        )

        edited_user.refresh_from_db()
        self.assertEqual(edited_user.username, "employee_updated")
        self.assertEqual(edited_user.email, "employee@example.com")
        self.assertTrue(edited_user.is_staff)
        self.assertFalse(edited_user.is_superuser)
        self.assertTrue(edited_user.check_password("new-pass-123"))
        self.assertEqual(response.status_code, 200)

    def test_last_superuser_cannot_be_downgraded(self):
        edit_url = reverse("licenses:user_edit", args=[self.admin_user.id])
        response = self.client.post(
            edit_url,
            {
                "username": "superadmin",
                "email": "superadmin@example.com",
                "password": "",
                "confirm_password": "",
                "role": "cashier",
                "is_active": "on",
            },
        )

        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_superuser)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "At least one superuser must remain in the system.")

    def test_non_superuser_is_redirected_from_user_pages(self):
        self.client.logout()
        normal_user = self.user_model.objects.create_user(
            username="normal_user",
            password="secure-pass-123",
        )
        self.client.force_login(normal_user)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("licenses:dashboard"), response["Location"])
