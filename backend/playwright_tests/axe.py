"""Run axe-core against the current Playwright page."""

from playwright.sync_api import Page
from pytest_playwright_axe import Axe

# pytest-playwright-axe passes this through to axe.run() as JavaScript.
# WCAG 2.1 AA is the legal bar; 2.2 A/AA tags come along in the same run.
# "best-practice" is left out so the report maps to success criteria, not taste.
_WCAG_RUN_ONLY = "{runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22a', 'wcag22aa']}}"

_MAX_NODES = 5

_axe = Axe(use_minified_file=True)


def scan(page: Page) -> dict:
    return _axe.run(
        page,
        options=_WCAG_RUN_ONLY,
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
