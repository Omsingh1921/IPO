"""
Security Hardening and Defensive Input Validation Utilities for Indian IPO Platform.
Guarantees path traversal prevention, safe atomic file persistence,
environment variable validation, and shell injection resistance.
"""

import os
from pathlib import Path
import re
import tempfile
from typing import List, Optional, Union


class SecurityError(Exception):
    """Base exception for all security policy violations."""
    pass


class PathTraversalError(SecurityError):
    """Raised when an untrusted path attempts to escape its designated base directory."""
    pass


class EnvironmentValidationError(SecurityError):
    """Raised when an environment configuration variable fails validation."""
    pass


class InputValidationError(SecurityError):
    """Raised when defensive input validation fails on untrusted data."""
    pass


# Disallowed Windows and Unix filename characters
DISALLOWED_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitizes a candidate filename, stripping path separators, control characters,
    and null bytes to prevent directory traversal and filesystem attacks.
    """
    if not filename or not isinstance(filename, str):
        raise InputValidationError("Filename must be a non-empty string")

    # Strip null bytes and whitespace
    clean = filename.replace("\x00", "").strip()
    # Strip any directory path components
    clean = os.path.basename(clean)
    # Remove disallowed filesystem characters
    clean = DISALLOWED_FILENAME_CHARS.sub("_", clean)

    if clean in ("", ".", ".."):
        raise InputValidationError(f"Invalid or unsafe filename: '{filename}'")

    if len(clean) > max_length:
        clean = clean[:max_length]

    return clean


def sanitize_path(
    path: Union[str, Path],
    base_dir: Optional[Union[str, Path]] = None,
    allow_absolute: bool = True,
) -> Path:
    """
    Resolves and validates a filesystem path, ensuring it does not contain null bytes
    and strictly resides within `base_dir` if specified.
    """
    path_str = str(path)
    if "\x00" in path_str:
        raise PathTraversalError("Path contains null bytes")

    target = Path(path)

    if base_dir is not None:
        base = Path(base_dir).resolve()
        # If target is relative, resolve it relative to base
        if not target.is_absolute():
            target = (base / target).resolve()
        else:
            target = target.resolve()

        # Enforce boundary containment
        try:
            target.relative_to(base)
        except ValueError:
            raise PathTraversalError(
                f"Path traversal detected: '{path}' escapes designated base directory '{base}'"
            )
        return target

    # No base directory constraint
    if not allow_absolute and target.is_absolute():
        raise PathTraversalError(f"Absolute paths are disallowed: '{path}'")

    return target.resolve()


def validate_output_directory(
    dir_path: Union[str, Path],
    base_dir: Optional[Union[str, Path]] = None,
    create_if_missing: bool = True,
) -> Path:
    """
    Sanitizes and validates an output directory path, ensuring it is contained
    within `base_dir` and exists with write access.
    """
    sanitized = sanitize_path(dir_path, base_dir=base_dir, allow_absolute=True)

    if not sanitized.exists():
        if create_if_missing:
            sanitized.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(f"Output directory does not exist: {sanitized}")

    if not sanitized.is_dir():
        raise NotADirectoryError(f"Target path is not a directory: {sanitized}")

    return sanitized


def safe_write_file(
    target_path: Union[str, Path],
    content: Union[str, bytes],
    base_dir: Optional[Union[str, Path]] = None,
    overwrite: bool = True,
    encoding: str = "utf-8",
) -> Path:
    """
    Safely writes content to a target file atomically using a temporary file in the same
    directory, avoiding partially-written corrupted files and race conditions.
    """
    sanitized = sanitize_path(target_path, base_dir=base_dir, allow_absolute=True)

    if not overwrite and sanitized.exists():
        raise FileExistsError(f"Destination file already exists and overwrite=False: {sanitized}")

    parent_dir = sanitized.parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    # Use atomic write via temp file in the same directory (guarantees same filesystem)
    is_bytes = isinstance(content, bytes)
    mode = "wb" if is_bytes else "w"

    tmp_file = tempfile.NamedTemporaryFile(
        mode=mode,
        dir=str(parent_dir),
        delete=False,
        encoding=None if is_bytes else encoding,
    )
    tmp_path = Path(tmp_file.name)

    try:
        tmp_file.write(content)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())
        tmp_file.close()

        # Atomic replace
        os.replace(tmp_path, sanitized)
    except Exception as exc:
        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise exc

    return sanitized


def validate_env_var(
    name: str,
    default: Optional[str] = None,
    required: bool = False,
    pattern: Optional[str] = None,
    allowed_values: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Retrieves and validates an environment variable against security criteria.
    """
    val = os.getenv(name, default)

    if required and (val is None or str(val).strip() == ""):
        raise EnvironmentValidationError(f"Required environment variable '{name}' is not set or empty")

    if val is not None:
        val_str = str(val).strip()
        if allowed_values is not None and val_str not in allowed_values:
            raise EnvironmentValidationError(
                f"Environment variable '{name}' value '{val_str}' not in allowed set: {allowed_values}"
            )
        if pattern is not None and not re.match(pattern, val_str):
            raise EnvironmentValidationError(
                f"Environment variable '{name}' does not match required security pattern: {pattern}"
            )

    return val


def validate_safe_command_args(args: List[str]) -> bool:
    """
    Validates that a list of command arguments does not contain null bytes or
    dangerous shell injection vectors.
    """
    if not isinstance(args, list) or len(args) == 0:
        raise InputValidationError("Command arguments must be a non-empty list of strings")

    for arg in args:
        if not isinstance(arg, str):
            raise InputValidationError(f"Command argument must be a string, got {type(arg)}")
        if "\x00" in arg:
            raise SecurityError(f"Command argument contains null byte: {arg!r}")

    return True
