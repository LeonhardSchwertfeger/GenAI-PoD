# -*- coding: utf-8 -*-
# Copyright (C) 2024
# Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
# Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger
#

"""This module automates the process of uploading designs to Redbubble using SeleniumBase.

Features:
- Interacts with Redbubble's web interface, including file uploads, product adjustments
  and publishing.
- Handle overlays, modals and Cloudflare challenges to ensure smooth automation.
- Validate and read required files (e.g., images, titles, tags, descriptions)
  from local directories.
- Scale and adjust design sizes for various products based on predefined configurations.
- Log and manage errors, including missing files, upload failures,
  and browser interaction issues.

The module is designed for batch processing, iterating over
multiple directories containing design assets.
It handles success and failure scenarios by moving directories
to designated folders and provides detailed
logs to aid debugging and monitoring of the upload process.
"""
from __future__ import annotations

import logging
import sys
from json import load
from pathlib import Path
from shutil import move

from PIL import Image
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from seleniumbase import SB  # type: ignore[import]
from tqdm import tqdm

from genai_pod.utils import chromedata

logging.basicConfig(level=logging.INFO)


def upload_redbubble(**kwargs) -> None:
    """Main function to initialize the browser and start uploading designs to Redbubble.

    :param **kwargs: Keyword arguments, expecting 'upload_path' key specifying the path
        to upload images from.
    :type kwargs: dict[str, Any]
    """
    try:
        upload_path = kwargs.get("upload_path")
        if not upload_path:
            logging.error("upload_path not provided in kwargs.")
            return

        user_data_folder, chrome_profile = chromedata("Spreadshirt")

        with SB(
            uc=True,
            chromium_arg=[
                f"--user-data-dir={user_data_folder}",
                f"--profile-directory={chrome_profile}",
            ],
        ) as sb:
            logging.info("Browser launched with specified user data directory.")
            sb.open(
                "https://www.redbubble.com/portfolio/images/new?ref=account-nav-dropdown"
            )

            # Time to login manually for the first time
            try:
                sb.wait_for_element("#login-form-container", timeout=10)
                logging.info("Login form detected. Please log in manually.")
                sb.wait_for_element_absent("#login-form-container", timeout=120)
            except Exception:
                logging.info("You are logged in!")

            # Solving Cloudflare challenge
            try:
                verify_success(sb)
            except Exception as e:
                logging.exception("Failed to bypass Cloudflare: %s", e)

            logging.info("Starting iterate_and_upload.")
            iterate_and_upload(
                sb,
                upload_path,
                "used_redbubble",
                "error_redbubble",
            )
            logging.info("Finished the upload.")
    except Exception as e:
        logging.exception("An error occurred in upload_redbubble: %s", e)


def _click_button_by_data_type(sb: SB, data_type: str, action: str) -> None:
    """Click a button associated with a specific product data type on Redbubble.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    :param data_type: The data-type attribute value of the product to interact with.
    :type data_type: str
    :param action: The action to perform, either 'edit', 'enable', or 'disable'.
    :type action: str
    """
    try:
        element = sb.wait_for_element_visible(
            f"div.slide.with-uploader.has-image[data-type='{data_type}']",
            timeout=10,
        )

        if action == "edit":
            button_selector = "div.rb-button.edit-product"
        elif action == "enable":
            button_selector = "div.rb-button.enable-all"
        elif action == "disable":
            button_selector = "div.rb-button.disable-all.green"
        else:
            raise ValueError(
                "Invalid action specified. 'edit', 'enable', or 'disable' expected.",
            )

        sb.execute_script("arguments[0].scrollIntoView();", element)
        button = element.find_element(By.CSS_SELECTOR, button_selector)
        sb.execute_script("arguments[0].scrollIntoView();", button)
        button.click()
    except ElementClickInterceptedException:
        logging.info(
            "Click intercepted. Trying to close overlays and retrying for '%s'.",
            data_type,
        )
        _close_overlays(sb)
        button = sb.wait_for_element_visible(
            f"div.slide.with-uploader.has-image[data-type='{data_type}']",
            timeout=10,
        ).find_element(By.CSS_SELECTOR, button_selector)
        sb.execute_script("arguments[0].scrollIntoView();", button)
        button.click()
    except (NoSuchElementException, TimeoutException):
        logging.info("Product '%s' is no longer available.", data_type)
    except ElementNotInteractableException:
        logging.info(
            "Action '%s' already performed for product '%s'.",
            action,
            data_type,
        )
    except Exception as e:
        logging.exception(
            "Error clicking button for data_type '%s' and action '%s': %s",
            data_type,
            action,
            e,
        )


