# -*- coding: utf-8 -*-
# Copyright (C) 2024
# Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
# Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger
#

"""This module automates the process of removing backgrounds
from images using the remove.bg site.

Features:
- Automates browser interactions to upload images,
  solve captchas and download processed files.
- Uses Selenium with undetected Chrome WebDriver to
  mimic human-like behavior and bypass restrictions.
- Handles retries for background removal in case
  of failures or errors during the process.
- Manages browser configurations to set custom
  download directories and handle session-specific files.

This module ensures a seamless and efficient approach to removing
image backgrounds, leveraging automation to reduce manual effort.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from time import sleep

import undetected_chromedriver as uc  # type: ignore[import]
from selenium.common.exceptions import (
    ElementNotVisibleException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from genai.utils import start_chrome

logging.basicConfig(level=logging.INFO)


class AbortScriptError(Exception):
    """Custom exception class to handle errors during the background removal process.

    :ivar driver: The Selenium WebDriver instance to be closed upon error.
    :vartype driver: uc.Chrome
    """

    def __init__(self, message: str, driver: uc.Chrome = None) -> None:
        """Initialize the AbortScriptError with a message and an optional driver.

        :param message: The error message.
        :type message: str
        :param driver: The Selenium WebDriver instance to be closed, defaults to None.
        :type driver: uc.Chrome, optional
        """
        super().__init__(message)
        self.driver = driver

    def close_driver(self) -> None:
        """Close the Selenium WebDriver instance if present.

        :return: None
        :rtype: None
        """
        if self.driver:
            self.driver.quit()


def _error_capsolver(driver: uc.Chrome) -> None:
    """Check if an error occurred during captcha solving with CapSolver.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :return: None
    :rtype: None
    """
    try:
        if WebDriverWait(driver, 10).until(
            ec.text_to_be_present_in_element(
                (
                    By.XPATH,
                    "//div[@id='capsolver-solver-tip-button' "
                    "and contains(@data-state, 'error')]",
                ),
                "ERROR_CAPTCHA_SOLVE_FAILED",
            ),
        ):
            logging.info("ERROR_CAPTCHA_SOLVE_FAILED")
    except Exception:
        logging.info("Captcha solve error not found.")


def run_bg_remove(image_path: str) -> Path:
    """Remove the background of an image using remove.bg.

    Automates the process using Selenium and handles captcha solving.

    :param image_path: The path to the image file.
    :type image_path: str
    :return: The path to the processed image file.
    :rtype: Path
    :raises AbortScriptError: If an error occurs during the process.
    """
    input_dir = Path(image_path).parent
    driver = None
    try:
        driver = start_chrome("capsolver", input_dir)

        # Handling modal dialog
        try:
            dialog = WebDriverWait(driver, 5).until(
                ec.presence_of_element_located(
                    (By.XPATH, "//dialog[@aria-modal='true']")
                ),
            )
            dialog.find_element(
                By.XPATH, ".//button[contains(text(), 'Close')]"
            ).click()
            WebDriverWait(driver, 5).until(ec.staleness_of(dialog))
        except Exception:
            logging.info("Dialog not found. Skipping.")

        # Click on 'Bild wählen' button
        try:
            # Wait for the button to be present in the DOM
            button = WebDriverWait(driver, 60).until(
                ec.presence_of_element_located(
                    (
                        By.XPATH,
                        "//button[contains(@class, 'rounded-full') and contains(., 'Bild wählen')]",
                    )
                ),
            )

            # Use JavaScript to click the element
            driver.execute_script("arguments[0].click();", button)
        except TimeoutException:
            logging.info("Button 'Bild wählen' not found. Skipping this step.")

        # Upload image
        try:
            WebDriverWait(driver, 80).until(
                ec.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")),
            ).send_keys(str(Path(image_path).resolve()))
        except Exception as e:
            _error_capsolver(driver)
            raise AbortScriptError("input[type='file'] failed") from e

        # Trying to click the download button (up to two times)
        for attempt in range(2):
            try:
                download_button = WebDriverWait(driver, 100).until(
                    ec.element_to_be_clickable(
                        (By.XPATH, "//button[.//div[text()='Download']]")
                    ),
                )
                sleep(2)
                download_button.click()
                sleep(10)
                break
            except (NoSuchElementException, ElementNotVisibleException) as err:
                logging.warning(
                    "Attempt %s failed to click the download button.", attempt + 1
                )
                if attempt == 1:
                    raise AbortScriptError(
                        "Trying to click the download button failed",
                        driver,
                    ) from err
    except Exception as err:
        logging.exception("An error occurred in run_bg_remove: %s", err)
        raise AbortScriptError("Error in run_bg_remove", driver) from err
    finally:
        if driver:
            driver.quit()

    # After driver is closed, proceed
    list_of_files = list(Path(input_dir).glob("*"))
    return max(list_of_files, key=os.path.getctime)


def bg_remove(image_path: str, retries: int = 2) -> Path | None:
    """Remove the background of an image with retries upon failure.

    :param image_path: The path to the image file.
    :type image_path: str
    :param retries: Number of retries allowed. Defaults to 2.
    :type retries: int, optional
    :return: The path to the processed image file, or None if unsuccessful.
    :rtype: Path | None
    """
    for attempt in range(retries):
        try:
            return run_bg_remove(image_path)
        except AbortScriptError as err:
            logging.exception("Attempt %d/%d failed: %s", attempt + 1, retries, err)
            err.close_driver()
            if attempt == retries - 1:
                logging.exception("Maximum number of attempts reached. Aborting.")
                return None
            logging.info("Retrying...")
    return None
