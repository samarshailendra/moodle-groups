"""
Add students to existing Moodle groups from a CSV file.

Author: Samar Shailendra
License: GPL v3.0
"""

from __future__ import annotations

import csv
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING, OrderedDict as OrderedDictType

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page, Playwright

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:
    PlaywrightError = PlaywrightTimeoutError = RuntimeError
    sync_playwright = None


MOODLE_URL = "https://moodle.mit.edu.au"
LOGIN_URL = f"{MOODLE_URL}/login/index.php"
WAIT_SECONDS = 20


class MoodleAutomationError(RuntimeError):
    """Raised when Moodle cannot complete an update safely."""


class CsvFormatError(ValueError):
    """Raised when a group-membership CSV does not have the required shape."""


def normalise_group_name(group_name: str) -> str:
    """Remove Moodle's displayed member count from a group name."""
    return re.sub(r"\s*\(\d+\)$", "", group_name).strip()


def is_header(row: list[str]) -> bool:
    """Return whether a row is the optional GroupName, StudentId header."""
    if len(row) < 2:
        return False

    group_column = row[0].strip().lower().replace(" ", "")
    student_columns = [value.strip().lower().replace(" ", "") for value in row[1:]]
    return group_column == "groupname" and all(
        value in {"studentid", "studentids"} for value in student_columns if value
    )


def load_group_memberships(csv_path: Path) -> OrderedDictType[str, list[str]]:
    """
    Read either supported CSV layout into ordered group-to-student-ID mappings.

    Supported rows are ``GroupName,StudentId,StudentId,...`` and repeated
    ``GroupName,StudentId`` rows. A GroupName/StudentId header is optional.
    """
    groups: OrderedDictType[str, list[str]] = OrderedDict()

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            rows = list(csv.reader(csv_file))
    except OSError as error:
        raise CsvFormatError(f"Cannot read '{csv_path}': {error}") from error
    except csv.Error as error:
        raise CsvFormatError(f"Cannot parse '{csv_path}' as CSV: {error}") from error

    for line_number, row in enumerate(rows, start=1):
        values = [value.strip() for value in row]
        if not any(values):
            continue
        if line_number == 1 and is_header(values):
            continue
        if len(values) < 2 or not values[0] or not any(values[1:]):
            raise CsvFormatError(
                f"Line {line_number} must contain a group name followed by at least one student ID."
            )
        if any(not student_id for student_id in values[1:]):
            raise CsvFormatError(
                f"Line {line_number} contains an empty student ID. Remove empty columns or provide an ID."
            )

        student_ids = groups.setdefault(values[0], [])
        for student_id in values[1:]:
            if student_id not in student_ids:
                student_ids.append(student_id)

    if not groups:
        raise CsvFormatError("The CSV contains no group memberships.")
    return groups


def ask_to_retry_or_exit() -> None:
    """Ask whether to correct the current input or leave the program."""
    if input("Provide another file? (y/N): ").strip().lower() != "y":
        print("Exiting.")
        sys.exit(1)


def prompt_for_csv_file(unit_code: str) -> tuple[Path, OrderedDictType[str, list[str]]]:
    """Prompt for and validate one CSV, defaulting to <UnitCode>.csv."""
    default_name = f"{unit_code}.csv"
    print(
        "CSV format: GroupName,StudentId,StudentId,... on one row, or repeat "
        "GroupName,StudentId on multiple rows. A GroupName,StudentId header is optional."
    )

    while True:
        file_name = input(f"CSV file name or path [{default_name}]: ").strip() or default_name
        csv_path = Path(file_name).expanduser()
        try:
            return csv_path, load_group_memberships(csv_path)
        except CsvFormatError as error:
            print(f"CSV error: {error}")
            ask_to_retry_or_exit()


def create_browser() -> tuple[Playwright, Browser, Page]:
    """
    Start the Chromium browser bundled with the application.

    PLAYWRIGHT_BROWSERS_PATH=0 uses Playwright's hermetic browser location. The
    build workflow places Chromium there, and PyInstaller bundles it with the
    executable, so end users do not install a browser or a browser driver.
    """
    if sync_playwright is None:
        raise MoodleAutomationError(
            "Playwright is required to build or run the source. Install the dependencies with "
            "'python3 -m pip install -r requirements.txt'."
        )

    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        print("Opened the bundled Chromium browser.")
        return playwright, browser, page
    except PlaywrightError as error:
        raise MoodleAutomationError(f"Could not start the bundled browser: {error}") from error


def login_to_moodle(page: Page) -> None:
    """Open Moodle and wait for the user to complete their normal visible login."""
    print("Opening Moodle. Complete your normal OAuth or username/password login in the browser window.")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    try:
        page.wait_for_function(
            """() => window.location.hostname === "moodle.mit.edu.au"
                && !window.location.pathname.includes("/login/")""",
            timeout=120_000,
        )
    except PlaywrightTimeoutError as error:
        raise MoodleAutomationError("Moodle login did not complete within two minutes.") from error
    print("Moodle login successful.")


