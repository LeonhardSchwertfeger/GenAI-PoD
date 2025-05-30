#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2024
# Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
# Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger
#

"""This module provides functionality for generating images using Selenium WebDriver
and ChatGPT. It integrates various utilities for automating browser interactions,
image processing and data scraping. The primary purpose is to facilitate the
creation, customization, and enhancement of images for print-on-demand platforms.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from re import sub
from secrets import choice, randbelow
from tempfile import NamedTemporaryFile
from time import sleep

import undetected_chromedriver as uc
from PIL import Image
from pytz import timezone
from requests import get
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

from genai_pod.utilitys.bigjpg_upscaler import upscale
from genai_pod.utils import clean_string, pilling_image, start_chrome, write_metadata

active_drivers: list[WebDriver] = []

logger = logging.getLogger(__name__)


# The login logic is based on code from the project
# "ChatGPT-unofficial-api-selenium" by Priyanshu-hawk
# Source:
# https://github.com/Priyanshu-hawk/ChatGPT-unofficial-api-selenium/
# tree/5a258b9db844ae13da633591568790460d82524b
# MIT License (c) 2022 Nat Friedman
def _start_chat_gpt() -> uc.Chrome:
    """Start a ChatGPT session by logging in.

    :return: The uc.Chrome instance.
    :rtype: uc.Chrome
    """
    driver = start_chrome("ChatGPT", None)
    active_drivers.append(driver)

    driver.get(
        "https://chatgpt.com/?model=gpt-4o",
    )
    logger.debug("Waiting for login page to load.")

    if _is_element_present(
        driver,
        "//*[contains(text(), 'Log in with your OpenAI account to continue')]",
    ):
        logger.warning("Login page detected. Please log in manually.")
        _wait_for_element(driver, "//div[@id='chatgpt-interface']", 300)

    logger.info("Logged in! (:")
    return driver


def _is_element_present(driver: uc.Chrome, xpath: str) -> bool:
    """Check if an element is present on the page.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :param xpath: The XPath of the element to check.
    :type xpath: str
    :return: True if the element is present, False otherwise.
    :rtype: bool
    """
    try:
        driver.find_element(By.XPATH, xpath)
        return True
    except NoSuchElementException:
        logger.warning("Element '%s' is not present.", xpath)
        return False


def _wait_for_element(driver: uc.Chrome, xpath: str, timeout: int = 4) -> None:
    """Wait for an element to be present on the page.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :param xpath: The XPath of the element to wait for.
    :type xpath: str
    :param timeout: The timeout duration in seconds. Defaults to 4.
    :type timeout: int, optional
    """
    try:
        WebDriverWait(driver, timeout).until(
            ec.presence_of_element_located((By.XPATH, xpath)),
        )
    except TimeoutException:
        logger.error("Element '%s' is not present within the timeout period.", xpath)


def _get_image_src(driver: uc.Chrome) -> str:
    """Get the source URL of the image element with specific characteristics on the page.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :return: The image source URL.
    :rtype: str
    :raises AbortScriptError: If no valid image source is found.
    """
    from selenium.webdriver.remote.webelement import WebElement

    WebDriverWait(driver, 60).until(
        ec.presence_of_element_located(
            (By.XPATH, "//button[contains(., 'Bilderstellung wird gestartet')]")
        )
    )

    WebDriverWait(driver, 250).until(
        ec.invisibility_of_element_located(
            (By.XPATH, "//button[contains(., 'Bilderstellung wird gestartet')]")
        )
    )
    sleep(120)

    image_div: WebElement = WebDriverWait(driver, 150).until(
        lambda d: d.find_element(By.CSS_SELECTOR, "div.absolute.left-0.right-0.top-0")
    )
    image_element = image_div.find_element(By.TAG_NAME, "img")
    image_src = image_element.get_attribute("src")
    if isinstance(image_src, str) and image_src.startswith("http"):
        return image_src

    raise AbortScriptError("No valid image source found.")


def _get_text_from_element(
    driver: uc.Chrome,
    class_index: int,
    retries: int = 10,
) -> str:
    """Attempts to retrieve the generated text from ChatGPT's
    response within a specified DOM structure.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :param class_index: The 0-based index of the target element in the DOM.
    :type class_index: int
    :param retries: The maximum number of retry attempts. Defaults to 10.
    :type retries: int, optional
    :return: The generated text from ChatGPT.
    :rtype: str
    :raises AbortScriptError: If the text cannot be retrieved after
                               all retries or a bad gateway error occurs.
    """
    class_xpath = (
        f"(//div[contains(@class, 'group/conversation-turn')])[{class_index + 1}]"
    )

    for attempt in range(retries):
        try:
            _wait_for_element(driver, class_xpath, 60)

            script = f"""
                var container = document.evaluate(
                    "{class_xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                ).singleNodeValue;
                if (container) {{
                    var markdown_div = container.querySelector('.markdown');
                    if (markdown_div) {{
                        var p_elements = markdown_div.querySelectorAll('p');
                        var full_text = '';
                        p_elements.forEach(function(p) {{
                            full_text += p.innerText + '\\n';
                        }});
                        return full_text.trim();
                    }} else {{
                        console.log("Markdown div not found within the container.");
                    }}
                }} else {{
                    console.log("Container not found for the given XPath.");
                }}
                return '';  // Fallback if no <p> elements are found
            """
            last_p_text = driver.execute_script(script)

            # If text is successfully retrieved, return it
            if isinstance(last_p_text, str) and last_p_text.strip():
                return last_p_text.strip()

        except (NoSuchElementException, TimeoutException) as e:
            logger.warning(
                "Attempt %d/%d: Failed to find elements, retrying... Exception: %s",
                attempt + 1,
                retries,
                str(e),
            )
            if _bad_gateway(driver):
                logger.error("Bad Gateway encountered. Aborting script.")
                raise AbortScriptError(
                    "Bad Gateway encountered during the process.",
                ) from e

        if attempt < retries - 1:
            logger.info("Retrying in 5 seconds...")
            sleep(5)
        else:
            logger.error("Failed after %d attempts.", retries)
            raise AbortScriptError("Failed to find the desired text after all retries.")

    logger.error("Nothing is found after retries.")
    raise AbortScriptError("Nothing is found after retries.")


def _gpt_send_prompt(driver: uc.Chrome) -> None:
    """Send the GPT prompt by clicking the send button.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :raises AbortScriptError: If the send button is not found.
    """
    try:
        WebDriverWait(driver, 600).until(
            ec.element_to_be_clickable(
                (By.CSS_SELECTOR, "[data-testid='send-button']"),
            ),
        ).click()
    except (TimeoutException, NoSuchElementException) as err:
        raise AbortScriptError("Sending Button not found!") from err
    _handle_errors(driver)


def _bad_gateway(driver: uc.Chrome) -> bool:
    """Check if a 'Bad Gateway' error is present.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :return: True if a bad gateway error is present, False otherwise.
    :rtype: bool
    """
    try:
        if WebDriverWait(driver, 50).until(
            ec.presence_of_element_located(
                (By.CSS_SELECTOR, ".cf-error-details.cf-error-502"),
            ),
        ):
            logger.warning("The web server reported a bad gateway error.")
            return True
    except Exception:
        logger.error("Error is not because of the gateway")
    return False


def _gpt_type_text(driver: uc.Chrome, text: str) -> None:
    """Type text into the GPT input field.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :param text: The text to type.
    :type text: str
    :raises AbortScriptError: If the text area is not found or a bad gateway error occurs.
    """
    try:
        textarea = WebDriverWait(driver, 60).until(
            ec.element_to_be_clickable((By.ID, "prompt-textarea")),
        )
    except TimeoutException as err:
        if _bad_gateway(driver):
            raise AbortScriptError("Bad Gateway") from err
        raise AbortScriptError("Timeout while waiting for textarea.") from err
    except NoSuchElementException as err:
        if _bad_gateway(driver):
            raise AbortScriptError("Bad Gateway") from err
        raise AbortScriptError("Textarea element not found.") from err

    textarea.click()
    textarea.send_keys(text)


def _process_image(
    image_url: str,
    image_dir: str,
    title: str,
    tor_binary_path: str | None,
) -> Path:
    """Process and save an image from a given URL, remove its background, and then upscale it.

    :param image_url: The URL of the image to process.
    :type image_url: str
    :param image_dir: The directory to save the processed images.
    :type image_dir: str
    :param title: The title of the image.
    :type title: str
    :return: The output directory where images are saved.
    :rtype: pathlib.Path
    :raises AbortScriptError: If background removal fails.
    """
    import os

    logger.info("Saving image from GPT...")

    image_response = get(image_url, timeout=60)
    image_response.raise_for_status()
    with Image.open(BytesIO(image_response.content)) as image:
        upscaled_image_path = None
        try:
            sanitized_title = sub(r"\W", "_", title)[:10]
            title_hash = sha256(title.encode()).hexdigest()[:8]
            output_directory = Path(image_dir) / f"{sanitized_title}_{title_hash}"

            output_directory.mkdir(parents=True, exist_ok=True)

            raw_image_path = output_directory / f"{title}-bg.png"
            image.save(raw_image_path)

            # No more background removal from external here, because ChatGPT does it

            logger.info("Upscaling for 2k image...")
            upscaled_image_path = upscale(
                str(raw_image_path),
                Path(output_directory),
                tor_binary_path,
            )

            if upscaled_image_path:
                logger.info("Pilling image...")
                pilling_image(str(upscaled_image_path))
        except:  # pylint: disable=try-except-raise # noqa: disable=bare-except
            raise
        finally:
            for file_ in (upscaled_image_path, raw_image_path):
                os.remove(str(file_))

    return output_directory


def _check_error(driver: uc.Chrome, selector: str, error_message: str) -> bool:
    """Check if a specific error exists.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :param selector: The CSS selector of the element to check.
    :type selector: str
    :param error_message: The error message to look for.
    :type error_message: str
    :return: True if the error exists, False otherwise.
    :rtype: bool
    """
    try:
        element = driver.find_element(By.CSS_SELECTOR, selector)
        if error_message in element.text:
            return True
    except NoSuchElementException:
        pass
    return False


def _handle_errors(driver: uc.Chrome) -> None:
    """Handle network and usage limit errors.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :raises AbortScriptError: If a network error is detected.
    """
    if _check_error(
        driver,
        "div.text-sm.text-token-text-error span",
        "Nutzungsobergrenze",
    ):
        _handle_usage_limit(driver)
    elif _check_error(driver, "div.text-sm.text-token-text-error span", ""):
        _handle_network_error(driver)


def _handle_usage_limit(driver: uc.Chrome) -> None:
    """Handle GPT usage limit errors.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :raises AbortScriptError: After waiting for the usage limit to reset.
    """
    error_text = driver.find_element(
        By.CSS_SELECTOR,
        "div.text-sm.text-token-text-error span",
    ).text
    if "Versuche es erneut after" in error_text:
        try:
            target_time = _calculate_target_time(
                error_text.split("after")[1].split()[0],
                error_text,
            )
            _wait_until_time(target_time)
        except ValueError as e:
            logger.exception("Error parsing time: %s", e)
            _handle_network_error(driver)
    else:
        logger.warning("Unexpected usage limit error text.")
        _handle_network_error(driver)


def _handle_network_error(driver: uc.Chrome) -> None:
    """Handle network-related errors.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :raises AbortScriptError: If a network error is detected.
    """
    if _check_error(driver, "div.text-sm.text-token-text-error", ""):
        raise AbortScriptError("Network error detected.")
    logger.debug("No network error found.")


def _calculate_target_time(time_part: str, error_text: str) -> datetime:
    """Calculate the target time for waiting based on the error message.

    :param time_part: The time part extracted from the error message.
    :type time_part: str
    :param error_text: The full error message text.
    :type error_text: str
    :return: The target time to wait until.
    :rtype: datetime
    :raises ValueError: If time parsing fails.
    """
    hour, minute = map(int, time_part.split(":"))

    if "PM" in error_text and hour < 12:
        hour += 12
    elif "AM" in error_text and hour == 12:
        hour = 0

    euro_time = datetime.now(timezone("Europe/Berlin"))
    target_time = euro_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target_time <= euro_time:
        target_time += timedelta(days=1)

    return target_time


def _wait_until_time(target_time: datetime) -> None:
    """Wait until the specified target time.

    :param target_time: The target time to wait until.
    :type target_time: datetime
    :raises AbortScriptError: After the waiting time elapses.
    """
    logger.info(
        "Current Time (Euro Zone): %s",
        datetime.now(timezone("Europe/Berlin")).strftime("%H:%M:%S"),
    )
    logger.info("Waiting until: %s", target_time.strftime("%H:%M:%S"))

    total_wait_seconds = (
        target_time - datetime.now(timezone("Europe/Berlin"))
    ).total_seconds()
    if total_wait_seconds > 0:
        with tqdm(total=int(total_wait_seconds), desc="Waiting Time", unit="s") as pbar:
            for _ in range(int(total_wait_seconds)):
                sleep(1)
                pbar.update(1)

    raise AbortScriptError("Usage limit reached and waiting time elapsed.")


class AbortScriptError(Exception):
    """Custom exception class for aborting the script.

    :ivar driver: The Selenium WebDriver instance to be closed upon error.
    :vartype driver: WebDriver | None

    Methods:
        close_all_drivers(): Closes all active Selenium WebDriver instances.

    """

    def __init__(self, message: str):
        """Initialize the AbortScriptError with a message.

        :param message: The error message.
        :type message: str
        """
        super().__init__(message)

    def close_all_drivers(self) -> None:
        """Closes all active drivers."""
        global active_drivers  # pylint: disable=W0603
        for driver in active_drivers:
            driver.quit()
        active_drivers = []


def _scrape_vexels_image(driver: uc.Chrome) -> str | None:
    """Scrape an image from vexels.com on a random page and save it temporarily.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :return: The path to the temporary image file or None if failed.
    :rtype: str | None
    :raises AbortScriptError: If scraping fails.
    """
    try:
        driver.set_page_load_timeout(60)
        driver.get(f"https://de.vexels.com/nischen/lustig/{randbelow(30) + 1}/")
        active_drivers.append(driver)

        WebDriverWait(driver, 60).until(
            ec.presence_of_all_elements_located((By.CLASS_NAME, "vx-grid-asset")),
        )

        for attempt in range(10):
            asset = choice(driver.find_elements(By.CLASS_NAME, "vx-grid-asset"))

            try:
                container = asset.find_element(
                    By.CSS_SELECTOR,
                    ".vx-grid-asset-container.d-block.h-100",
                )

                img_title_element = container.find_element(
                    By.CSS_SELECTOR,
                    ".title-container h3.text",
                )
                img_title = driver.execute_script(
                    "return arguments[0].textContent;",
                    img_title_element,
                ).strip()
                logger.info("Found image title: %s", img_title)

                if not img_title:
                    logger.warning("Image title is empty")
                    continue

                img_element = container.find_element(
                    By.CSS_SELECTOR,
                    ".vx-grid-figure img.vx-grid-thumb",
                )
                img_src = img_element.get_attribute("src")

                if not img_src:
                    logger.warning("No src found for image, retrying...")
                    continue

                # Saving image
                response = get(img_src, timeout=10)
                response.raise_for_status()
                logger.info("Image downloaded successfully.")

                # saving image in tempfile
                with NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                    Image.open(BytesIO(response.content)).save(temp_file, format="PNG")
                    return temp_file.name

            except WebDriverException as e:
                if "disconnected" in str(e):
                    logger.warning("WebDriver disconnected. Restarting driver...")
                    driver.quit()
                    driver = uc.Chrome()
                    continue
                logger.warning(
                    "Error processing asset on attempt %d: %s",
                    attempt + 1,
                    str(e),
                )
                continue

        logger.error("No suitable image found after filtering.")
        return None

    except Exception as e:
        logger.exception("Error in _scrape_vexels_image: %s", str(e))
        return None

    finally:
        if driver:
            driver.quit()


def _start_generating(
    driver: uc.Chrome,
    image_dir: str,
    image_file_path: str,
    tor_binary_path: str | None,
) -> None:
    """Start generating an image using GPT and save it to a specified directory.

    :param driver: The Selenium WebDriver instance.
    :type driver: uc.Chrome
    :param image_dir: The directory to save the generated image.
    :type image_dir: str
    :param image_file_path: The path to the image file to upload.
    :type image_file_path: str
    :raises AbortScriptError: If any step in the generation process fails.
    """
    import time

    driver.set_page_load_timeout(30)
    # time.sleep(10) waits for JavaScript to decide if the GPT model allows file uploads.
    # Without this wait, the image might be sent too early before uploads are allowed.
    time.sleep(10)

    # Uploading image
    try:
        WebDriverWait(driver, 60).until(
            ec.presence_of_element_located((By.XPATH, "//input[@type='file']")),
        ).send_keys(image_file_path)
    except Exception as e:
        logger.error("Error uploading the image:")
        raise AbortScriptError("Could not upload the image.") from e
    _gpt_type_text(
        driver,
        "Always follow the following Prompt Guidelines."
        "Analyse the image and Only describe the pod design",
    )
    _gpt_send_prompt(driver)
    sleep(10)

    _gpt_type_text(
        driver,
        # "Analyse the image"
        "1. Generate a better pod design from this design description."
        # "Keep a balanced amount of negative space around the subject."
        "Make sure, everything is in view and zoomed out for a sticker"
        "Only the design/vector in view!"
        "1. Show the entire subject within the frame. (1024x1024), full in view"
        "2. Centered composition with all elements fully visible."
        "4. Isolate the graphic on a background color and just start creating it. "
        "5. Make it transparent."
        "6. improve the original design",
    )
    _gpt_send_prompt(driver)
    image_url = _get_image_src(driver)

    _gpt_type_text(
        driver,
        "Provide a concise title for Spreadshirt, for the first image max 40 characters.",
    )
    _gpt_send_prompt(driver)
    sleep(10)
    title = clean_string(_get_text_from_element(driver, class_index=5))
    if title is None:
        raise AbortScriptError("No title found!")

    _gpt_type_text(
        driver,
        "Provide a concise description for Spreadshirt, min 200,"
        "max 240 characters, based on the image.",
    )
    _gpt_send_prompt(driver)
    sleep(20)
    description = _get_text_from_element(driver, class_index=7)
    if description is None:
        raise AbortScriptError("No description found!")

    _gpt_type_text(
        driver,
        "Provide concise tags for Spreadshirt, min 20 words and max 25 words,"
        "separated by commas, based on the image.",
    )
    _gpt_send_prompt(driver)
    sleep(20)
    tags = _get_text_from_element(driver, class_index=9)
    if tags is None:
        raise AbortScriptError("No description found!")

    _gpt_type_text(
        driver,
        "DONE",
    )

    try:
        WebDriverWait(driver, 600).until(
            ec.element_to_be_clickable(
                (By.CSS_SELECTOR, "[data-testid='send-button']"),
            ),
        )
    except (TimeoutException, NoSuchElementException) as err:
        raise AbortScriptError("Sending Button not found!") from err
    _handle_errors(driver)

    driver.quit()
    result = _process_image(image_url, image_dir, title, tor_binary_path)
    write_metadata(
        title=title,
        tags=tags,
        description=description,
        directory=result,
    )

    try:
        Path(image_file_path).unlink()
    except Exception:
        logger.error("Error deleting temporary image file")


def generate_image_selenium_gpt(
    output_directory: str,
    tor_binary_path: str | None,
) -> None:
    """Main function to start the GPT generating process."""
    import time

    max_retries = 5
    retries = 0

    while retries < max_retries:
        try:
            logger.info("Starting Chrome and scraping image from Vexels.")
            driver = start_chrome("Default", None)
            active_drivers.append(driver)
            image_file_path = _scrape_vexels_image(driver)
            if image_file_path is None:
                raise AbortScriptError("Error scraping the image from vexels.com")
            if driver:
                driver.quit()
                active_drivers.remove(driver)

            logger.info("Starting ChatGPT session and generating image.")
            chatgpt_driver = _start_chat_gpt()
            active_drivers.append(chatgpt_driver)
            _start_generating(
                chatgpt_driver,
                output_directory,
                image_file_path,
                tor_binary_path,
            )
            active_drivers.remove(chatgpt_driver)

            logger.info("Image generation completed successfully.")
            break

        except AbortScriptError as err:
            logger.error("An error occurred: %s", err)
            err.close_all_drivers()
            retries += 1
            logger.info(
                "Restarting the process due to an unexpected error... (%d/%d)",
                retries,
                max_retries,
            )
            time.sleep(5)

        except Exception as err:
            logger.error("An unexpected error occurred: %s", err)
            for driver in active_drivers:
                driver.quit()
            active_drivers.clear()
            retries += 1
            logger.warning(
                "Restarting the process due to an unexpected error... (%d/%d)",
                retries,
                max_retries,
            )
            time.sleep(5)

    else:
        logger.error("Max retries reached. Exiting the process.")
