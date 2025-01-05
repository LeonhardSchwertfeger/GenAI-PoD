# -*- coding: utf-8 -*-
# Copyright (C) 2024
# Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
# Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger
#

"""This module automates the process of uploading designs to Spreadshirt using Selenium WebDriver.

Features:
- Starts a Chrome browser session with a predefined user profile.
- Automates the uploading process of images to Spreadshirt's design platform.
- Validates and corrects input fields (title, description, tags)
  for forbidden words or invalid content.
- Selects and configures the appropriate marketplaces, templates and
  settings for the uploaded design.
- Finalizes the upload process, ensuring the design is published successfully.
- Handles various exceptions such as timeout issues, missing elements and incorrect
  inputs, with detailed logging.
"""

from __future__ import annotations

import logging
import re
from time import sleep

import undetected_chromedriver as uc  # type: ignore[import]
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from genai.utils import UploadConfig, iterate_and_upload, start_chrome


def upload_spreadshirt(upload_path: str) -> None:
    """Initialize the driver and start uploading designs to Spreadshirt.

    :param upload_path: The path to upload designs from.
    :type upload_path: str
    """
    driver = start_chrome("Spreadshirt", None)
    driver.get("https://partner.spreadshirt.de/designs")

    config = UploadConfig(
        upload_path=upload_path,
        upload_function=_upload_with_selenium,
        used_folder_name="used_spreadshirt",
        error_folder_name="error_spreadshirt",
        exclude_folders=["used_redbubble", "error_spreadshirt", "used_spreadshirt"],
    )

    iterate_and_upload(
        driver=driver,
        config=config,
    )
    driver.quit()


def _wait_and_click(
    driver: uc.Chrome,
    selector: str,
    by: str = By.CSS_SELECTOR,
    timeout: int = 30,
) -> None:
    """Wait for an element to be clickable and then click it.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    :param selector: The selector for the element to click.
    :type selector: str
    :param by: The method to locate elements, defaults to By.CSS_SELECTOR.
    :type by: By, optional
    :param timeout: The maximum time to wait in seconds, defaults to 30.
    :type timeout: int, optional
    """
    try:
        WebDriverWait(driver, timeout).until(
            ec.element_to_be_clickable((by, selector)),
        ).click()
    except Exception:
        logging.info("Failed to click on element with selector: %s", selector)


def _check_not_available_names(
    driver: uc.Chrome,
    text: str,
    field_type: str,
) -> tuple[bool, str]:
    """Checks for forbidden words in the given field and removes them if found.
    Updates the field in the browser accordingly.

    :param driver: The WebDriver instance controlling the browser.
    :type driver: uc.Chrome
    :param text: The current text of the field (title, description, or tags).
    :type text: str
    :param field_type: The type of the field ('title', 'description', 'tags').
    :type field_type: str
    :return: A tuple containing a boolean indicating if a correction
      was made and the corrected text.
    :rtype: tuple[bool, str]
    """
    try:
        # Define selectors based on field_type
        if field_type == "title":
            error_info_selector = "small.error-info.error-info-name"
            input_field_id = "input-design-name"
        elif field_type == "description":
            error_info_selector = "small.error-info.error-info-description"
            input_field_id = "input-design-description"
        elif field_type == "tags":
            error_info_selector = "small.error-info.error-info-tags"
            input_field_id = None  # Tags are handled differently
        else:
            raise ValueError(f"Invalid field_type: {field_type}")

        error_text = driver.find_element(By.CSS_SELECTOR, error_info_selector).text
        prefix = "Folgende Begriffe sind nicht erlaubt: "

        if not error_text.startswith(prefix):
            return False, text  # No forbidden words found

        # Extract forbidden words
        forbidden_words = [
            word.strip() for word in error_text[len(prefix) :].split(",")
        ]

        if field_type in ["title", "description"]:
            # Remove forbidden words from text
            for word in forbidden_words:
                text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
            text = re.sub(r"\s+", " ", text).strip()  # Clean whitespace

            # Update the input field
            input_field = driver.find_element(By.ID, input_field_id)
            driver.execute_script("arguments[0].value = '';", input_field)
            driver.execute_script(
                "arguments[0].value = arguments[1];", input_field, text
            )

            # Trigger necessary events
            for event in ["input", "change", "blur", "keyup"]:
                driver.execute_script(
                    f"arguments[0].dispatchEvent(new Event('{event}'));", input_field
                )

            # Wait for error message to disappear
            WebDriverWait(driver, 15).until(
                ec.invisibility_of_element_located(
                    (By.CSS_SELECTOR, error_info_selector)
                ),
            )

            return True, text  # Correction made

        if field_type == "tags":
            not_allowed_tags = [tag.strip().lower() for tag in forbidden_words]
            # Split the tags_string into individual tags, remove forbidden words
            filtered_tags = [
                tag
                for tag in map(str.strip, text.split(","))
                if tag.lower() not in not_allowed_tags
            ]
            final_tags_string = ",".join(filtered_tags).strip(",")
            # Update tags
            _setup_tags(driver, final_tags_string)

            # Wait for error message to disappear
            WebDriverWait(driver, 15).until(
                ec.invisibility_of_element_located(
                    (By.CSS_SELECTOR, error_info_selector)
                ),
            )

            return True, final_tags_string  # Correction made

    except NoSuchElementException:
        logging.info("%s", str(field_type.capitalize()) + "is already valid.")
        return False, text  # No error element found

    except TimeoutException:
        logging.info(
            "Error message did not disappear after correction for %s", str(field_type)
        )
        return False, text  # Correction failed

    return False, text


