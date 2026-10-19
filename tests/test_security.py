"""
Unit Tests for Platform Security Hardening.
Verifies path sanitization, directory traversal rejection, safe atomic file writes,
environment variable validation, and defensive input guards.
"""

import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ipo_platform.security.hardening import (
    EnvironmentValidationError,
    InputValidationError,
    PathTraversalError,
    SecurityError,
    safe_write_file,
    sanitize_filename,
    sanitize_path,
    validate_env_var,
    validate_output_directory,
    validate_safe_command_args,
)


class TestSecurityHardening(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name).resolve()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sanitize_path_within_base_directory(self):
        # Valid path inside base_dir
        safe_path = sanitize_path("reports/daily/report.md", base_dir=self.base_dir)
        self.assertTrue(safe_path.is_relative_to(self.base_dir))
        self.assertEqual(safe_path.name, "report.md")

    def test_sanitize_path_rejects_directory_traversal(self):
        traversal_attempts = [
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "reports/../../../secret_keys.env",
            "subdir/../../../../outside.txt",
            "subdir/..\\../mixed/../../outside.txt",
            "/etc/passwd",
            "\\\\attacker-server\\share\\data.txt",
            "//attacker-server/share/data.txt",
        ]

        for bad_path in traversal_attempts:
            with self.assertRaises(PathTraversalError):
                sanitize_path(bad_path, base_dir=self.base_dir)

    def test_sanitize_path_rejects_prefix_lookalike_directory(self):
        # Prevent /base_dir-lookalike from bypassing prefix check
        lookalike_path = str(self.base_dir) + "-evil" + os.sep + "payload.txt"
        with self.assertRaises(PathTraversalError):
            sanitize_path(lookalike_path, base_dir=self.base_dir, allow_absolute=True)

    def test_sanitize_path_missing_base_dir_fails_closed(self):
        # Without base_dir or IPO_TRUSTED_BASE_DIR, fails closed
        old_env = os.environ.pop("IPO_TRUSTED_BASE_DIR", None)
        try:
            with self.assertRaises(PathTraversalError):
                sanitize_path("some_file.txt", base_dir=None)
        finally:
            if old_env is not None:
                os.environ["IPO_TRUSTED_BASE_DIR"] = old_env

    def test_sanitize_path_configured_trusted_base_env(self):
        os.environ["IPO_TRUSTED_BASE_DIR"] = str(self.base_dir)
        try:
            safe = sanitize_path("sub/report.md", base_dir=None)
            self.assertTrue(safe.is_relative_to(self.base_dir))
        finally:
            del os.environ["IPO_TRUSTED_BASE_DIR"]

    def test_sanitize_path_rejects_null_bytes(self):
        with self.assertRaises(PathTraversalError):
            sanitize_path("valid_file.txt\x00.exe", base_dir=self.base_dir)

    def test_sanitize_path_symlink_outside_base_rejected(self):
        # Create external target
        external_dir = tempfile.TemporaryDirectory()
        try:
            external_file = Path(external_dir.name) / "secret.txt"
            external_file.write_text("classified", encoding="utf-8")

            symlink_path = self.base_dir / "symlink_to_external"
            try:
                symlink_path.symlink_to(external_file)
            except (OSError, NotImplementedError):
                # Symlinks may require admin privileges on Windows; skip if OS forbids
                return

            with self.assertRaises(PathTraversalError):
                sanitize_path(symlink_path, base_dir=self.base_dir)
        finally:
            external_dir.cleanup()

    def test_sanitize_filename(self):
        # Cleans disallowed characters and paths
        clean_name = sanitize_filename("../../malicious:file<name>.csv")
        self.assertNotIn("/", clean_name)
        self.assertNotIn("\\", clean_name)
        self.assertNotIn("<", clean_name)
        self.assertNotIn(":", clean_name)
        self.assertTrue(clean_name.endswith(".csv"))

        # Rejects empty or reserved names
        with self.assertRaises(InputValidationError):
            sanitize_filename("..")
        with self.assertRaises(InputValidationError):
            sanitize_filename("")

    def test_validate_output_directory(self):
        out_dir = self.base_dir / "exports" / "2026"
        validated = validate_output_directory(out_dir, base_dir=self.base_dir, create_if_missing=True)
        self.assertTrue(validated.exists())
        self.assertTrue(validated.is_dir())

        # Attempt to create directory outside base_dir must fail
        with self.assertRaises(PathTraversalError):
            validate_output_directory("../../outside_folder", base_dir=self.base_dir)

    def test_safe_atomic_file_write(self):
        dest_file = self.base_dir / "output" / "atomic.txt"
        test_content = "Safe atomic output data"

        written_path = safe_write_file(dest_file, test_content, base_dir=self.base_dir, overwrite=True)
        self.assertTrue(written_path.exists())
        self.assertEqual(written_path.read_text(encoding="utf-8"), test_content)

        # Overwrite=False prevents collision
        with self.assertRaises(FileExistsError):
            safe_write_file(dest_file, "New data", base_dir=self.base_dir, overwrite=False)

        # Attempting to write outside base_dir must fail
        with self.assertRaises(PathTraversalError):
            safe_write_file("../../etc/shadow", "data", base_dir=self.base_dir)

    def test_validate_env_var(self):
        os.environ["TEST_SECURITY_PORT"] = "8080"
        os.environ["TEST_SECURITY_MODE"] = "production"

        # Valid checks
        val_port = validate_env_var("TEST_SECURITY_PORT", pattern=r"^\d+$")
        self.assertEqual(val_port, "8080")

        val_mode = validate_env_var("TEST_SECURITY_MODE", allowed_values=["development", "production"])
        self.assertEqual(val_mode, "production")

        # Pattern mismatch
        with self.assertRaises(EnvironmentValidationError):
            validate_env_var("TEST_SECURITY_MODE", pattern=r"^\d+$")

        # Allowed values violation
        with self.assertRaises(EnvironmentValidationError):
            validate_env_var("TEST_SECURITY_MODE", allowed_values=["staging", "test"])

        # Required missing variable
        with self.assertRaises(EnvironmentValidationError):
            validate_env_var("NON_EXISTENT_SECURITY_KEY", required=True)

    def test_validate_safe_command_args(self):
        self.assertTrue(validate_safe_command_args(["ipo-cli", "list", "--status", "CURRENTLY_OPEN"]))

        with self.assertRaises(SecurityError):
            validate_safe_command_args(["ipo-cli", "ingest\x00--malicious"])

        with self.assertRaises(InputValidationError):
            validate_safe_command_args([])


if __name__ == "__main__":
    unittest.main()
