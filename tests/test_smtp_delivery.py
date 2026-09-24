"""Offline SMTP state-machine tests; never connect to a real mail server."""

import os
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import daily_updates as app


class SMTPDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_directory = os.getcwd()
        os.chdir(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(os.chdir, self.original_directory)
        self.ssl_patch = patch.object(app.smtplib, "SMTP_SSL")
        self.starttls_patch = patch.object(app.smtplib, "SMTP")
        self.primary = self.ssl_patch.start()
        self.secondary = self.starttls_patch.start()
        self.addCleanup(self.ssl_patch.stop)
        self.addCleanup(self.starttls_patch.stop)
        self.primary.return_value.sendmail.return_value = {}
        self.secondary.return_value.sendmail.return_value = {}
        self.cfg = app.Config("sender@example.com", "test-password", ("receiver@example.com",))

    def send(self):
        return app.send_email(self.cfg, "Subject", "Body", "<p>Body</p>")

    def fallback(self):
        return next(Path('.').glob('email_fallback_*.txt')).read_text()

    def test_connection_disconnect_uses_verified_starttls(self):
        self.primary.side_effect = app.smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
        self.assertTrue(self.send())
        self.secondary.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
        server = self.secondary.return_value
        context = server.starttls.call_args.kwargs["context"]
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        server.login.assert_called_once_with(self.cfg.sender_email, self.cfg.sender_password)
        server.sendmail.assert_called_once()
        self.assertFalse(list(Path('.').glob('email_fallback_*.txt')))

    def test_disconnect_during_login_can_fallback(self):
        self.primary.return_value.login.side_effect = app.smtplib.SMTPServerDisconnected("offline")
        self.assertTrue(self.send())
        self.primary.return_value.sendmail.assert_not_called()
        self.primary.return_value.close.assert_called_once()
        self.secondary.return_value.sendmail.assert_called_once()

    def test_authentication_rejection_is_not_retried(self):
        self.primary.return_value.login.side_effect = app.smtplib.SMTPAuthenticationError(535, b"Bad credentials")
        self.assertFalse(self.send())
        self.secondary.assert_not_called()
        self.assertIn("at authenticate", self.fallback())
        self.assertIn("Not submitted", self.fallback())

    def test_certificate_failure_is_not_retried(self):
        self.primary.side_effect = ssl.SSLCertVerificationError("certificate expired")
        self.assertFalse(self.send())
        self.secondary.assert_not_called()

    def test_disconnect_during_submission_is_ambiguous_and_not_retried(self):
        self.primary.return_value.sendmail.side_effect = app.smtplib.SMTPServerDisconnected("offline")
        self.assertFalse(self.send())
        self.secondary.assert_not_called()
        self.primary.return_value.sendmail.assert_called_once()
        self.assertIn("at sendmail", self.fallback())
        self.assertIn("Delivery partial or unknown", self.fallback())

    def test_partial_acceptance_is_not_retried(self):
        self.primary.return_value.sendmail.return_value = {"refused@example.com": (550, b"Rejected")}
        self.assertFalse(self.send())
        self.secondary.assert_not_called()
        self.assertIn("refused@example.com", self.fallback())
        self.assertIn("Do not resend to all recipients", self.fallback())

    def test_quit_failure_after_acceptance_is_success(self):
        self.primary.return_value.quit.side_effect = app.smtplib.SMTPServerDisconnected("offline")
        self.assertTrue(self.send())
        self.secondary.assert_not_called()
        self.assertFalse(list(Path('.').glob('email_fallback_*.txt')))

    def test_starttls_failure_never_sends_credentials(self):
        self.primary.side_effect = TimeoutError("offline")
        self.secondary.return_value.starttls.side_effect = app.smtplib.SMTPNotSupportedError("No TLS")
        self.assertFalse(self.send())
        self.secondary.return_value.login.assert_not_called()
        self.secondary.return_value.sendmail.assert_not_called()
        self.assertIn("at STARTTLS", self.fallback())

    def test_explicit_data_rejection_is_not_retried(self):
        self.primary.return_value.sendmail.side_effect = app.smtplib.SMTPDataError(451, b"Try later")
        self.assertFalse(self.send())
        self.secondary.assert_not_called()
        self.assertIn("SMTP rejected this submission", self.fallback())

    def test_permanent_connection_rejection_is_not_retried(self):
        self.primary.side_effect = app.smtplib.SMTPConnectError(554, b"Service unavailable")
        self.assertFalse(self.send())
        self.secondary.assert_not_called()

    def test_primary_connection_uses_certificate_verification(self):
        self.assertTrue(self.send())
        context = self.primary.call_args.kwargs["context"]
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.secondary.assert_not_called()

    def test_diagnostic_redacts_password(self):
        self.primary.return_value.login.side_effect = ValueError(self.cfg.sender_password)
        self.assertFalse(self.send())
        self.assertNotIn(self.cfg.sender_password, self.fallback())
        self.assertIn("[redacted]", self.fallback())
