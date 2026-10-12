"""
Security Package for Indian IPO Platform.
Exposes path sanitization, atomic file writers, environment validation,
and defensive input validation guards.
"""

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

__all__ = [
    "SecurityError",
    "PathTraversalError",
    "EnvironmentValidationError",
    "InputValidationError",
    "sanitize_path",
    "sanitize_filename",
    "validate_output_directory",
    "safe_write_file",
    "validate_env_var",
    "validate_safe_command_args",
]
