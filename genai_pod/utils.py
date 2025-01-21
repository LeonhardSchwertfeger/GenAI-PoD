# -*- coding: utf-8 -*-
# Copyright (C) 2024
# Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
# Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger
#

"""This module provides utilities for managing browser cookies and
automating the setup of a Chrome browser profile for web interactions.

Features:
- Save and load cookies to/from a JSON file, enabling session persistence across browser sessions.
- Create user-specific Chrome profile directories for isolated browsing contexts.
- Launch Chrome with a specified profile and preloaded cookies for seamless website interactions.

This module simplifies session persistence and browser
profile management for automated web interactions.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import undetected_chromedriver as uc  # type: ignore[import]
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class UploadConfig:
    """Configuration settings for the upload process.

    :ivar upload_path: The path where files to be uploaded are located.
    :vartype upload_path: str
    :ivar upload_function: The function responsible for handling the upload.
    :vartype upload_function: Callable[..., Any]
    :ivar used_folder_name: The name of the folder where successfully uploaded files are moved.
    :vartype used_folder_name: str
    :ivar error_folder_name: The name of the folder where files that failed to upload are moved.
    :vartype error_folder_name: str
    :ivar exclude_folders: A list of folder names to exclude from processing. Defaults to None.
    :vartype exclude_folders: list[str] | None
    """

    upload_path: str
    upload_function: Callable[..., Any]
    used_folder_name: str
    error_folder_name: str
    exclude_folders: list[str]


def start_chrome(chrome_profile: str, output_directory: Path | None) -> uc.Chrome:
    """Launches a Chrome browser instance using the specified parameters.

    The `chrome_profile` parameter is always required. If `output_directory` is provided,
    the browser is configured with additional settings for file downloads and remote debugging.

    :param chrome_profile: The name of the Chrome profile to use (required).
    :type chrome_profile: str
    :param output_directory: The directory where downloads will be saved,
    or None if no such directory is specified.
    :type output_directory: Path | None
    :return: An instance of the undetected_chromedriver Chrome WebDriver.
    :rtype: uc.Chrome
    """
    from genai_pod.utilitys.bg_remove import (  # pylint: disable=cyclic-import
        AbortScriptError,
    )

    user_data_dir = Path("chromedata").resolve()

    try:
        used_profile_dir, used_profile_name = _prepare_profile_directory(
            user_data_dir,
            chrome_profile,
            output_directory,
        )
        chrome_options = _build_chrome_options(
            used_profile_dir,
            used_profile_name,
            output_directory,
        )
        driver = _launch_chrome(chrome_options)

        if output_directory:
            _configure_download_behavior(driver, output_directory)
        if chrome_profile != "Default":
            _load_existing_cookies(driver, user_data_dir)

        return driver
    except Exception as e:
        logger.exception("Error starting Chrome: %s", e)
        if "driver" in locals() and driver:
            driver.quit()
        raise AbortScriptError("Error starting Chrome") from e


def _create_profile_directory(user_data_dir: Path, profile_name: str) -> None:
    """Create a user profile directory if it doesn't exist.

    :param user_data_dir: The base directory for user data.
    :type user_data_dir: Path
    :param profile_name: The name of the profile directory to create.
    :type profile_name: str
    """
    profile_path = user_data_dir / profile_name
    profile_path.mkdir(parents=True, exist_ok=True)


def _prepare_profile_directory(
    user_data_dir: Path, chrome_profile: str, output_directory: Path | None
) -> tuple[Path, str]:
    """Prepares the directory structure for the specified Chrome profile.

    If `output_directory` is provided, session files are cleared to ensure a clean browser state.
    Otherwise, a profile directory is created if it does not exist.

    :param user_data_dir: The base directory for user data.
    :type user_data_dir: Path
    :param chrome_profile: The name of the Chrome profile to prepare.
    :type chrome_profile: str
    :param output_directory: The directory for downloads, or None if not required.
    :type output_directory: Path | None
    :return: A tuple containing the resolved profile directory path and the profile name.
    :rtype: tuple[Path, str]
    """
    if output_directory:
        output_directory.mkdir(parents=True, exist_ok=True)
        profile_dir = user_data_dir / chrome_profile
        _clear_session_files(profile_dir)
        return profile_dir.parent, profile_dir.name
    _create_profile_directory(user_data_dir, chrome_profile)
    return user_data_dir, chrome_profile


def _clear_session_files(profile_dir: Path) -> None:
    """Removes session-related files from the given profile directory to start with a clean state.

    :param profile_dir: The directory containing the Chrome profile data.
    :type profile_dir: Path
    """
    for session_file in [
        "Current Session",
        "Current Tabs",
        "Last Session",
        "Last Tabs",
    ]:
        file_path = profile_dir / session_file
        if file_path.exists():
            file_path.unlink()


def _build_chrome_options(
    user_data_dir: Path, profile_name: str, output_directory: Path | None
) -> uc.ChromeOptions:
    """Constructs and configures ChromeOptions for undetected_chromedriver.

    If `output_directory` is provided, additional options for remote debugging, notifications,
    and download settings are applied.

    :param user_data_dir: The base directory for user data.
    :type user_data_dir: Path
    :param profile_name: The name of the Chrome profile to use.
    :type profile_name: str
    :param output_directory: The directory for downloads, or None if not required.
    :type output_directory: Path | None
    :return: Configured ChromeOptions instance.
    :rtype: uc.ChromeOptions
    """
    chrome_options = uc.ChromeOptions()
    chrome_options.binary_location = get_chrome_path()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument(f"--profile-directory={profile_name}")
    chrome_options.add_argument("-lang=de-DE")

    if output_directory:
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": str(output_directory),
                "download.prompt_for_download": False,
                "profile.default_content_settings.popups": 0,
                "download.directory_upgrade": True,
                "intl.accept_languages": "de-DE",
            },
        )
    return chrome_options


def _launch_chrome(chrome_options: uc.ChromeOptions) -> uc.Chrome:
    """Launches the Chrome browser using undetected_chromedriver with the specified options.

    If running on an aarch64 architecture, a special path must be provided.

    :param chrome_options: The ChromeOptions instance to configure the driver.
    :type chrome_options: uc.ChromeOptions
    :return: A running instance of the Chrome WebDriver.
    :rtype: uc.Chrome
    """
    import os
    import platform
    import sys

    if platform.machine() == "aarch64":
        path = "Paste here your undetected_chromedriver/chromedriver_copy path"
        if not os.path.exists(path):
            logger.error(
                "You have an aarch64 Architecture. "
                "Please follow the steps in aarch64_README.md!"
            )
            sys.exit(0)
        return uc.Chrome(options=chrome_options, driver_executable_path=path)
    return uc.Chrome(options=chrome_options)


def _configure_download_behavior(driver: uc.Chrome, output_directory: Path) -> None:
    """Configures the given Chrome WebDriver instance to allow
    file downloads to the specified directory without prompts
    or popups, and navigates to a given URL after setup.

    :param driver: The Chrome WebDriver instance.
    :type driver: uc.Chrome
    :param output_directory: The directory where files will be downloaded.
    :type output_directory: Path
    """
    driver.execute_cdp_cmd(
        "Page.setDownloadBehavior",
        {
            "behavior": "allow",
            "downloadPath": str(output_directory),
        },
    )
    driver.get("https://www.remove.bg/de")


def _load_existing_cookies(driver: uc.Chrome, user_data_dir: Path) -> None:
    """Loads existing cookies from a JSON file (if available) into the
    given Chrome WebDriver instance, and then refreshes the page to
    ensure the cookies are applied.

    :param driver: The Chrome WebDriver instance.
    :type driver: uc.Chrome
    :param user_data_dir: The base directory for user data, where the cookies file is located.
    :type user_data_dir: Path
    """
    cookies_path = user_data_dir / "cookies.json"
    if cookies_path.exists() and cookies_path.stat().st_size > 0:
        load_cookies(driver, cookies_path)
        driver.refresh()


def chromedata(chrome_profile: str) -> tuple[str, str]:
    """Creates a chromedata folder with all profiles.

    :param chrome_profile: The name of the Chrome profile.
    :type chrome_profile: str
    :return: A tuple containing the user data directory and the profile directory.
    :rtype: tuple[str, str]
    """
    chromedata_path = Path(__file__).parents[2] / "chromedata"
    chromedata_path.mkdir(parents=True, exist_ok=True)
    return (str(chromedata_path), chrome_profile)


def write_metadata(
    title: str,
    description: str,
    tags: str,
    directory: Path,
) -> None:
    """Writes metadata to title.txt, description.txt, and tags.txt.

    :param title: The title to save.
    :type title: str
    :param description: The description to save.
    :type description: str
    :param tags: The tags to save.
    :type tags: str
    :param directory: The directory where metadata files will be saved.
    :type directory: Path
    """
    logger.info("Writing metadata to %s", directory)
    directory.mkdir(parents=True, exist_ok=True)

    # Write title
    with (directory / "title.txt").open("a", encoding="utf-8") as f:
        f.write(f"{title}\n")

    # Write tags
    with (directory / "tags.txt").open("a", encoding="utf-8") as f:
        f.write(f"{tags}\n")

    # Write description
    with (directory / "description.txt").open("a", encoding="utf-8") as f:
        f.write(f"{description}\n")


def clean_string(string: str) -> str:
    """Removes specific characters from a string.

    :param string: The string to clean.
    :type string: str
    :return: The cleaned string.
    :rtype: str
    """
    from re import sub

    return sub(r'[\\/*?:"<>|]', "", string)


def iterate_and_upload(
    driver: Any,
    config: UploadConfig,
) -> None:
    """General function to iterate over subdirectories in upload_path and upload designs
    using the provided upload_function.

    :param driver: The driver instance (e.g., uc.Chrome or SeleniumBase SB).
    :type driver: Any
    :param config: Configuration settings for the upload process.
    :type config: UploadConfig
    """
    logger.info("Starting iterate_and_upload in path: %s", config.upload_path)
    if config.exclude_folders is None:
        config.exclude_folders = [config.used_folder_name, config.error_folder_name]
    base_path = Path(config.upload_path)

    (base_path / config.used_folder_name).mkdir(parents=True, exist_ok=True)
    (base_path / config.error_folder_name).mkdir(parents=True, exist_ok=True)

    subdirs = [
        subdir
        for subdir in base_path.iterdir()
        if subdir.is_dir() and subdir.name not in config.exclude_folders
    ]

    logger.debug("Found %d subdirectories to process.", len(subdirs))

    if not subdirs:
        logger.warning("No subdirectories found to process. Exiting iterating process.")
        return

    for subdir in subdirs:
        logger.info("Processing subdirectory: %s", subdir)
        result = process_subdir(
            subdir=subdir,
            base_path=base_path,
            driver=driver,
            config=config,
        )
        if not result:
            logger.error("An error occurred during processing folder %s.", subdir)

    logger.info("Finished iterate_and_upload.")


def process_subdir(
    subdir: Path,
    base_path: Path,
    driver: Any,
    config: UploadConfig,
) -> bool:
    """Processes a single subdirectory by validating required files and attempting to upload
    its content.

    :param subdir: The subdirectory containing the design files to upload.
    :type subdir: Path
    :param base_path: The base path where the subdirectories are located.
    :type base_path: Path
    :param driver: The driver instance (e.g., uc.Chrome or SeleniumBase SB).
    :type driver: Any
    :param config: Configuration settings for the upload process.
    :type config: UploadConfig
    :return: True if the upload was successful; False otherwise.
    :rtype: bool
    """
    from shutil import move

    logger.info("Starting to process subdir: %s", subdir)
    try:
        image_file = find_image_file(subdir)

        # Validate and read required files
        description_text = read_file_contents(subdir / "description.txt")
        tags_text = read_file_contents(subdir / "tags.txt")
        title_text = read_file_contents(subdir / "title.txt")

        # Attempt to upload using the provided upload function
        logger.debug("Calling upload function.")
        success = config.upload_function(
            driver=driver,
            description=description_text,
            tag=tags_text,
            title=title_text,
            image_path=str(image_file),
        )

        target_folder = config.used_folder_name if success else config.error_folder_name
        move(str(subdir), base_path / target_folder)
        if success:
            logger.debug(
                "Successfully uploaded %s. Moving to %s.", subdir, target_folder
            )
        else:
            logger.error("Upload failed for folder %s.", subdir)
        return success

    except FileNotFoundError as e:
        logger.exception(str(e))
        move(str(subdir), base_path / config.error_folder_name)
    except Exception as e:
        logger.exception("Error processing folder %s: %s", subdir, e)
        move(str(subdir), base_path / config.error_folder_name)

    return False


def find_image_file(subdir: Path) -> Path:
    """Finds the first image file in the subdirectory.

    :param subdir: The subdirectory to search for image files.
    :type subdir: Path
    :return: The path to the first found image file.
    :rtype: Path
    :raises FileNotFoundError: If no image file is found in the subdirectory.
    """
    for ext in ["*.png", "*.jpg", "*.jpeg"]:
        files = list(subdir.glob(ext))
        if files:
            logger.debug("Found image file: %s", files[0])
            return files[0]
    raise FileNotFoundError(f"No image file found in {subdir}")


def read_file_contents(file_path: Path) -> str:
    """Reads and returns the stripped content of a file.

    :param file_path: The path to the file to read.
    :type file_path: Path
    :return: The stripped content of the file.
    :rtype: str
    """
    with file_path.open("r", encoding="utf-8") as f:
        content = f.read().strip()
        logger.debug("Read from %s: %s", file_path.name, content)
        return content


def get_chrome_path() -> str:
    """Determines the path to the Chrome executable based on the operating system.

    :return: The path to the Chrome executable.
    :rtype: str
    :raises Exception: If the operating system is unsupported.
    """
    import platform

    os_name = platform.system().lower()
    if os_name == "darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # chrome://version
    if os_name == "windows":
        return "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
    if os_name == "linux":
        if platform.machine() == "aarch64":
            return "/usr/bin/chromium-browser"
        return "/usr/bin/google-chrome"
    raise Exception(f"Unsupported OS: {os_name}")


def save_cookies(driver: uc.Chrome, path: Path) -> None:
    """Save the browser cookies from the WebDriver to a file.

    :param driver: The WebDriver instance from which to get cookies.
    :type driver: uc.Chrome
    :param path: The file path where the cookies will be saved.
    :type path: Path
    """
    with path.open("w", encoding="utf-8") as file:
        json.dump(driver.get_cookies(), file)


def load_cookies(driver: uc.Chrome, path: Path) -> None:
    """Load browser cookies from a specified file path and add them to the driver.

    :param driver: The selenium uc.Chrome instance.
    :type driver: uc.Chrome
    :param path: The file path from which the cookies will be loaded.
    :type path: Path
    """
    from selenium.common.exceptions import NoSuchElementException, TimeoutException

    if not path.exists() or path.stat().st_size == 0:
        return

    with path.open("r", encoding="utf-8") as file:
        cookies = json.load(file)

    current_url = driver.current_url
    for cookie in cookies:
        try:
            if cookie.get("domain", "").startswith("."):
                cookie["domain"] = cookie["domain"].lstrip(".")

            if cookie["domain"] in current_url:
                driver.add_cookie(cookie)
            else:
                logger.debug(
                    "Skipping cookie for domain '%s' (current URL: %s)",
                    cookie["domain"],
                    current_url,
                )

        except (NoSuchElementException, TimeoutException) as e:
            logger.exception("Error adding cookie: %s", e)
        except Exception as e:
            logger.exception("Unexpected error adding cookie: %s", e)


def pilling_image(image_path: str) -> None:
    """Processes an image by adjusting transparency and blending
    it with a white background more efficiently.

    :param image_path: The path to the PNG image file to be processed.
    :type image_path: str

    This function performs the following steps:
    1. Opens the image and converts it to RGBA mode for transparency handling.
    2. Converts the image into a NumPy array for efficient processing.
    3. Creates masks based on the alpha (transparency) values of the pixels.
       - Pixels with alpha greater than 153 (more than 60% opacity) are adjusted.
       - Pixels with alpha 153 or less (60% or less opacity) are made fully transparent.
    4. Adjusts the RGB values of the pixels with high opacity, blending them with white background.
    5. Sets the alpha channel of adjusted pixels to full opacity (255).
    6. Saves the modified image as a new PNG file with "_customised" added to the original filename.
    """
    import numpy as np  # type: ignore[import]

    image = Image.open(image_path).convert("RGBA")
    image_array = np.array(image).astype(np.float32)

    r, g, b, a = (
        image_array[:, :, 0],
        image_array[:, :, 1],
        image_array[:, :, 2],
        image_array[:, :, 3],
    )

    mask_high_alpha = a > 153
    mask_low_alpha = a <= 153
    image_array[mask_low_alpha] = [0, 0, 0, 0]

    if np.any(mask_high_alpha):
        delta = (255 - a[mask_high_alpha]) / 255.0

        image_array[:, :, 0][mask_high_alpha] = (
            r[mask_high_alpha] + (255 - r[mask_high_alpha]) * delta
        )
        image_array[:, :, 1][mask_high_alpha] = (
            g[mask_high_alpha] + (255 - g[mask_high_alpha]) * delta
        )
        image_array[:, :, 2][mask_high_alpha] = (
            b[mask_high_alpha] + (255 - b[mask_high_alpha]) * delta
        )
        image_array[:, :, 3][mask_high_alpha] = 255

    new_image = Image.fromarray(image_array.astype("uint8"), "RGBA")
    new_image_path = image_path.replace(".png", "_pil.png")
    new_image.save(new_image_path)