def _setup_tags(driver: uc.Chrome, tags: str | list[str]) -> None:
    """Delete all existing tags and input new tags.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    :param tags: A comma-separated string or list of tags to input.
    :type tags: Union[str, list[str]]
    """
    input_element = driver.find_element(
        By.CSS_SELECTOR, "div.dropdown-button input.dropdown-input"
    )

    # Clear existing tags
    input_element.send_keys(Keys.BACK_SPACE * 30)

    # Convert tags to a comma-separated string if it's a list
    if isinstance(tags, list):
        tags = ",".join(tags)

    # Input new tags
    for tag in map(str.strip, tags.split(",")):
        if tag:
            input_element.send_keys(tag)
            input_element.send_keys(Keys.ENTER)

    logging.info("***TAG SETUP DONE***")


def wait_until_value_exceeds_50(driver: uc.Chrome) -> None:
    """Waits for the value inside a <strong> tag within an element with the class 'sellable-count'
    to exceed 50. It checks the value every 5 seconds for up to 1 minute.

    :param driver: The WebDriver instance controlling the browser.
    :type driver: uc.Chrome
    :raises Exception: If the value does not exceed 50 within 1 minute.
    """
    try:
        WebDriverWait(driver, 60, poll_frequency=5).until(
            lambda d: int(
                d.find_element(By.CLASS_NAME, "sellable-count")
                .find_element(By.TAG_NAME, "strong")
                .text,
            )
            > 50,
        )
    except TimeoutException as err:
        raise Exception(
            "The template does not include at least 50 products. "
            "Please check the README if you haven't done so yet.",
        ) from err


def _select_marketplace(driver: uc.Chrome) -> None:
    """Select the marketplaces (Spreadshirt and Spreadshop) for the design.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    """
    # Wait until the marketplace selection elements are present
    select_marketplaces = WebDriverWait(driver, 15).until(
        ec.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "div.pos-selection div.pos-selection-header"),
        ),
    )

    # Click on Spreadshirt
    try:
        select_marketplaces[0].click()
        logging.info("Spreadshirt has been successfully selected.")
    except (ElementClickInterceptedException, ElementNotInteractableException) as e:
        logging.info(
            "Failed to select Spreadshirt. "
            "Please ensure the Spreadshirt option is available.",
        )
        raise e

    # Attempt to click on Spreadshop
    if len(select_marketplaces) > 1:
        try:
            select_marketplaces[1].click()
            logging.info("Spreadshop has been successfully selected.")
        except (ElementClickInterceptedException, ElementNotInteractableException):
            logging.info(
                "Spreadshop could not be selected. "
                "This is optional. Please set up a Spreadshop if you wish to use this feature.",
            )
    else:
        logging.info(
            "Spreadshop option is not available. "
            "This is optional. Please set up a Spreadshop if you wish to use this feature.",
        )


