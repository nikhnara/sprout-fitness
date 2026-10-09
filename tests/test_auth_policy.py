import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
from auth_policy import owner_from_bearer

class OwnerAuthorizationTests(unittest.TestCase):
    def claims(self):
        return dict(uid='firebase-user-123', email='owner@example.com', email_verified=True,
                    firebase={'sign_in_provider': 'google.com'})
    def test_verified_owner_uses_stable_uid(self):
        self.assertEqual(owner_from_bearer('Bearer signed-token', 'OWNER@example.com', lambda _: self.claims()),
                         owner_from_bearer('Bearer refreshed-token', 'owner@example.com', lambda _: self.claims()))
    def test_wrong_account_unverified_or_wrong_provider_denied(self):
        for change in [dict(email='other@example.com'), dict(email_verified=False), dict(email_verified='true'),
                       dict(uid=''), dict(firebase={'sign_in_provider': 'password'})]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                owner_from_bearer('Bearer signed-token', 'owner@example.com', lambda _: {**self.claims(), **change})
    def test_sdk_verification_failure_cannot_authorize(self):
        def rejected(_):
            raise ValueError('Invalid signature, project, or expired token')
        with self.assertRaises(ValueError):
            owner_from_bearer('Bearer invalid-token', 'owner@example.com', rejected)
    def test_missing_or_malformed_bearer_does_not_call_verifier(self):
        def unexpected(_):
            self.fail('Malformed credentials reached verifier')
        for header in [None, '', 'signed-token', 'Basic token', 'Bearer ', 'Bearer a b']:
            with self.subTest(header=header), self.assertRaises(ValueError):
                owner_from_bearer(header, 'owner@example.com', unexpected)
