"""Checks on the files the release workflow and HACS depend on."""
from __future__ import annotations

import json
import re
from pathlib import Path

from custom_components.water_softener_salt_tracker.const import DOMAIN

ROOT = Path(__file__).parent.parent
MANIFEST = json.loads(
    (ROOT / "custom_components" / DOMAIN / "manifest.json").read_text()
)


def test_manifest_version_is_semver() -> None:
    """The release workflow needs a plain X.Y.Z version."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", MANIFEST["version"])
    assert MANIFEST["domain"] == DOMAIN


def test_changelog_has_section_for_current_version() -> None:
    """Every release needs notes: a "## vX.Y.Z" section with some content."""
    changelog = (ROOT / "CHANGELOG.md").read_text()
    heading = f"## v{MANIFEST['version']}"
    sections = re.split(r"^## ", changelog, flags=re.MULTILINE)
    matching = [s for s in sections if f"## {s}".startswith(heading + "\n")]
    assert matching, f"CHANGELOG.md has no '{heading}' section"
    assert matching[0].split("\n", 1)[1].strip(), f"'{heading}' section is empty"


def test_minimum_version_is_the_one_tested() -> None:
    """hacs.json's minimum Home Assistant must match what CI tests against."""
    minimum = json.loads((ROOT / "hacs.json").read_text())["homeassistant"]
    requirements = (ROOT / "requirements_test_min.txt").read_text()
    assert f"homeassistant=={minimum}" in requirements