def _upload_image(driver: uc.Chrome, image_path: str) -> bool:
    """Uploads the image to Spreadshirt.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    :param image_path: The file path of the image to upload.
    :type image_path: str
    :return: True if the image was uploaded successfully, False otherwise.
    :rtype: bool
    """
    import sys

    _wait_and_click(driver, ".card-container.col-xs-1.upload-tile", timeout=60)
    driver.find_element(By.ID, "hiddenFileInput").send_keys(image_path)
    wait = WebDriverWait(driver, timeout=60)

    try:
        wait.until(
            ec.visibility_of_element_located(
                (By.CSS_SELECTOR, ".preview-image-loader")
            ),
        )
    except TimeoutException:
        try:
            error_element = driver.find_element(
                By.CSS_SELECTOR,
                ".design-upload-progress-bar.upload-error",
            )
            if error_element.is_displayed():
                limit_message_element = driver.find_element(
                    By.CSS_SELECTOR,
                    ".design-upload-message.text-sm",
                )
                if (
                    "Du hast das tägliche Limit für Uploads erreicht."
                    in limit_message_element.text
                ):
                    logging.exception("Upload limit reached.")
                    sys.exit(1)
                logging.exception("Upload failed, error element found.")
                return False
        except NoSuchElementException:
            logging.info("No upload error detected, proceeding.")

    wait.until(
        ec.invisibility_of_element_located((By.CSS_SELECTOR, ".preview-image-loader")),
    )

    return True


def _process_overlay(driver: uc.Chrome) -> None:
    """Processes the overlay after the image upload.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    """
    WebDriverWait(driver, timeout=60).until(
        ec.presence_of_element_located(
            (By.CSS_SELECTOR, ".image-overlay .overlay-content"),
        ),
    )
    overlay_content = driver.find_element(
        By.CSS_SELECTOR,
        ".image-overlay .overlay-content",
    )
    driver.execute_script("arguments[0].style.display = 'block';", overlay_content)
    driver.execute_script("arguments[0].scrollIntoView(true);", overlay_content)
    driver.execute_script(
        "arguments[0].click();",
        driver.find_element(
            By.CSS_SELECTOR,
            ".overlay-content .edit-icon",
        ),
    )


def _select_marketplace_and_save(driver: uc.Chrome) -> None:
    """Selects the marketplace and saves the selection.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    """
    try:
        _select_marketplace(driver)
        _wait_and_click(
            driver,
            "button#account-settings-save-button.btn-progress."
            "IDLE.null.btn.btn-primary.icon-btn.icon-right",
            By.CSS_SELECTOR,
            timeout=5,
        )
    except TimeoutException:
        _wait_and_click(
            driver,
            "button.btn-progress.IDLE.btn.btn-primary",
            By.CSS_SELECTOR,
            timeout=10,
        )
        _wait_and_click(
            driver,
            'div[class="preview-image"] > div[class="idea-preview-image"]',
            By.CSS_SELECTOR,
            timeout=15,
        )
        _select_marketplace(driver)
        _wait_and_click(
            driver,
            "button#account-settings-save-button.btn-progress."
            "IDLE.null.btn.btn-primary.icon-btn.icon-right",
            By.CSS_SELECTOR,
            timeout=60,
        )
    except NoSuchElementException:
        logging.info(
            "No Element found while determining if original or marketplace selection is required.",
        )
    except Exception:
        logging.info(
            "Problem while determining if original or marketplace selection is required.",
        )


def _select_template(driver: uc.Chrome) -> None:
    """Selects the design template.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    """
    WebDriverWait(driver, 60).until(
        ec.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "button.btn.btn-light.icon-btn"),
        ),
    )[1].click()

    WebDriverWait(driver, 60).until(
        ec.presence_of_all_elements_located(
            (
                By.CSS_SELECTOR,
                "button.btn-progress.IDLE.null.btn.btn-primary.btn-light.icon-btn",
            ),
        ),
    )[-1].click()
    wait_until_value_exceeds_50(driver)


def _finalize_upload(driver: uc.Chrome) -> None:
    """Finalizes the upload process.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    """
    WebDriverWait(driver, 30).until(
        lambda driver: all(
            [
                ec.visibility_of_element_located(
                    (By.ID, "account-settings-save-button"),
                )(driver),
                ec.element_to_be_clickable((By.ID, "account-settings-save-button"))(
                    driver,
                ),
                not driver.find_element(
                    By.CSS_SELECTOR,
                    "#account-settings-save-button .overlay",
                ).is_displayed(),
            ],
        )
        and driver.find_element(By.ID, "account-settings-save-button"),
    ).click()  # type: ignore[attr-defined]
    _wait_and_click(driver, "toggle", By.CLASS_NAME, timeout=30)


