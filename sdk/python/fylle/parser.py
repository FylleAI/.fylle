"""
Parser for .fylle agent packages.

Handles unpacking ZIP archives, loading YAML/Markdown files,
and validating against Pydantic schemas.
"""

from __future__ import annotations

import hashlib
import os
import zipfile
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import yaml

from fylle.schema import (
    FylleAgent,
    FylleManifest,
    Guardrails,
    MemorySchema,
    Skill,
)

# Maximum package size: 10MB
MAX_PACKAGE_SIZE = 10 * 1024 * 1024

# Allowed file extensions inside a .fylle package
ALLOWED_EXTENSIONS = {".yaml", ".yml", ".md"}


class FylleParseError(Exception):
    """Raised when a .fylle package cannot be parsed."""
    pass


class FylleSecurityError(FylleParseError):
    """Raised when a .fylle package contains security issues."""
    pass


def parse_fylle_package(source: str | Path | BinaryIO) -> FylleAgent:
    """Parse a .fylle package and return a fully validated FylleAgent.

    Args:
        source: Path to a .fylle file, or a file-like object (BytesIO).

    Returns:
        FylleAgent with all components parsed and validated.

    Raises:
        FylleParseError: If the package is invalid or missing required files.
        FylleSecurityError: If the package contains security issues.
    """
    # Read the file into memory
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FylleParseError(f"File not found: {path}")
        file_size = path.stat().st_size
        if file_size > MAX_PACKAGE_SIZE:
            raise FylleSecurityError(
                f"Package too large: {file_size} bytes (max {MAX_PACKAGE_SIZE})"
            )
        file_bytes = path.read_bytes()
    else:
        file_bytes = source.read()
        if len(file_bytes) > MAX_PACKAGE_SIZE:
            raise FylleSecurityError(
                f"Package too large: {len(file_bytes)} bytes (max {MAX_PACKAGE_SIZE})"
            )

    # Compute SHA-256 hash
    package_hash = hashlib.sha256(file_bytes).hexdigest()

    # Open as ZIP
    try:
        zf = zipfile.ZipFile(BytesIO(file_bytes))
    except zipfile.BadZipFile:
        raise FylleParseError("Not a valid ZIP archive")

    # Security: check for path traversal (zip slip attack)
    _check_zip_security(zf)

    # Load required files
    manifest_data = _load_yaml_from_zip(zf, "manifest.yaml", required=True)
    personality = _load_text_from_zip(zf, None, required=False)  # loaded after manifest

    # Parse manifest
    try:
        manifest = FylleManifest(**manifest_data)
    except Exception as e:
        raise FylleParseError(f"Invalid manifest.yaml: {e}")

    # Load agent.md (the prompt file referenced in manifest)
    prompt_file = manifest.agent.prompt_file
    personality = _load_text_from_zip(zf, prompt_file, required=True)
    if not personality or not personality.strip():
        raise FylleParseError(f"System prompt file '{prompt_file}' is empty")

    # Load optional files
    guardrails = None
    guardrails_file = manifest.agent.guardrails.file
    if guardrails_file:
        guardrails_data = _load_yaml_from_zip(zf, guardrails_file, required=False)
        if guardrails_data and "guardrails" in guardrails_data:
            try:
                guardrails = Guardrails(**guardrails_data["guardrails"])
            except Exception as e:
                raise FylleParseError(f"Invalid {guardrails_file}: {e}")

    memory_schema = None
    if manifest.agent.memory:
        schema_file = manifest.agent.memory.schema_file
        memory_data = _load_yaml_from_zip(zf, schema_file, required=False)
        if memory_data and "memory" in memory_data:
            try:
                memory_schema = MemorySchema(**memory_data["memory"])
            except Exception as e:
                raise FylleParseError(f"Invalid {schema_file}: {e}")

    # Load skills
    skills = []
    for skill_ref in manifest.agent.skills:
        skill_data = _load_yaml_from_zip(zf, skill_ref.ref, required=True)
        if skill_data and "skill" in skill_data:
            try:
                skills.append(Skill(**skill_data["skill"]))
            except Exception as e:
                raise FylleParseError(f"Invalid skill {skill_ref.ref}: {e}")

    # Load README (optional, not validated)
    readme = _load_text_from_zip(zf, "README.md", required=False)

    zf.close()

    return FylleAgent(
        manifest=manifest,
        personality=personality,
        skills=skills,
        guardrails=guardrails,
        memory_schema=memory_schema,
        readme=readme,
        package_hash=package_hash,
    )


def unpack_fylle_to_dir(source: str | Path, output_dir: str | Path) -> str:
    """Extract a .fylle package to a directory for inspection.

    Args:
        source: Path to a .fylle file.
        output_dir: Directory to extract into.

    Returns:
        Path to the output directory.

    Raises:
        FylleParseError: If the file is invalid.
        FylleSecurityError: If the package contains path traversal.
    """
    source = Path(source)
    output_dir = Path(output_dir)

    if not source.exists():
        raise FylleParseError(f"File not found: {source}")

    file_size = source.stat().st_size
    if file_size > MAX_PACKAGE_SIZE:
        raise FylleSecurityError(
            f"Package too large: {file_size} bytes (max {MAX_PACKAGE_SIZE})"
        )

    try:
        zf = zipfile.ZipFile(source)
    except zipfile.BadZipFile:
        raise FylleParseError("Not a valid ZIP archive")

    _check_zip_security(zf)

    output_dir.mkdir(parents=True, exist_ok=True)
    zf.extractall(output_dir)
    zf.close()

    return str(output_dir)


# ============================================================
# Internal helpers
# ============================================================

def _check_zip_security(zf: zipfile.ZipFile) -> None:
    """Check a ZIP file for security issues."""
    for info in zf.infolist():
        # Path traversal check
        if ".." in info.filename or info.filename.startswith("/"):
            raise FylleSecurityError(
                f"Dangerous path in archive: '{info.filename}' (possible zip slip attack)"
            )
        # Check file extensions
        ext = os.path.splitext(info.filename)[1].lower()
        basename = os.path.basename(info.filename)
        # Allow directories (no extension) and allowed file types
        if ext and ext not in ALLOWED_EXTENSIONS and basename != "":
            raise FylleSecurityError(
                f"Disallowed file type in archive: '{info.filename}' "
                f"(allowed: {', '.join(ALLOWED_EXTENSIONS)})"
            )


def _load_yaml_from_zip(
    zf: zipfile.ZipFile, filename: str, required: bool = False
) -> dict | None:
    """Load and parse a YAML file from a ZIP archive."""
    try:
        with zf.open(filename) as f:
            content = f.read().decode("utf-8")
            return yaml.safe_load(content)
    except KeyError:
        if required:
            raise FylleParseError(f"Required file missing: {filename}")
        return None
    except yaml.YAMLError as e:
        raise FylleParseError(f"Invalid YAML in {filename}: {e}")


def _load_text_from_zip(
    zf: zipfile.ZipFile, filename: str | None, required: bool = False
) -> str | None:
    """Load a text file from a ZIP archive."""
    if filename is None:
        return None
    try:
        with zf.open(filename) as f:
            return f.read().decode("utf-8")
    except KeyError:
        if required:
            raise FylleParseError(f"Required file missing: {filename}")
        return None
