'''
Author: Samar Shailendra
License: GPL v3.0
'''
import os
import time
import pandas as pd
import logging
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import re
import getpass
from webdriver_manager.chrome import ChromeDriverManager


# Suppress GetPassWarning
#warnings.filterwarnings('ignore', category=getpass.GetPassWarning)

def graceful_exit(driver, message):
    """Function to gracefully exit with an error message."""
    print(f"Error: {message}")
    driver.quit()
    exit(1)


def login_to_AMS(driver, username_str, password_str):
    """Function to log in to Moodle with user-provided credentials."""
    #username_str = input("Enter your Moodle username: ")
    #password_str = getpass.getpass("Enter your Moodle password: ")

    driver.get('https://ams.mit.edu.au/')
    try:
        username = driver.find_element(By.ID, 'Username')
        password = driver.find_element(By.ID, 'Password')
        login_button = driver.find_element(By.XPATH, '//input[@type="submit" and @value="Sign In"]')
    except Exception as e:
        graceful_exit(driver, f"Failed to locate login elements: {e}")

    username.send_keys(username_str)
    password.send_keys(password_str)
    login_button.click()
    time.sleep(5)  # Wait for login to complete


def get_chromedriver_path():
    default_path = os.path.join(os.getcwd(), 'chromedriver')
    #default_path = "//home//mit//chromedriver-linux64//chromedriver"

    if os.path.exists(default_path):
        return default_path

    while True:
        chromedriver_dir = input("Default Chromedriver Not found, Enter the full path to the EXE (including the Executable Name): ")
        custom_path = chromedriver_dir  #+ "//chromedriver"
        print(custom_path)
        if os.path.exists(custom_path):
            return custom_path
        else:
            retry = input(
                "Path Not Found! Do you want to try again? (y/N): ").strip().lower()
            if retry != 'y':
                print("Exiting...")
                exit(1)


def setup_chrome_driver():
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
        file_dir = input(f"File '{file_name}' not found. Enter the full folder path of the file: ")
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


def check_attendance_and_process_unit(driver, url):
    # Navigate to the provided URL
    driver.get(url)

    try:
        # Wait for the table or page to load completely
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "timetable"))
        )

        # Find all rows within the table
        rows = driver.find_elements(By.XPATH, '//tr[contains(@class, "odd") or contains(@class, "even")]')

        print(f"Number of rows found: {len(rows)}")

        if not rows:
            print("No rows found. Check the XPath or ensure the page has loaded correctly.")
            return

        # Store the indices of rows with attendance > 50%
        eligible_indices = []

        for index in range(len(rows)):
            try:
                row = rows[index]

                student_id = row.find_element(By.XPATH, './td[3]').text
                attendance_element = row.find_element(By.XPATH, './td[19]')
                attendance_str = attendance_element.text.strip()

                if not attendance_str:
                    logging.info(f"Skipping student {student_id} due to missing attendance data.")
                    continue

                if attendance_str.endswith('%'):
                    attendance_percentage = float(attendance_str.strip('%'))
                else:
                    logging.info(f"Skipping student {student_id} due to invalid attendance data: '{attendance_str}'")
                    continue

                if attendance_percentage < 50:
                    logging.info(
                        f"+++++++++ Skipping student {student_id} with attendance {attendance_percentage}%. +++++++++")
                    continue

                print(f"Student {student_id} with attendance {attendance_percentage}% is eligible.")
                eligible_indices.append(index)

            except Exception as e:
                print(f"An error occurred on student {student_id}: {e}")

        # Call process_unit for eligible rows only
        if eligible_indices:
            process_unit(driver, url, eligible_indices)

    except Exception as e:
        print(f"An error occurred: {e}")


