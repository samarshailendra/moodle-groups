'''
Author: Samar Shailendra
License: GPL v3.0
'''
import os
import platform
import subprocess
import sys
import time
import pandas as pd
from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
import getpass
import re
import zipfile
import urllib.request
import shutil
import stat
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


# Suppress GetPassWarning
# warnings.filterwarnings('ignore', category=getpass.GetPassWarning)

def graceful_exit(driver, message):
    """Function to gracefully exit with an error message."""
    print(f"Error: {message}")
    driver.quit()
    exit(1)


def login_to_moodle(driver):
    """Open Moodle login page and wait for manual login to complete."""
    print("Opening Moodle login page... Please log in manually.")
    driver.get("https://moodle.mit.edu.au/login/index.php")

    try:
        # Wait until user is logged in by detecting a page change
        WebDriverWait(driver, 120).until(lambda d: "login" not in d.current_url.lower())

        print("Login successful. Continuing automation...")
    except Exception as e:
        driver.save_screenshot("login_debug_manual.png")
        graceful_exit(driver, f"Login not detected after timeout. Error: {e}")


def get_group_mapping(driver, unit_id):
    """Function to create a mapping of group names to their values for a given unit."""
    group_mapping = {}
    group_management_url = f"https://moodle.mit.edu.au/group/index.php?id={unit_id}"
    driver.get(group_management_url)
    time.sleep(2)  # Wait for the page to load

    try:
        select_element = driver.find_element(By.ID, 'groups')
        options = select_element.find_elements(By.TAG_NAME, 'option')
        for option in options:
            group_name = re.sub(r'\s*\(\d+\)$', '', option.text)  # Clean up group name
            group_value = option.get_attribute('value')
            group_mapping[group_name] = group_value
    except Exception as e:
        graceful_exit(f"Failed to create group mapping for unit ID {unit_id}: {e}")

    return group_mapping


def ensure_auto_select_checkbox(driver):
    """
    Ensures the checkbox 'If only one user matches the search, select them automatically' is selected
    by explicitly checking the 'checked' attribute.
    """
    try:
        # Locate the checkbox by its ID
        auto_select_checkbox = driver.find_element(By.ID, 'userselector_autoselectuniqueid')

        # Bring the checkbox into view (focus) before interacting
        driver.execute_script("arguments[0].scrollIntoView(true);", auto_select_checkbox)

        # Retrieve the 'checked' attribute
        is_checked = auto_select_checkbox.get_attribute("checked")

        # If 'checked' is None or False, the checkbox is not selected
        if is_checked is None or is_checked.lower() != "true":
            auto_select_checkbox.click()
            print(
                "Checkbox 'If only one user matches the search, select them automatically' was not selected. Now selected.")
        # else:
        #    print("Checkbox 'If only one user matches the search, select them automatically' is already selected.")
    except Exception as e:
        graceful_exit(driver, f"Failed to locate or interact with the checkbox: {e}")


def add_students_to_group(driver, group_value, student_names):
    """Function to add multiple students to a group."""
    add_student_url = f"https://moodle.mit.edu.au/group/members.php?group={group_value}"
    driver.get(add_student_url)
    time.sleep(1)  # Wait for the page to load

    # Ensure the autoselect single output checkbox is selected
    ensure_auto_select_checkbox(driver)

    for student_name in student_names:
        print(f"Adding Student: {student_name}")
        try:
            search_box = driver.find_element(By.ID, 'addselect_searchtext')
            search_box.clear()
            search_box.send_keys(student_name)
            search_box.send_keys(Keys.RETURN)
            time.sleep(1)  # Wait for search results

            add_button = driver.find_element(By.ID, 'add')
            add_button.click()
            time.sleep(1)  # Wait for the student to be added
        except Exception as e:
            graceful_exit(driver, f"Failed to add student '{student_name}' to group with value '{group_value}': {e}")


