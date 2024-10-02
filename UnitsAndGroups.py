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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
import re
import getpass
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


# Suppress GetPassWarning
#warnings.filterwarnings('ignore', category=getpass.GetPassWarning)

def graceful_exit(driver, message):
    """Function to gracefully exit with an error message."""
    print(f"Error: {message}")
    driver.quit()
    exit(1)


def login_to_moodle(driver, username_str, password_str):
    """Function to log in to Moodle with user-provided credentials."""
    #username_str = input("Enter your Moodle username: ")
    #password_str = getpass.getpass("Enter your Moodle password: ")

    driver.get('https://moodle.mit.edu.au/login/index.php')
    try:
        username = driver.find_element(By.ID, 'username')
        password = driver.find_element(By.ID, 'password')
        login_button = driver.find_element(By.ID, 'loginbtn')
    except Exception as e:
        graceful_exit(driver, f"Failed to locate login elements: {e}")

    username.send_keys(username_str)
    password.send_keys(password_str)
    login_button.click()
    time.sleep(5)  # Wait for login to complete


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


def add_students_to_group(driver, group_value, student_names):
    """Function to add multiple students to a group."""
    add_student_url = f"https://moodle.mit.edu.au/group/members.php?group={group_value}"
    driver.get(add_student_url)
    time.sleep(1)  # Wait for the page to load

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

        print(f"Adding for Group: {group_name}")

        group_value = group_mapping[group_name]
        add_students_to_group(driver, group_value, student_names)


#This method is not used anymore
def get_chromedriver_path():
    default_path = os.path.join(os.getcwd(), 'chromedriver')

    if os.path.exists(default_path):
        return default_path

    while True:
        chromedriver_dir = input(
            "Default Chromedriver Not found, Enter the Full path to ChromeDriver EXE (including the executable name) : ")
        custom_path = chromedriver_dir  #+ "//chromedriver"
        print(custom_path)
        if os.path.exists(custom_path):
            return custom_path
        else:
            retry = input(
                "Path Not Found ! Do you want to try again? (y/N): ").strip().lower()
            if retry != 'y':
                print("Exiting...")
                exit(1)


def setup_chrome_driver():
    try:
        print("Automatically downloads and installs ChromeDriver!")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        return driver
    except WebDriverException as e:
        print(f"Failed to set up ChromeDriver: {e}")
        exit(1)  # Exit here if chromedriver failed


#This method is not used anymore.
def setup_chrome_driver_old():
    chromedriver_path = get_chromedriver_path()
    try:
        service = ChromeService(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service)
        return driver
    except Exception as e:
        print(f"Error initializing ChromeDriver: {e}")
        exit(1)


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
    """Check if Google Chrome is installed."""
    try:
        # Try running 'google-chrome --version' to see if it's installed
        subprocess.run(['google-chrome', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #print("Google Chrome is installed.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Google Chrome is not installed.")
        return False

def check_operating_system():
    """Check if the operating system is Linux."""
    if platform.system() == "Linux":
        #print("Operating system is Linux.")
        return True
    else:
        print(f"Operating system is not Linux. Detected OS: {platform.system()}. \nPls build it using source.")
        return False

def validate_environment():
    """Ensure both Google Chrome is installed and the OS is Linux."""
    if not check_chrome_installed() or not check_operating_system():
        print("Environment validation failed. Exiting...")
        sys.exit(1)  # Exit the program with a status of 1 (indicating an error)
    #print("Both conditions are met. Proceeding...")


def main():
    validate_environment()
    retry = input("IMPORTANT - Have you already created the group names on Moodle ? ").strip().lower()
    if retry != 'y':
        print(" Please create the groups on Moodle using the import groups feature (Check the template CSV on Git or "
              "Moodle Docs), \n OR \n Create them Manually on Moodle.")
        exit(1)

    # Load the Units.csv file
    """Read the Units.csv file."""
    file_name = "Units.csv"

    units_df, unit_dir = load_csv_file(file_name)

    # Prompt the user for their Moodle credentials before initializing WebDriver
    username_str = input("Enter your Moodle username: ")
    password_str = getpass.getpass("Enter your Moodle password: ")

    # Set up the WebDriver (e.g., Chrome)
    #service = ChromeService(executable_path='//home//mit//chromedriver-linux64//chromedriver')
    # Now use the function to set up the WebDriver
    driver = setup_chrome_driver()

    # Log in to Moodle
    login_to_moodle(driver, username_str, password_str)

    # Process each unit
    for index, unit_row in units_df.iterrows():
        unit_name = unit_row.iloc[0]  # First column is the unit name
        unit_id = unit_row.iloc[1]  # Second column is the unit ID
        print(f"Processing Unit Name: {unit_name}, Unit ID: {unit_id}")

        process_unit(driver, unit_dir, unit_name, unit_id)

    print("Exiting")
    driver.quit()


if __name__ == "__main__":
    main()
