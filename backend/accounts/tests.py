from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.auth.hashers import is_password_usable, identify_hasher
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from projects.models import Project


class NForgeAuthenticationSecurityTests(TestCase):
    """
    Phase 8.6.2 — NForge Authentication & Session Security Audit Regression Tests.
    Verifies authentication mechanics, credential defenses, inactive account handling,
    token lifecycle, privilege escalation prevention, and zero credential leakage.
    """

    def setUp(self):
        self.client = APIClient()

        # Regular research user
        self.raw_password = "SecureResearchPassword123!"
        self.normal_user = User.objects.create_user(
            username="researcher_alice",
            email="alice@example.com",
            password=self.raw_password,
        )

        # Staff admin user
        self.staff_password = "StaffAdminPassword123!"
        self.staff_user = User.objects.create_user(
            username="staff_admin_bob",
            email="bob_admin@example.com",
            password=self.staff_password,
            is_staff=True,
        )

        # Superuser
        self.super_password = "SuperUserPassword123!"
        self.super_user = User.objects.create_superuser(
            username="superuser_root",
            email="root@example.com",
            password=self.super_password,
        )

        # Inactive user
        self.inactive_password = "InactivePassword123!"
        self.inactive_user = User.objects.create_user(
            username="inactive_charlie",
            email="charlie@example.com",
            password=self.inactive_password,
            is_active=False,
        )

    # -------------------------------------------------------------------------
    # 1. Login Authentication Tests
    # -------------------------------------------------------------------------

    def test_valid_login_succeeds_and_returns_token_and_safe_user_metadata(self):
        """Valid credentials return HTTP 200 with token and safe user attributes."""
        res = self.client.post(
            "/api/auth/login/",
            {"username": "researcher_alice", "password": self.raw_password},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("token", res.data)
        self.assertIn("user", res.data)
        self.assertEqual(res.data["user"]["username"], "researcher_alice")
        self.assertEqual(res.data["user"]["email"], "alice@example.com")
        self.assertFalse(res.data["user"]["is_staff"])
        self.assertFalse(res.data["user"]["is_superuser"])

        # Token exists in DB and maps to user
        token = Token.objects.get(key=res.data["token"])
        self.assertEqual(token.user, self.normal_user)

    def test_invalid_password_fails_safely_with_generic_error(self):
        """Invalid password returns generic 400 Bad Request error."""
        res = self.client.post(
            "/api/auth/login/",
            {"username": "researcher_alice", "password": "WrongPasswordXYZ"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("error"), "Invalid Credentials")
        self.assertNotIn("token", res.data)

    def test_nonexistent_user_fails_safely_with_identical_generic_error(self):
        """Nonexistent username returns identical generic 400 Bad Request error."""
        res = self.client.post(
            "/api/auth/login/",
            {"username": "ghost_user_9999", "password": "AnyPassword123!"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("error"), "Invalid Credentials")
        self.assertNotIn("token", res.data)

    def test_missing_and_empty_credentials_rejected_cleanly(self):
        """Missing or blank username/password are rejected without server errors."""
        cases = [
            {},
            {"username": "researcher_alice"},
            {"password": self.raw_password},
            {"username": "", "password": ""},
            {"username": "researcher_alice", "password": ""},
            {"username": "", "password": self.raw_password},
            {"username": None, "password": None},
        ]
        for payload in cases:
            res = self.client.post("/api/auth/login/", payload, format="json")
            self.assertEqual(
                res.status_code,
                status.HTTP_400_BAD_REQUEST,
                f"Payload {payload} should return 400",
            )
            self.assertEqual(res.data.get("error"), "Invalid Credentials")

    def test_malformed_login_payload_rejected_cleanly(self):
        """Non-dictionary payloads (lists, raw strings) are rejected safely."""
        for malformed in [[], ["bad"], "not a json dict"]:
            res = self.client.post("/api/auth/login/", malformed, format="json")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(res.data.get("error"), "Invalid Credentials")

    # -------------------------------------------------------------------------
    # 2. Inactive User Handling
    # -------------------------------------------------------------------------

    def test_inactive_user_cannot_login(self):
        """Users with is_active=False cannot authenticate or obtain a new token."""
        res = self.client.post(
            "/api/auth/login/",
            {"username": "inactive_charlie", "password": self.inactive_password},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("error"), "Invalid Credentials")
        self.assertNotIn("token", res.data)

    def test_already_authenticated_user_blocked_when_deactivated(self):
        """
        If an authenticated user's account is deactivated (is_active=False),
        subsequent API requests using their existing token are rejected with 401.
        """
        token = Token.objects.create(user=self.normal_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        # Active user succeeds
        res_active = self.client.get("/api/auth/me/")
        self.assertEqual(res_active.status_code, status.HTTP_200_OK)

        # Deactivate user
        self.normal_user.is_active = False
        self.normal_user.save()

        # Existing token now rejected with 401
        res_deactivated = self.client.get("/api/auth/me/")
        self.assertEqual(res_deactivated.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("inactive", str(res_deactivated.data).lower())

    # -------------------------------------------------------------------------
    # 3. Protected Endpoint Authorization & Token Handling
    # -------------------------------------------------------------------------

    def test_unauthenticated_request_to_protected_endpoints_returns_401(self):
        """Unauthenticated requests to protected endpoints return HTTP 401."""
        protected_urls = [
            "/api/auth/me/",
            "/api/auth/test/",
            "/api/projects/",
            "/api/admin/dashboard/",
        ]
        self.client.credentials()  # Clear credentials
        for url in protected_urls:
            res = self.client.get(url)
            self.assertEqual(
                res.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"URL '{url}' must require authentication",
            )

    def test_invalid_or_malformed_token_returns_401(self):
        """Requests with fabricated, corrupt, or invalid tokens return 401."""
        invalid_headers = [
            "Token nonexistent_key_999999999",
            "Token invalid!token!format",
            "Bearer invalid_scheme",
            "Token",
        ]
        for auth_header in invalid_headers:
            self.client.credentials(HTTP_AUTHORIZATION=auth_header)
            res = self.client.get("/api/auth/me/")
            self.assertEqual(
                res.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Header '{auth_header}' should return 401",
            )

    def test_valid_normal_user_token_accesses_research_endpoints(self):
        """Valid normal user token grants access to research endpoints."""
        token = Token.objects.create(user=self.normal_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        res_me = self.client.get("/api/auth/me/")
        self.assertEqual(res_me.status_code, status.HTTP_200_OK)
        self.assertEqual(res_me.data["username"], "researcher_alice")

        res_proj = self.client.get("/api/projects/")
        self.assertEqual(res_proj.status_code, status.HTTP_200_OK)

    def test_staff_and_superuser_authentication_works_correctly(self):
        """Staff and superuser tokens authenticate and access admin endpoints."""
        # Staff token
        token_staff = Token.objects.create(user=self.staff_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token_staff.key}")
        res_staff_me = self.client.get("/api/auth/me/")
        self.assertEqual(res_staff_me.status_code, status.HTTP_200_OK)
        self.assertTrue(res_staff_me.data["is_staff"])
        res_staff_admin = self.client.get("/api/admin/dashboard/")
        self.assertEqual(res_staff_admin.status_code, status.HTTP_200_OK)

        # Superuser token
        token_super = Token.objects.create(user=self.super_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token_super.key}")
        res_super_admin = self.client.get("/api/admin/dashboard/")
        self.assertEqual(res_super_admin.status_code, status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # 4. Privilege Escalation Prevention
    # -------------------------------------------------------------------------

    def test_normal_user_token_cannot_access_admin_endpoints(self):
        """Normal authenticated researcher token cannot access admin endpoints (403)."""
        token = Token.objects.create(user=self.normal_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        admin_urls = [
            "/api/admin/dashboard/",
            "/api/admin/users/",
            "/api/admin/projects/",
            "/api/admin/papers/",
            "/api/admin/activity/",
            "/api/admin/ai-usage/",
        ]
        for url in admin_urls:
            res = self.client.get(url)
            self.assertEqual(
                res.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Normal user token must receive 403 on '{url}'",
            )

    def test_registration_payload_cannot_forge_staff_or_superuser_status(self):
        """
        Submitting is_staff=True or is_superuser=True during registration
        must be ignored; created accounts must remain normal unprivileged users.
        """
        payload = {
            "username": "hacker_attempt",
            "email": "hacker@example.com",
            "password": "HackerPassword123!",
            "is_staff": True,
            "is_superuser": True,
        }
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="hacker_attempt")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    # -------------------------------------------------------------------------
    # 5. Logout & Token Invalidation
    # -------------------------------------------------------------------------

    def test_logout_deletes_token_and_invalidates_subsequent_requests(self):
        """
        Calling /api/auth/logout/ deletes the user's Token from the database.
        Any subsequent API request using the same token returns HTTP 401.
        """
        token = Token.objects.create(user=self.normal_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        # Successfully access protected endpoint before logout
        res_before = self.client.get("/api/auth/me/")
        self.assertEqual(res_before.status_code, status.HTTP_200_OK)

        # Call logout
        res_logout = self.client.post("/api/auth/logout/")
        self.assertEqual(res_logout.status_code, status.HTTP_200_OK)
        self.assertEqual(res_logout.data.get("success"), "Successfully logged out.")

        # Token was purged from database
        self.assertFalse(Token.objects.filter(key=token.key).exists())

        # Subsequent call with the same token fails with 401
        res_after = self.client.get("/api/auth/me/")
        self.assertEqual(res_after.status_code, status.HTTP_401_UNAUTHORIZED)

    # -------------------------------------------------------------------------
    # 6. Password Storage & Data Leakage Prevention
    # -------------------------------------------------------------------------

    def test_passwords_are_securely_hashed_and_plaintext_never_stored(self):
        """Passwords must be hashed with standard Django hasher; plaintext must not exist in DB."""
        user = User.objects.get(username="researcher_alice")
        # Django's password field must be a valid PBKDF2 hash
        self.assertTrue(is_password_usable(user.password))
        self.assertIn("pbkdf2_sha256", user.password)
        # Plaintext password is never the value stored in password field
        self.assertNotEqual(user.password, self.raw_password)

    def test_passwords_and_hashes_never_exposed_in_any_api_response(self):
        """
        Ensure passwords and password hashes are never returned in:
        - login response
        - registration response
        - me response
        - admin user endpoints
        """
        # 1. Login response
        res_login = self.client.post(
            "/api/auth/login/",
            {"username": "researcher_alice", "password": self.raw_password},
            format="json",
        )
        login_str = str(res_login.data)
        self.assertNotIn(self.raw_password, login_str)
        self.assertNotIn("pbkdf2", login_str)
        self.assertNotIn("password", res_login.data.get("user", {}))

        # 2. Registration response
        res_reg = self.client.post(
            "/api/auth/register/",
            {"username": "new_student", "email": "new@example.com", "password": "SecretPassword123!"},
            format="json",
        )
        self.assertEqual(res_reg.status_code, status.HTTP_201_CREATED)
        reg_str = str(res_reg.data)
        self.assertNotIn("SecretPassword123!", reg_str)
        self.assertNotIn("pbkdf2", reg_str)
        self.assertNotIn("password", res_reg.data)

        # 3. Current user response
        token = Token.objects.get(user=self.normal_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        res_me = self.client.get("/api/auth/me/")
        me_str = str(res_me.data)
        self.assertNotIn("password", me_str.lower())
        self.assertNotIn("pbkdf2", me_str)

        # 4. Admin user list and detail responses
        staff_token = Token.objects.create(user=self.staff_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {staff_token.key}")
        res_admin_user = self.client.get(f"/api/admin/users/{self.normal_user.id}/")
        self.assertEqual(res_admin_user.status_code, status.HTTP_200_OK)
        admin_user_str = str(res_admin_user.data)
        self.assertNotIn("password", admin_user_str.lower())
        self.assertNotIn("pbkdf2", admin_user_str)


class FriendshipSystemTests(TestCase):
    """
    Tests for NForge Friendship & Contact System.
    """

    def setUp(self):
        self.client = APIClient()

        self.user_a = User.objects.create_user(
            username="alice_researcher",
            email="alice@example.com",
            password="Password123!",
        )
        self.token_a = Token.objects.create(user=self.user_a)

        self.user_b = User.objects.create_user(
            username="bob_collaborator",
            email="bob@example.com",
            password="Password123!",
        )
        self.token_b = Token.objects.create(user=self.user_b)

        self.user_c = User.objects.create_user(
            username="charlie_third",
            email="charlie@example.com",
            password="Password123!",
        )
        self.token_c = Token.objects.create(user=self.user_c)

    def test_list_friends_initially_empty(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        res = self.client.get("/api/friends/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["friends"], [])
        self.assertEqual(res.data["incoming"], [])
        self.assertEqual(res.data["outgoing"], [])

    def test_send_friend_request_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        res = self.client.post(
            "/api/friends/request/",
            {"username": "bob_collaborator"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["status"], "PENDING")

        # Verify outgoing for A
        res_a = self.client.get("/api/friends/")
        self.assertEqual(len(res_a.data["outgoing"]), 1)
        self.assertEqual(res_a.data["outgoing"][0]["to_user"]["username"], "bob_collaborator")

        # Verify incoming for B
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_b.key}")
        res_b = self.client.get("/api/friends/")
        self.assertEqual(len(res_b.data["incoming"]), 1)
        self.assertEqual(res_b.data["incoming"][0]["from_user"]["username"], "alice_researcher")

    def test_cannot_friend_self(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        res = self.client.post(
            "/api/friends/request/",
            {"username": "alice_researcher"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_send_duplicate_friend_request(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        res1 = self.client.post(
            "/api/friends/request/",
            {"username": "bob_collaborator"},
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post(
            "/api/friends/request/",
            {"username": "bob_collaborator"},
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_friend_request_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        res_req = self.client.post(
            "/api/friends/request/",
            {"username": "bob_collaborator"},
            format="json",
        )
        friendship_id = res_req.data["id"]

        # User B accepts
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_b.key}")
        res_accept = self.client.post(f"/api/friends/{friendship_id}/accept/")
        self.assertEqual(res_accept.status_code, status.HTTP_200_OK)

        # Both now have each other in friends list
        res_b_list = self.client.get("/api/friends/")
        self.assertEqual(len(res_b_list.data["friends"]), 1)
        self.assertEqual(res_b_list.data["friends"][0]["user"]["username"], "alice_researcher")

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        res_a_list = self.client.get("/api/friends/")
        self.assertEqual(len(res_a_list.data["friends"]), 1)
        self.assertEqual(res_a_list.data["friends"][0]["user"]["username"], "bob_collaborator")

    def test_non_recipient_cannot_accept_request(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        res_req = self.client.post(
            "/api/friends/request/",
            {"username": "bob_collaborator"},
            format="json",
        )
        friendship_id = res_req.data["id"]

        # User C attempts to accept request intended for User B
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_c.key}")
        res_accept = self.client.post(f"/api/friends/{friendship_id}/accept/")
        self.assertEqual(res_accept.status_code, status.HTTP_403_FORBIDDEN)

    def test_decline_friend_request(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        res_req = self.client.post(
            "/api/friends/request/",
            {"username": "bob_collaborator"},
            format="json",
        )
        friendship_id = res_req.data["id"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_b.key}")
        res_decline = self.client.post(f"/api/friends/{friendship_id}/decline/")
        self.assertEqual(res_decline.status_code, status.HTTP_200_OK)

        res_b_list = self.client.get("/api/friends/")
        self.assertEqual(len(res_b_list.data["incoming"]), 0)
        self.assertEqual(len(res_b_list.data["friends"]), 0)

    def test_remove_friend(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        res_req = self.client.post(
            "/api/friends/request/",
            {"username": "bob_collaborator"},
            format="json",
        )
        friendship_id = res_req.data["id"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_b.key}")
        self.client.post(f"/api/friends/{friendship_id}/accept/")

        # User B removes friend
        res_del = self.client.delete(f"/api/friends/{friendship_id}/")
        self.assertEqual(res_del.status_code, status.HTTP_200_OK)

        res_b_list = self.client.get("/api/friends/")
        self.assertEqual(len(res_b_list.data["friends"]), 0)

    def test_search_users(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        res = self.client.get("/api/friends/search/?q=bob")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["username"], "bob_collaborator")
        self.assertNotIn("password", res.data[0])


class UserProfileEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="profile_researcher",
            email="researcher@example.com",
            password="StrongPassword123!",
            first_name="Jane",
            last_name="Doe",
        )
        self.token = Token.objects.create(user=self.user)

    def test_unauthenticated_profile_access_rejected(self):
        res = self.client.get("/api/auth/profile/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_profile_returns_safe_data(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        res = self.client.get("/api/auth/profile/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["username"], "profile_researcher")
        self.assertEqual(res.data["email"], "researcher@example.com")
        self.assertEqual(res.data["first_name"], "Jane")
        self.assertEqual(res.data["last_name"], "Doe")
        self.assertTrue(res.data["is_active"])
        self.assertIn("date_joined", res.data)
        self.assertIn("projects_count", res.data)
        self.assertIn("friends_count", res.data)
        self.assertNotIn("password", res.data)
        self.assertNotIn("token", res.data)