def process_unit(driver, unit_dir, unit_name, unit_id):
    """Function to process each unit: read group file, map groups, and add students."""
    group_mapping = get_group_mapping(driver, unit_id)

    if unit_dir is None:
        group_file = f"{unit_name}_groups.csv"
    else:
        group_file = unit_dir + "/" + f"{unit_name}_groups.csv"

    try:
        group_df = pd.read_csv(group_file)
    except Exception as e:
        graceful_exit(driver, f"Failed to read {group_file}: {e}")

    for index, group_row in group_df.iterrows():
        group_name = group_row.iloc[0]  # First column is the group name
        student_names = group_row.iloc[1:].dropna().tolist()  # Other columns are student names

        if group_name not in group_mapping:
            graceful_exit(driver, f"Group name '{group_name}' not found in mapping for unit {unit_name}")

        print(f"Adding the members for Group: {group_name}")

        group_value = group_mapping[group_name]
        add_students_to_group(driver, group_value, student_names)


def prompt_for_unit_info():
    """Prompt the user for unit name and Moodle unit ID, then locate the corresponding CSV."""
    unit_name = input("Enter the Unit Name (e.g., MITS5001): ").strip()

    while True:
        unit_id_input = input("Enter the Moodle Unit ID (numeric only): ").strip()
        if unit_id_input.isdigit():
            unit_id = int(unit_id_input)
            break
        else:
            print("Invalid Unit ID. Please enter a numeric value.")

    # Look for "<unit_name>_groups.csv" in current directory
    group_file = f"{unit_name}_groups.csv"
    unit_dir = None

    if not os.path.exists(group_file):
        # Ask user for directory
        while True:
            file_dir = input(f"File '{group_file}' not found. Enter the full folder path of the file: ").strip()
            custom_path = os.path.join(file_dir, group_file)

            if os.path.exists(custom_path):
                unit_dir = file_dir
                break
            else:
                print(f"File not found at '{custom_path}'.")
                retry = input("Do you want to try again? (y/N): ").strip().lower()
                if retry != 'y':
                    print("Exiting...")
                    exit(1)

    return unit_name, unit_id, unit_dir


# This method is not used anymore
def get_chromedriver_path():
    default_path = os.path.join(os.getcwd(), 'chromedriver')

    if os.path.exists(default_path):
        return default_path

    while True:
        chromedriver_dir = input(
            "Default Chromedriver Not found, Enter the Full path to ChromeDriver EXE (including the executable name) : ")
        custom_path = chromedriver_dir  # + "//chromedriver"
        print(custom_path)
        if os.path.exists(custom_path):
            return custom_path
        else:
            retry = input(
                "Path Not Found ! Do you want to try again? (y/N): ").strip().lower()
            if retry != 'y':
                print("Exiting...")
                exit(1)


def get_chrome_version():
    system = platform.system()
    version = None
    try:
        if system == "Windows":
            output = subprocess.check_output(
                r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version',
                shell=True).decode()
            version = re.search(r"(\d+\.\d+\.\d+\.\d+)", output).group(1)
        elif system == "Linux":
            output = subprocess.check_output(["google-chrome", "--version"]).decode()
            version = re.search(r"(\d+\.\d+\.\d+\.\d+)", output).group(1)
    except Exception as e:
        print(f"Could not detect Chrome version: {e}")
        sys.exit(1)

    return version


def get_chromedriver_download_url(version, os_name):
    base_url = "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing"
    version_main = ".".join(version.split('.')[:3])
    if os_name == "Windows":
        return f"{base_url}/{version}/win64/chromedriver-win64.zip"
    elif os_name == "Linux":
        return f"{base_url}/{version}/linux64/chromedriver-linux64.zip"
    else:
        raise Exception("Unsupported OS for ChromeDriver download")