def process_unit(driver, url, eligible_indices):
    # Navigate to the provided URL
    driver.get(url)

    try:
        # Wait for the table or page to load completely
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "timetable"))
        )

        # Find all "View" links within the table cells
        view_links = driver.find_elements(By.XPATH,
                                          '//td/a[contains(@class, "btn-outline-primary") and contains(@class, "btn-sm")]')

        # Debugging: Print the number of links found
        print(f"Number of 'View' links found: {len(view_links)}")

        if not view_links:
            print("No 'View' links found. Check the XPath or ensure the page has loaded correctly.")
            return

        # Loop through each link and click on it
        for index in range(len(view_links)):
            #Check if this is a valid index to be clicked or not
            if index not in eligible_indices:
                print("This is not an eligible index to be processed.")
                continue

            try:
                # Click the link
                print(f"Going to click the link: {index + 1}")

                # Re-locate the link before each click to avoid stale element references
                view_links = driver.find_elements(By.XPATH,
                                                  '//td/a[contains(@class, "btn-outline-primary") and contains(@class, "btn-sm")]')

                print(f"The link is: {view_links[index]}")

                # Scroll the link into view before clicking
                driver.execute_script("arguments[0].scrollIntoView(true);", view_links[index])
                time.sleep(1)  # Wait for the scrolling to complete

                try:
                    # Attempt to click the link
                    view_links[index].click()
                except Exception as e:
                    print(f"Error using Selenium click, trying JavaScript click for link {index + 1}. Error: {e}")
                    driver.execute_script("arguments[0].click();", view_links[index])

                # Wait for the new page to load (you may need to adjust this)
                time.sleep(3)

                update_assessment(driver)

                print(f"returned from update_assessment for link: {index + 1}")

                # Navigate back to the original page
                #driver.back()

                # Wait for the page to load again
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "timetable"))
                )

                time.sleep(2)  # Additional wait to ensure all elements are loaded before the next iteration

            except Exception as e:
                logging.info(f"An error occurred on link {index + 1}")
                print(e)  #print the stack trace only on console.

    except Exception as e:
        print(f"An error occurred: {e}")


def update_assessment(driver):
    try:
        # Wait for the radio buttons to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "AttemptedFormativeAssessment"))
        )

        # Select the radio button for AccessUnitShell
        accessed_radio = driver.find_element(By.ID, "AccessUnitShell")
        if not accessed_radio.is_selected():
            accessed_radio.click()
        else:
            print("AccessUnitShell is already selected.")

        # Select the radio button for AttemptedFormativeAssessment
        attempted_radio = driver.find_element(By.ID, "AttemptedFormativeAssessment")
        if not attempted_radio.is_selected():
            attempted_radio.click()
        else:
            print("AttemptedFormativeAssessment is already selected.")

        # Select the radio button for PassedFormativeAssessment
        passed_radio = driver.find_element(By.ID, "PassedFormativeAssessment")
        if not passed_radio.is_selected():
            passed_radio.click()
        else:
            print("PassedFormativeAssessment is already selected.")

        # Wait for the first submit button to be present
        first_submit_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//button[@data-bs-target="#confirmation"]'))
        )

        # Scroll into view and click the first submit button
        driver.execute_script("arguments[0].scrollIntoView(true);", first_submit_button)

        try:
            first_submit_button.click()
        except Exception as e:
            print("Error using Selenium click, trying JavaScript click.")
            driver.execute_script("arguments[0].click();", first_submit_button)

        # Wait for the modal to appear and the second submit button to be clickable
        confirmation_modal = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "confirmation"))
        )
        print("Confirmation modal appeared.")

        # Click the confirmation submit button in the modal
        confirmation_submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@type="Submit" and @value="Update"]'))
        )
        confirmation_submit_button.click()
        print("Confirmation submit button clicked.")

        # Optionally, wait a moment for any actions that follow the submission
        time.sleep(2)

    except Exception as e:
        print(f"An error occurred while updating the assessment: {e}")


# Function to set up logging
def setup_logging(log_filename):
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='w'
    )
    # Set up logging to the console as well
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)


def main():
    # Load the Units.csv file
    """Read the AMS_Units.csv file."""
    file_name = "AMS_Units.csv"
    log_filename = 'app.log'  # Replace with the desired log filename

    ams_units, file_dir = load_csv_file(file_name)
    setup_logging(log_filename)
    # Example usage
    print("Setup Logging in file. While Errors and StackTraces are printed only on terminal!")

    # Prompt the user for their Moodle credentials before initializing WebDriver
    username_str = input("Enter your AMS username: ")
    password_str = getpass.getpass("Enter your AMS password: ")

    # Set up the WebDriver (e.g., Chrome)
    #service = ChromeService(executable_path='//home//mit//chromedriver-linux64//chromedriver')
    # Now use the function to set up the WebDriver
    driver = setup_chrome_driver()

    # Log in to Moodle
    login_to_AMS(driver, username_str, password_str)

    base_url = "https://ams.mit.edu.au/AcademicStaff/Students/"

    # Process each unit
    for index, unit_row in ams_units.iterrows():
        unit_name = unit_row.iloc[0]  # First column is the unit name
        unit_id = unit_row.iloc[1]  # Second column is the unit ID
        logging.info(f"++++++++++++ Processing Unit Name: {unit_name}, Unit ID: {unit_id} ++++++++++++")
        url = base_url + str(unit_id)
        check_attendance_and_process_unit(driver, url)

    logging.info("Exiting")
    driver.quit()


if __name__ == "__main__":
    main()