def _close_overlays(sb: SB) -> None:
    """Close any overlays or modals that might be blocking interactions.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    """
    try:
        if sb.is_element_visible("div#privacy-policy"):
            sb.click('button[aria-label="Close"]')
            logging.info("Closed privacy policy overlay.")
    except Exception:
        logging.info("Can't click on button[aria-label='Close'")

    try:
        if sb.is_element_visible("div.modal-dialog"):
            sb.click('button[aria-label="Close"]')
            logging.info("Closed modal dialog.")
    except Exception:
        logging.info("Can't click on button[aria-label='Close'")


def _load_config(filename: str) -> dict:
    """Load configuration settings from a JSON file.

    :param filename: The path to the JSON configuration file.
    :type filename: str
    :return: The loaded configuration, which can be a dictionary or a list
    :rtype: dict | list
    """
    with Path(filename).open(encoding="utf-8") as file:
        return load(file)


def _setup_clothes(sb: SB, base_scaling: str) -> None:
    """
    Select products and adjust their design sizes on Redbubble
    based on base scaling from the JSON.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    :param base_scaling: The base scaling identifier (e.g., '4096x4096')
                         used to select scaling adjustments.
    :type base_scaling: str
    """
    scaling_adjustments = _load_config("genai/resources/scaling_adjustments.json")

    if base_scaling in scaling_adjustments:
        product_adjustments = scaling_adjustments[base_scaling]
    else:
        logging.info("No adjustments defined for scaling value: %s", base_scaling)
        return

    for data_type, (action, final_scaling) in product_adjustments.items():
        adjust_product(sb, data_type, action, final_scaling)


def adjust_product(sb: SB, data_type: str, action: str, final_scaling: int) -> None:
    """Adjusts a single product based on the provided action and scaling.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    :param data_type: The data-type attribute of the product to adjust.
    :type data_type: str
    :param action: The action to perform ('edit', 'enable', 'disable').
    :type action: str
    :param final_scaling: The final scaling value for the design size.
    :type final_scaling: int
    """
    try:
        _click_button_by_data_type(sb, data_type, action)
        if action != "disable":
            _click_button_by_data_type(sb, data_type, "edit")
            _adjust_design_size(sb, data_type, final_scaling)
    except Exception as e:
        logging.exception("Failed to adjust product '%s': %s", data_type, e)


def _adjust_and_publish(sb: SB, image_path: str) -> None:
    """Adjust product settings based on image size and publish the design.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    :param image_path: The file path to the uploaded image.
    :type image_path: str
    """
    # Get image size
    with Image.open(image_path) as img:
        width = img.size[0]

    # Select the design size based on image width
    if width > 7000:
        _setup_clothes(sb, "8000x8000")
    elif width > 4000:
        _setup_clothes(sb, "4096x4096")
    elif width > 2000:
        _setup_clothes(sb, "2048x2048")
    elif width > 1000:
        _setup_clothes(sb, "1024x1024")
    else:
        logging.info("Design size too small.")
        raise Exception

    # Wait for the page to be ready
    sb.wait_for_ready_state_complete(timeout=30)

    # Close any overlays that might block interactions
    _close_overlays(sb)

    # Perform settings
    _select_media_types(sb)
    _set_safe_for_work(sb)
    _set_default_product(sb)
    _set_visibility(sb)
    _accept_user_agreement(sb)
    _publish_design(sb)

    # Navigate back to the new upload page
    sb.open("https://www.redbubble.com/portfolio/images/new")
    sb.sleep(4)
    logging.info("Finished _adjust_and_publish.")


def _select_media_types(sb: SB) -> None:
    """Select media types.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    """
    try:
        logging.info("Selecting media types.")
        sb.wait_for_element_visible("#media_design", timeout=10)
        sb.scroll_to("#media_design")
        sb.click("#media_design")
        sb.click("#media_digital")
        logging.info("Selected media types.")
    except Exception as e:
        logging.exception("Failed to select media types: %s", e)


def _set_safe_for_work(sb: SB) -> None:
    """Set content as safe for work.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    """
    try:
        sb.wait_for_element_visible("#work_safe_for_work_true", timeout=10)
        sb.scroll_to("#work_safe_for_work_true")
        sb.click("#work_safe_for_work_true")
        logging.info("Set content as safe for work.")
    except Exception as e:
        logging.exception("Failed to set content as safe for work: %s", e)


def _set_default_product(sb: SB) -> None:
    """Select T-Shirt as default product.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    """
    try:
        sb.wait_for_element_visible("#work_default_product", timeout=10)
        sb.scroll_to("#work_default_product")
        sb.select_option_by_text("#work_default_product", "T-Shirt")
        logging.info("Selected T-Shirt as default product.")
    except Exception as e:
        logging.exception("Failed to select default product: %s", e)


def _set_visibility(sb: SB) -> None:
    """Set visibility to public.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    """
    try:
        sb.wait_for_element_visible("#work_hidden_false", timeout=10)
        sb.scroll_to("#work_hidden_false")
        sb.click("#work_hidden_false")
        logging.info("Set visibility to public.")
    except Exception as e:
        logging.exception("Failed to set visibility: %s", e)