def setup_chrome_driver():
    os_name = platform.system()
    chrome_version = get_chrome_version()  # You must define this function separately
    version_tag = chrome_version.replace(".", "_")
    driver_dir = os.path.join(os.getcwd(), f"chromedriver_{os_name}_v{version_tag}")
    driver_bin = "chromedriver.exe" if os_name == "Windows" else "chromedriver"
    driver_path = os.path.join(driver_dir, driver_bin)

    if os.path.exists(driver_path):
        print(f"✅ Found existing ChromeDriver for version {chrome_version}")
    else:
        print(f"⬇️  Downloading ChromeDriver for version {chrome_version}...")

        download_url = get_chromedriver_download_url(chrome_version, os_name)  # Define this as well
        zip_path = os.path.join(driver_dir, "chromedriver.zip")
        os.makedirs(driver_dir, exist_ok=True)

        try:
            urllib.request.urlretrieve(download_url, zip_path)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(driver_dir)

            os.remove(zip_path)

            # Search for chromedriver inside the extracted structure
            found = False
            for root, dirs, files in os.walk(driver_dir):
                for file in files:
                    if file.lower().startswith("chromedriver"):
                        extracted_path = os.path.join(root, file)
                        shutil.move(extracted_path, driver_path)
                        found = True
                        break
                if found:
                    break

            if not os.path.exists(driver_path):
                raise FileNotFoundError("ChromeDriver executable not found after extraction.")

            # Set executable permissions on Linux
            if os_name != "Windows":
                os.chmod(driver_path, os.stat(driver_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            print(f"✅ ChromeDriver saved to: {driver_path}")

        except Exception as e:
            print(f"❌ Error downloading or extracting ChromeDriver: {e}")
            sys.exit(1)

    # Launch WebDriver
    try:
        service = ChromeService(executable_path=driver_path)
        driver = webdriver.Chrome(service=service)
        return driver
    except Exception as e:
        print(f"❌ Failed to launch ChromeDriver: {e}")
        sys.exit(1)


def load_csv_file(file_name):
    file_dir = None
    # First, check if the file exists in the current directory
    if os.path.exists(file_name):
        try:
            units_df = pd.read_csv(file_name)
            return units_df, file_dir
        except Exception as e:
            print(f"Failed to read {file_name}: {e}")
            exit(1)

    # If not found, prompt the user for the correct path
    while True:
        file_dir = input(f"File '{file_name}' not found. Enter the full folder path of the file : ")
        custom_path = file_dir + "/" + file_name

        if os.path.exists(custom_path):
            try:
                units_df = pd.read_csv(custom_path)
                return units_df, file_dir
            except Exception as e:
                print(f"Failed to read {custom_path}: {e}")
                exit(1)
        else:
            print(f"File not found at '{custom_path}'.")
            retry = input("Do you want to try entering the path again? (y/N): ").strip().lower()
            if retry != 'y':
                print("Exiting...")
                exit(1)


def check_chrome_installed():
    """Check if Google Chrome is installed on Linux or Windows."""
    system = platform.system()

    try:
        if system == "Linux":
            # Try command line
            result = subprocess.run(['google-chrome', '--version'], check=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            version = result.stdout.decode().strip()
            print(f"Detected Chrome version: {version}")
            return True

        elif system == "Windows":
            # Try registry query (user-level Chrome install)
            result = subprocess.check_output(
                r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version',
                shell=True).decode()
            version = re.search(r"(\d+\.\d+\.\d+\.\d+)", result)
            if version:
                print(f"Detected Chrome version: {version.group(1)}")
                return True
            else:
                print("Chrome registry key found but version could not be parsed.")
                return False
        else:
            print(f"Unsupported OS: {system}")
            return False
    except Exception as e:
        print(f"Could not detect Google Chrome: {e}")
        return False


def check_operating_system():
    """Return the name of the current operating system."""
    os_name = platform.system()
    print(f"Detected Operating System: {os_name}")
    return os_name in ["Linux", "Windows"]


def validate_environment():
    """Ensure Google Chrome is installed and OS is supported."""
    if not check_operating_system():
        print("Unsupported operating system. Exiting...")
        sys.exit(1)

    if not check_chrome_installed():
        print("Google Chrome not found. Please install it first.")
        sys.exit(1)

    print("Environment validation successful.")


def main():
    validate_environment()

    retry = input("IMPORTANT - Have you already created the group names on Moodle (y/n)? ").strip().lower()
    if retry != 'y':
        print(" Please create the groups on Moodle using the import groups feature (Check the template CSV on Git or "
              "Moodle Docs), \n OR \n Create them Manually on Moodle.")
        exit(1)

    while True:
        # Ask for unit info before launching browser
        unit_name, unit_id, unit_dir = prompt_for_unit_info()

        # Launch browser only after inputs are collected
        driver = setup_chrome_driver()
        login_to_moodle(driver)

        print(f"Processing Unit Name: {unit_name}, Unit ID: {unit_id}")
        process_unit(driver, unit_dir, unit_name, unit_id)

        # Close browser session after each unit
        driver.quit()

        again = input("Do you want to process another unit? (y/N): ").strip().lower()
        if again != 'y':
            print("All done. Exiting.")
            break


if __name__ == "__main__":
    main()
