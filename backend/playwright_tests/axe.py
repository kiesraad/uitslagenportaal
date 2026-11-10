"""Run axe-core against the current Playwright page."""

import json

from playwright.sync_api import Page
from pytest_playwright_axe import Axe

# WCAG 2.1 AA is the legal bar; 2.2 A/AA tags come along in the same run.
_WCAG_TAGS = ("wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa")

# "best-practice" as a whole is left out so the report maps to success criteria, not taste.
# These single rules from it back a criterion or guard the page structure screen readers rely on;
# "region" is left out as too noisy for new sections outside the landmarks.
_BEST_PRACTICE_RULES = (
    "heading-order",
    "page-has-heading-one",
    "empty-heading",
    "landmark-one-main",
    "skip-link",
    "landmark-unique",
    "scope-attr-valid",
    "empty-table-header",
    "aria-allowed-role",
    "presentation-role-conflict",
    "tabindex",
)

# pytest-playwright-axe passes this through to axe.run() as JavaScript, which JSON is.
_AXE_OPTIONS = json.dumps(
    {
        "runOnly": {"type": "tag", "values": list(_WCAG_TAGS)},
        "rules": {rule: {"enabled": True} for rule in _BEST_PRACTICE_RULES},
    }
)

_MAX_NODES = 5

_axe = Axe(use_minified_file=True)


def scan(page: Page) -> dict:
    return _axe.run(
        page,
        options=_AXE_OPTIONS,
        html_report_generated=False,
        json_report_generated=False,
    )


def format_violations(results: dict) -> str:
    violations = results.get("violations") or []
    url = results.get("url", "")
    lines = [f"{len(violations)} axe violation(s) on {url}", ""]
    for violation in violations:
        impact = violation.get("impact") or "unknown"
        help_text = violation.get("help") or violation["id"]
        tags = ", ".join(tag for tag in violation.get("tags", []) if tag.startswith("wcag"))
        nodes = violation.get("nodes") or []
        lines.append(f"{violation['id']} ({impact}) [{tags}]")
        lines.append(f"  {help_text}")
        for node in nodes[:_MAX_NODES]:
            target = ", ".join(str(part) for part in (node.get("target") or []))
            lines.append(f"  - {target}")
        leftover = len(nodes) - _MAX_NODES
        if leftover > 0:
            lines.append(f"  - … {leftover} more")
        lines.append("")
    return "\n".join(lines).rstrip()


def assert_no_axe_violations(page: Page) -> None:
    results = scan(page)
    if results.get("violations"):
        raise AssertionError(format_violations(results))