def _input_details(
    driver: uc.Chrome,
    title: str,
    description: str,
    tag: str,
) -> tuple[list, str]:
    """Inputs the title, description, and tags.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    :param title: The title of the design.
    :type title: str
    :param description: The description of the design.
    :type description: str
    :param tag: A comma-separated string of tags.
    :type tag: str
    :return: A tuple containing the more languages button and the tags string.
    :rtype: tuple[list, str]
    """
    description_text = driver.find_element(By.ID, "input-design-description")
    description_text.clear()
    input_element = driver.find_element(
        By.CSS_SELECTOR,
        "div.dropdown-button input.dropdown-input",
    )
    for _ in range(25):
        input_element.send_keys(Keys.BACK_SPACE)
    title_text = driver.find_element(By.ID, "input-design-name")
    title_text.clear()
    more_languages_button = WebDriverWait(driver, 60).until(
        ec.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "button.btn.text-btn.link-blue"),
        ),
    )
    more_languages_button[-1].click()
    _wait_and_click(driver, "//a[contains(text(), 'English')]", By.XPATH, timeout=30)
    title_text.send_keys(title)
    description_text.send_keys(description)
    tags_list = tag.strip().split(",")
    if len(tags_list) > 25:
        tags_list = tags_list[:25]
    tags_string = ",".join(tags_list)
    _setup_tags(driver, tags_string)
    return more_languages_button, tags_string


def _correct_fields(
    driver: uc.Chrome,
    title: str,
    description: str,
    tags_string: str,
) -> tuple[str, str, str]:
    """Corrects the fields if there are forbidden words.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    :param title: The title of the design.
    :type title: str
    :param description: The description of the design.
    :type description: str
    :param tags_string: The tags string.
    :type tags_string: str
    :return: The corrected title, description, and tags string.
    :rtype: tuple[str, str, str]
    """
    while True:
        title_corrected, title = _check_not_available_names(driver, title, "title")
        description_corrected, description = _check_not_available_names(
            driver, description, "description"
        )
        tags_corrected, tags_string = _check_not_available_names(
            driver, tags_string, "tags"
        )
        if not (title_corrected or description_corrected or tags_corrected):
            break
    return title, description, tags_string


def _select_language_and_publish(
    driver: uc.Chrome,
    more_languages_button: list,
) -> None:
    """Selects the language and publishes the design.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    :param more_languages_button: The more languages button element.
    :type more_languages_button: list
    """
    more_languages_button[0].click()
    WebDriverWait(driver, 60).until(
        ec.presence_of_all_elements_located((By.CLASS_NAME, "radiobutton-container")),
    )[1].click()
    _wait_and_click(
        driver,
        "//button[contains(text(), 'Übernehmen')]",
        By.XPATH,
        timeout=35,
    )
    _wait_and_click(driver, "account-settings-save-button", By.ID, timeout=35)
    sleep(5)
    _wait_and_click(driver, ".link-main.icon-link", By.CSS_SELECTOR, timeout=35)


def _upload_with_selenium(
    driver: uc.Chrome,
    description: str,
    tag: str,
    title: str,
    image_path: str,
) -> bool:
    """Control the upload process to Spreadshirt using Selenium.

    :param driver: The WebDriver instance.
    :type driver: uc.Chrome
    :param description: The description of the design.
    :type description: str
    :param tag: A comma-separated string of tags.
    :type tag: str
    :param title: The title of the design.
    :type title: str
    :param image_path: The file path of the image to upload.
    :type image_path: str
    :return: True if upload was successful, False otherwise.
    :rtype: bool
    """
    try:
        # Removing emojis and special characters
        title = re.sub(r"[^\w\s]", "", title)
        description = re.sub(r"[^\w\s]", "", description)

        # Truncate the title to 50 characters
        if len(title) > 50:
            title = title[:50].strip()

        # Truncate the description to 200 characters
        if len(description) > 200:
            description = description[:200].strip()

        # Upload image
        if not _upload_image(driver, image_path):
            return False

        _process_overlay(driver)
        _select_marketplace_and_save(driver)
        _select_template(driver)
        _finalize_upload(driver)

        # Input details
        more_languages_button, tags_string = _input_details(
            driver,
            title,
            description,
            tag,
        )

        # Correct fields
        title, description, tags_string = _correct_fields(
            driver,
            title,
            description,
            tags_string,
        )

        _select_language_and_publish(driver, more_languages_button)
        return True
    except Exception:
        return False
