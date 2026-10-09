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
            "first_name": "Hacker",
            "last_name": "Attempt",
            "username": "hacker_attempt",
            "email": "hacker@example.com",
            "password": "HackerPassword123!",
            "confirm_password": "HackerPassword123!",
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
            {
                "first_name": "New",
                "last_name": "Student",
                "username": "new_student",
                "email": "new@example.com",
                "password": "SecretPassword123!",
                "confirm_password": "SecretPassword123!",
            },
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
        self.raw_password = "StrongPassword123!"
        self.user = User.objects.create_user(
            username="profile_researcher",
            email="researcher@example.com",
            password=self.raw_password,
            first_name="Jane",
            last_name="Doe",
        )
        self.token = Token.objects.create(user=self.user)

        self.other_user = User.objects.create_user(
            username="other_researcher",
            email="other@example.com",
            password="OtherPassword123!",
            first_name="John",
            last_name="Smith",
        )
        self.other_token = Token.objects.create(user=self.other_user)

    def test_unauthenticated_profile_access_rejected(self):
        """Unauthenticated GET, PATCH, and PUT requests to profile endpoint are rejected with 401."""
        for method in ['get', 'patch', 'put']:
            res = getattr(self.client, method)("/api/auth/profile/", {"username": "new_name"}, format="json")
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_profile_returns_safe_data(self):
        """GET /api/auth/profile/ returns profile details without password or tokens."""
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

    def test_successful_username_change_via_patch_and_put(self):
        """Authenticated user can update their username via PATCH and PUT."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        # 1. Update via PATCH
        res_patch = self.client.patch(
            "/api/auth/profile/",
            {"username": "jane_researcher"},
            format="json"
        )
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data["username"], "jane_researcher")
        self.assertEqual(res_patch.data["first_name"], "Jane")
        self.assertEqual(res_patch.data["last_name"], "Doe")
        self.assertEqual(res_patch.data["email"], "researcher@example.com")

        # Verify DB updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "jane_researcher")

        # 2. Update via PUT
        res_put = self.client.put(
            "/api/auth/profile/",
            {"username": "jane_curie"},
            format="json"
        )
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
        self.assertEqual(res_put.data["username"], "jane_curie")

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "jane_curie")

    def test_duplicate_username_rejected(self):
        """Attempting to change username to an already existing username is rejected."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        # Exact match duplicate
        res = self.client.patch(
            "/api/auth/profile/",
            {"username": "other_researcher"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", res.data)

        # Case-insensitive duplicate
        res_case = self.client.patch(
            "/api/auth/profile/",
            {"username": "OTHER_RESEARCHER"},
            format="json"
        )
        self.assertEqual(res_case.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", res_case.data)

        # Verify DB unchanged
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "profile_researcher")

    def test_invalid_username_rejected(self):
        """Invalid username length, format, or blank characters are rejected."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        invalid_cases = [
            "",
            "   ",
            "ab",  # Less than 3 chars
            "user with spaces",
            "user@name!",
            "invalid#char",
        ]

        for bad_username in invalid_cases:
            res = self.client.patch(
                "/api/auth/profile/",
                {"username": bad_username},
                format="json"
            )
            self.assertEqual(
                res.status_code,
                status.HTTP_400_BAD_REQUEST,
                f"Username '{bad_username}' should be rejected with 400"
            )
            self.assertIn("username", res.data)

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "profile_researcher")

    def test_first_name_last_name_and_email_cannot_be_changed(self):
        """Attempts to change first_name, last_name, or email via profile update return explicit validation errors."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        # Attempt to change first_name
        res_first = self.client.patch(
            "/api/auth/profile/",
            {"first_name": "HackedName"},
            format="json"
        )
        self.assertEqual(res_first.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("first_name", res_first.data)

        # Attempt to change last_name
        res_last = self.client.patch(
            "/api/auth/profile/",
            {"last_name": "HackedLastName"},
            format="json"
        )
        self.assertEqual(res_last.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("last_name", res_last.data)

        # Attempt to change email
        res_email = self.client.patch(
            "/api/auth/profile/",
            {"email": "different_email@evil.com"},
            format="json"
        )
        self.assertEqual(res_email.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res_email.data)

        # Verify DB values were not altered
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Jane")
        self.assertEqual(self.user.last_name, "Doe")
        self.assertEqual(self.user.email, "researcher@example.com")

    def test_staff_and_superuser_privileges_cannot_be_modified(self):
        """Attempts to escalate privileges via profile update return explicit validation errors."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        # Attempt to set is_staff=True
        res_staff = self.client.patch(
            "/api/auth/profile/",
            {"is_staff": True},
            format="json"
        )
        self.assertEqual(res_staff.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_staff", res_staff.data)

        # Attempt to set is_superuser=True
        res_super = self.client.patch(
            "/api/auth/profile/",
            {"is_superuser": True},
            format="json"
        )
        self.assertEqual(res_super.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_superuser", res_super.data)

        # Verify DB flags remain False
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_user_cannot_modify_another_users_account(self):
        """Users cannot supply another user's ID or target username to modify another account."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        # Attempt to supply other user's id
        res_id = self.client.patch(
            "/api/auth/profile/",
            {"id": self.other_user.id, "username": "victim_tampered"},
            format="json"
        )
        self.assertEqual(res_id.status_code, status.HTTP_403_FORBIDDEN)

        # Attempt to supply other user's user_id
        res_user_id = self.client.patch(
            "/api/auth/profile/",
            {"user_id": self.other_user.id, "username": "victim_tampered"},
            format="json"
        )
        self.assertEqual(res_user_id.status_code, status.HTTP_403_FORBIDDEN)

        # Attempt to supply target_username
        res_target = self.client.patch(
            "/api/auth/profile/",
            {"target_username": "other_researcher", "username": "victim_tampered"},
            format="json"
        )
        self.assertEqual(res_target.status_code, status.HTTP_403_FORBIDDEN)

        # Other user remains untouched
        self.other_user.refresh_from_db()
        self.assertEqual(self.other_user.username, "other_researcher")

    def test_existing_login_and_token_authentication_still_work_after_username_change(self):
        """After username change, existing token remains valid, and login works with new username and email."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        # 1. Update username
        res_update = self.client.patch(
            "/api/auth/profile/",
            {"username": "jane_updated_login"},
            format="json"
        )
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)

        # 2. Existing token still authenticates immediately
        res_me = self.client.get("/api/auth/me/")
        self.assertEqual(res_me.status_code, status.HTTP_200_OK)
        self.assertEqual(res_me.data["username"], "jane_updated_login")

        # 3. Can log in with the new username and original password
        self.client.credentials()  # Clear auth header
        res_new_login = self.client.post(
            "/api/auth/login/",
            {"username": "jane_updated_login", "password": self.raw_password},
            format="json"
        )
        self.assertEqual(res_new_login.status_code, status.HTTP_200_OK)
        self.assertEqual(res_new_login.data["user"]["username"], "jane_updated_login")
        self.assertEqual(res_new_login.data["token"], self.token.key)

        # 4. Can still log in with email and original password
        res_email_login = self.client.post(
            "/api/auth/login/",
            {"username": "researcher@example.com", "password": self.raw_password},
            format="json"
        )
        self.assertEqual(res_email_login.status_code, status.HTTP_200_OK)
        self.assertEqual(res_email_login.data["user"]["username"], "jane_updated_login")


class NForgeRegistrationAndAuthenticationTests(TestCase):
    """
    Tests covering registration fields (first_name, last_name, username, email,
    password, confirm_password), validation, duplicate username/email prevention,
    privilege escalation defense, and sign-in via username or email.
    """

    def setUp(self):
        self.client = APIClient()
        self.valid_payload = {
            "first_name": "Marie",
            "last_name": "Curie",
            "username": "marie_curie",
            "email": "marie.curie@radium.org",
            "password": "RadiumDiscovery123!",
            "confirm_password": "RadiumDiscovery123!",
        }

    def test_successful_registration_with_all_required_fields(self):
        """User registers with all required fields; name, email, and password hashing are verified."""
        res = self.client.post("/api/auth/register/", self.valid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["username"], "marie_curie")
        self.assertEqual(res.data["email"], "marie.curie@radium.org")
        self.assertEqual(res.data["first_name"], "Marie")
        self.assertEqual(res.data["last_name"], "Curie")
        self.assertNotIn("password", res.data)
        self.assertNotIn("confirm_password", res.data)

        # Verify DB entry
        user = User.objects.get(username="marie_curie")
        self.assertEqual(user.first_name, "Marie")
        self.assertEqual(user.last_name, "Curie")
        self.assertEqual(user.email, "marie.curie@radium.org")
        self.assertTrue(user.check_password("RadiumDiscovery123!"))
        self.assertNotEqual(user.password, "RadiumDiscovery123!")
        self.assertTrue(is_password_usable(user.password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_registration_privilege_escalation_prevention(self):
        """Privilege escalation fields (is_staff, is_superuser) in registration payload are rejected/ignored."""
        payload = dict(self.valid_payload)
        payload["is_staff"] = True
        payload["is_superuser"] = True
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="marie_curie")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_registration_password_mismatch_fails(self):
        """Mismatched confirm_password returns 400 Bad Request with field error."""
        payload = dict(self.valid_payload)
        payload["confirm_password"] = "DifferentPasswordXYZ999!"
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", res.data)
        self.assertFalse(User.objects.filter(username="marie_curie").exists())

    def test_registration_missing_first_and_last_name_fails(self):
        """Missing first or last name returns 400 Bad Request."""
        payload = dict(self.valid_payload)
        payload.pop("first_name")
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("first_name", res.data)

        payload2 = dict(self.valid_payload)
        payload2.pop("last_name")
        res2 = self.client.post("/api/auth/register/", payload2, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("last_name", res2.data)

    def test_registration_blank_names_rejected(self):
        """Whitespace-only names are rejected."""
        payload = dict(self.valid_payload)
        payload["first_name"] = "   "
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("first_name", res.data)

    def test_registration_invalid_email_format_rejected(self):
        """Invalid email format returns 400 Bad Request."""
        payload = dict(self.valid_payload)
        payload["email"] = "not-an-email-address"
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_registration_short_password_rejected(self):
        """Passwords shorter than 8 characters are rejected."""
        payload = dict(self.valid_payload)
        payload["password"] = "short1!"
        payload["confirm_password"] = "short1!"
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", res.data)

    def test_registration_duplicate_username_rejected(self):
        """Duplicate username returns 400 Bad Request."""
        self.client.post("/api/auth/register/", self.valid_payload, format="json")
        payload2 = dict(self.valid_payload)
        payload2["email"] = "different_email@lab.org"
        res = self.client.post("/api/auth/register/", payload2, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", res.data)

    def test_registration_duplicate_email_rejected(self):
        """Duplicate email (case-insensitive) returns 400 Bad Request."""
        self.client.post("/api/auth/register/", self.valid_payload, format="json")
        payload2 = dict(self.valid_payload)
        payload2["username"] = "different_username"
        payload2["email"] = "MARIE.CURIE@RADIUM.ORG"
        res = self.client.post("/api/auth/register/", payload2, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_sign_in_using_email_address_succeeds(self):
        """Users can sign in using their email address instead of username."""
        self.client.post("/api/auth/register/", self.valid_payload, format="json")

        login_res = self.client.post(
            "/api/auth/login/",
            {"username": "marie.curie@radium.org", "password": "RadiumDiscovery123!"},
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertIn("token", login_res.data)
        self.assertEqual(login_res.data["user"]["username"], "marie_curie")
        self.assertEqual(login_res.data["user"]["first_name"], "Marie")
        self.assertEqual(login_res.data["user"]["last_name"], "Curie")

    def test_sign_in_using_email_address_case_insensitive(self):
        """Email sign-in is case-insensitive."""
        self.client.post("/api/auth/register/", self.valid_payload, format="json")

        login_res = self.client.post(
            "/api/auth/login/",
            {"username": "MARIE.CURIE@RADIUM.ORG", "password": "RadiumDiscovery123!"},
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertIn("token", login_res.data)

    def test_sign_in_using_email_invalid_password_fails(self):
        """Email sign-in with wrong password returns 400 Bad Request."""
        self.client.post("/api/auth/register/", self.valid_payload, format="json")

        login_res = self.client.post(
            "/api/auth/login/",
            {"username": "marie.curie@radium.org", "password": "WrongPassword123!"},
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(login_res.data.get("error"), "Invalid Credentials")