def _accept_user_agreement(sb: SB) -> None:
    """Accept user agreement.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    """
    try:
        sb.wait_for_element_visible("#rightsDeclaration", timeout=10)
        sb.scroll_to("#rightsDeclaration")
        sb.click("#rightsDeclaration")
        logging.info("Accepted user agreement.")
    except Exception as e:
        logging.exception("Failed to accept user agreement: %s", e)
    sb.sleep(3)


def _publish_design(sb: SB) -> None:
    """Publish the design.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    """
    try:
        sb.wait_for_element_visible("#submit-work", timeout=10)
        sb.scroll_to("#submit-work")
        sb.click("#submit-work")
        logging.info("Clicked publish button.")
    except Exception as e:
        logging.exception("Failed to click publish button: %s", e)
    sb.sleep(15)


def _adjust_design_size(sb: SB, data_type: str, slider_value: int) -> None:
    """Adjust the design size for a specific product on Redbubble.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    :param data_type: The data-type attribute of the product to adjust.
    :type data_type: str
    :param slider_value: The value to set the size slider to (0-100).
    :type slider_value: int
    """
    class_name = _find_and_adjust_design_size(sb, data_type)
    if class_name:
        try:
            parent_div = sb.wait_for_element_visible(
                f"div.{class_name.replace(' ', '.')}",
                timeout=10,
            )

            slider = parent_div.find_element(By.XPATH, ".//input[@type='range']")
            slider.send_keys(Keys.HOME)
            slider.send_keys(Keys.RIGHT * slider_value)

            # Execute JavaScript to click buttons
            sb.execute_script(
                """
                const parentDiv = arguments[0];
                parentDiv.querySelectorAll("button").forEach(button => {
                    const value = button.getAttribute('value') || '';
                    const text = button.textContent || '';
                    if (value.toLowerCase() === 'center vertically'.toLowerCase()) {
                        button.click();
                    } else if (value.toLowerCase() === 'center horizontally'.toLowerCase()) {
                        button.click();
                    } else if (text.toLowerCase().includes('apply changes'.toLowerCase())) {
                        button.click();
                    }
                });
            """,
                parent_div,
            )

        except Exception:
            logging.exception("Error adjusting design size for '%s'", data_type)
    else:
        logging.info("No valid class name found. Does '%s' still exist?", data_type)


def _find_and_adjust_design_size(sb: SB, data_type: str) -> str | None:
    """Find the complete class name starting with 'image-box' for a given data type.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    :param data_type: The data-type attribute of the product.
    :type data_type: str
    :return: The class name if found, else None.
    :rtype: str | None
    """
    try:
        sb.wait_for_element_present(
            f"div.image-box[data-type='{data_type}']",
            timeout=10,
        )
        parent_divs = sb.find_elements(f"div.image-box[data-type='{data_type}']")

        if parent_divs:
            return parent_divs[0].get_attribute("class")
        logging.info("No suitable div element found for data type '%s'.", data_type)
        return None
    except Exception:
        logging.exception(
            "No suitable div element found for data type '%s'.", data_type
        )
        return None


def verify_success(sb: SB) -> None:
    """Function to solve Cloudflare challenge using SeleniumBase.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    """
    try:
        sb.assert_element('img[alt="Logo Assembly"]', timeout=8)
    except Exception:
        if sb.is_element_visible('input[value*="Verify"]'):
            sb.click('input[value*="Verify"]')
        elif sb.is_element_visible('iframe[title*="challenge"]'):
            sb.switch_to.frame(sb.find_element('iframe[title*="challenge"]'))
            sb.click("span.mark")
            sb.switch_to.default_content()
        else:
            raise Exception("Detected!") from None

    sb.open("https://www.redbubble.com/portfolio/images/new?ref=account-nav-dropdown")
    sb.sleep(30)