def get_group_mapping(page: Page, unit_id: int) -> dict[str, str]:
    """Return existing Moodle groups and their internal IDs for one unit."""
    page.goto(f"{MOODLE_URL}/group/index.php?id={unit_id}", wait_until="domcontentloaded")
    try:
        page.locator("#groups").wait_for(state="attached", timeout=WAIT_SECONDS * 1000)
        group_options = page.locator("#groups option")
        group_mapping = {}
        for index in range(group_options.count()):
            option = group_options.nth(index)
            group_id = option.get_attribute("value")
            if group_id:
                group_mapping[normalise_group_name(option.text_content() or "")] = group_id
        return group_mapping
    except PlaywrightTimeoutError as error:
        raise MoodleAutomationError(
            f"Could not load groups for Moodle unit ID {unit_id}. Check the unit ID and your permissions."
        ) from error
    except PlaywrightError as error:
        raise MoodleAutomationError(f"Could not read Moodle groups: {error}") from error


def validate_groups_exist(
    group_memberships: OrderedDictType[str, list[str]],
    group_mapping: dict[str, str],
    unit_code: str,
) -> None:
    """Fail before updates if any CSV group is absent from Moodle."""
    missing_groups = [
        group_name
        for group_name in group_memberships
        if normalise_group_name(group_name) not in group_mapping
    ]
    if missing_groups:
        raise MoodleAutomationError(
            f"These groups do not exist in Moodle for {unit_code}: {', '.join(missing_groups)}. "
            "Create them in Moodle or correct the CSV, then try again."
        )


def add_students_to_group(page: Page, group_id: str, student_ids: list[str]) -> None:
    """Add the provided student IDs to an existing Moodle group."""
    page.goto(f"{MOODLE_URL}/group/members.php?group={group_id}", wait_until="domcontentloaded")
    try:
        auto_select = page.locator("#userselector_autoselectuniqueid")
        auto_select.wait_for(state="visible", timeout=WAIT_SECONDS * 1000)
        if not auto_select.is_checked():
            auto_select.check()

        search_box = page.locator("#addselect_searchtext")
        matching_students = page.locator("#addselect option")
        add_button = page.locator("#add")
        for student_id in student_ids:
            print(f"Adding student: {student_id}")
            search_box.fill(student_id)
            search_box.press("Enter")
            matching_students.first.wait_for(state="attached", timeout=WAIT_SECONDS * 1000)
            add_button.click()
    except PlaywrightTimeoutError as error:
        raise MoodleAutomationError(
            "Moodle did not return a matching student in time. Check the student ID and try again."
        ) from error
    except PlaywrightError as error:
        raise MoodleAutomationError(f"Could not add a student to the group: {error}") from error


def process_unit(
    page: Page,
    unit_code: str,
    unit_id: int,
    group_memberships: OrderedDictType[str, list[str]],
) -> None:
    """Validate all named Moodle groups, then add every requested student."""
    group_mapping = get_group_mapping(page, unit_id)
    validate_groups_exist(group_memberships, group_mapping, unit_code)

    for group_name, student_ids in group_memberships.items():
        print(f"Adding members to group: {group_name}")
        add_students_to_group(page, group_mapping[normalise_group_name(group_name)], student_ids)


def prompt_for_unit_info() -> tuple[str, int, Path, OrderedDictType[str, list[str]]]:
    """Prompt for one unit and its one group-membership CSV."""
    while True:
        unit_code = input("Unit code (for example, MITS5001): ").strip()
        if unit_code:
            break
        print("A unit code is required.")

    while True:
        unit_id = input("Moodle unit ID (numbers only): ").strip()
        if unit_id.isdigit():
            break
        print("Invalid Moodle unit ID. Enter numbers only.")

    csv_path, group_memberships = prompt_for_csv_file(unit_code)
    return unit_code, int(unit_id), csv_path, group_memberships


def main() -> None:
    """Run visible Moodle group updates for one or more units."""
    playwright = browser = page = None
    try:
        playwright, browser, page = create_browser()
        login_to_moodle(page)

        while True:
            unit_code, unit_id, csv_path, group_memberships = prompt_for_unit_info()
            print(f"Processing {unit_code} from '{csv_path}'.")
            process_unit(page, unit_code, unit_id, group_memberships)
            print(f"Completed {unit_code}.")

            if input("Process another unit? (y/N): ").strip().lower() != "y":
                break
    except MoodleAutomationError as error:
        print(f"Error: {error}")
        sys.exit(1)
    finally:
        if browser is not None:
            browser.close()
        if playwright is not None:
            playwright.stop()

    print("All done.")


if __name__ == "__main__":
    main()