def _upload_with_selenium(
    sb: SB,
    description: str,
    tag: str,
    title: str,
    image_path: str,
) -> None:
    """Perform the upload process to Redbubble using SeleniumBase.

    :param sb: The SeleniumBase instance.
    :type sb: SB
    :param description: The description of the artwork.
    :type description: str
    :param tag: A comma-separated string of tags.
    :type tag: str
    :param title: The title of the artwork.
    :type title: str
    :param image_path: The file path to the image to be uploaded.
    :type image_path: str
    """
    logging.info("Starting upload with image: %s", image_path)
    tags_list = tag.strip().split(",")
    if len(tags_list) > 15:
        tags_list = tags_list[:15]
    tags_str = ",".join(tags_list)

    sb.wait_for_ready_state_complete(timeout=30)

    # Dismiss cookie consent banner if present
    if sb.is_element_visible("button#onetrust-accept-btn-handler"):
        sb.click("button#onetrust-accept-btn-handler")
        logging.info("Closed cookie consent banner.")

    # Dismiss any modals if present
    _close_overlays(sb)

    # image input
    try:
        file_input = sb.driver.find_element(By.ID, "select-image-single")
        file_input.send_keys(image_path)
    except Exception as e:
        if sb.driver.find_element(By.CLASS_NAME, "exceeded-upload-limit"):
            logging.info("***Exceeded upload limit!***")
            sys.exit(1)

        logging.exception("Failed to send image path to file input: %s", e)
        raise Exception from e  # Skipping to the next image

    # Wait for the image to finish uploading
    sb.sleep(20)

    # Wait for the title field to be ready
    sb.wait_for_element("#work_title_en", timeout=20)

    # Set the title
    sb.type("#work_title_en", title)
    logging.info("Set title.")

    # Set the tags
    sb.type("#work_tag_field_en", tags_str)
    logging.info("Set tags.")

    # Set the description
    sb.type("#work_description_en", description)
    logging.info("Set description.")

    # Proceed with adjusting product settings and publishing
    _adjust_and_publish(sb, image_path)


def iterate_and_upload(
    sb: SB,
    upload_path: str,
    folder: str,
    error_folder: str,
) -> None:
    """Iterates over folders in upload_path and uploads designs using SeleniumBase.
    Excludes folders specified in the 'exclude_folders' list.

    :param sb: SeleniumBase instance used for browser interactions.
    :type sb: SB
    :param upload_path: Path containing folders with designs to upload.
    :type upload_path: str
    :param folder: Destination folder for successful uploads.
    :type folder: str
    :param error_folder: Destination folder for failed uploads.
    :type error_folder: str
    """
    logging.info("Starting iterate_and_upload in path: %s", upload_path)
    exclude_folders = [folder, error_folder]
    base_path = Path(upload_path)

    (base_path / folder).mkdir(parents=True, exist_ok=True)
    (base_path / error_folder).mkdir(parents=True, exist_ok=True)

    subdirs = [
        subdir
        for subdir in base_path.iterdir()
        if subdir.is_dir() and subdir.name not in exclude_folders
    ]

    if not subdirs:
        logging.warning(
            "No subdirectories found to process. Exiting iterate_and_upload."
        )
        return

    for subdir in tqdm(subdirs, desc="Processing designs"):
        logging.info("Processing subdirectory: %s", subdir)
        result = process_subdir(subdir, base_path, folder, error_folder, sb)
        if not result:
            logging.error("An error occurred during processing folder %s.", subdir)

    logging.info("Finished iterate_and_upload.")


def process_subdir(
    subdir: Path, base_path: Path, folder: str, error_folder: str, sb: SB
) -> bool:
    """Processes a single subdirectory by validating required files and attempting to upload
    its content.

    :param subdir: The subdirectory containing the design files to upload.
    :type subdir: Path
    :param base_path: The base path where the subdirectories are located.
    :type base_path: Path
    :param folder: The folder name to move successful uploads to.
    :type folder: str
    :param error_folder: The folder name to move failed uploads to.
    :type error_folder: str
    :param sb: SeleniumBase instance used for browser interactions.
    :type sb: SB
    :returns: Whether the upload was successful.
    :rtype: bool
    """
    try:
        logging.info("Starting to process subdir: %s", subdir)

        # Searching for an image file in the subdirectory
        image_file = next(
            (file for ext in ["*.png", "*.jpg", "*.jpeg"] for file in subdir.glob(ext)),
            None,
        )
        if image_file:
            logging.debug("Found image file: %s", image_file)
        else:
            raise FileNotFoundError(f"No image file found in {subdir}")

        # Defining required file names
        required_files = ["description.txt", "tags.txt", "title.txt"]

        # Content from required files
        contents = {}
        for file_name in required_files:
            file_path = subdir / file_name
            if not file_path.exists():
                raise FileNotFoundError(f"No {file_name} found in {subdir}")
            with file_path.open("r", encoding="utf-8") as f:
                contents[file_name.split(".", maxsplit=1)[0]] = f.read().strip()

        # Attempt to upload using the provided upload function
        _upload_with_selenium(
            sb,
            description=contents["description"],
            tag=contents["tags"],
            title=contents["title"],
            image_path=str(image_file),
        )

        logging.info("Successfully uploaded %s. Moving to %s.", subdir, folder)
        move(str(subdir), base_path / folder)

    except FileNotFoundError as e:
        logging.exception(str(e))
        move(str(subdir), base_path / error_folder)
        return False
    except Exception as e:
        logging.exception("Error processing folder %s: %s", subdir, e)
        move(str(subdir), base_path / error_folder)
        return False

    return True
