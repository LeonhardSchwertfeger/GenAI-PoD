#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2024
# Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
# Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger

"""
This module provides utilities for managing browser cookies, automating the setup of a
Chrome browser profile for web interactions, and file operations.

Features:
- Save and load cookies to/from a JSON file, enabling session persistence across browser sessions.
- Create user-specific Chrome profile directories for isolated browsing contexts.
- Launch Chrome with a specified profile and preloaded cookies for seamless website interactions.
- Configure browser download settings.
- Write and manage metadata files.
- Process directories for uploading content.
- Additional utilities for image processing and string cleaning.

This module simplifies session persistence, browser profile management,
 and file operations for automated web interactions.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import undetected_chromedriver as uc

logger = logging.getLogger(__name__)


@dataclass
class UploadConfig:
    """
    Configuration for upload processes.

    :ivar upload_path: The path where files to be uploaded are located.
    :vartype upload_path: str
    :ivar upload_function: The function responsible for handling the upload.
    :vartype upload_function: Callable[..., bool]
    :ivar used_folder_name: The name of the folder where successfully uploaded files are moved.
    :vartype used_folder_name: str
    :ivar error_folder_name: The name of the folder where files that failed to upload are moved.
    :vartype error_folder_name: str
    :ivar exclude_folders: A list of folder names to exclude from processing. Defaults to None.
    :vartype exclude_folders: list[str] | None
    """

    upload_path: str
    upload_function: Callable[..., bool]
    used_folder_name: str
    error_folder_name: str
    exclude_folders: list[str] | None


def start_chrome(chrome_profile: str, output_directory: Path | None) -> uc.Chrome:
    """
    Launches a Chrome browser instance using the specified parameters.

    The chrome_profile parameter is required. If output_directory is provided,
    the browser is configured with additional settings for file downloads and remote debugging.

    :param chrome_profile: The name of the Chrome profile to use.
    :type chrome_profile: str
    :param output_directory: The directory where downloads will be saved, or None if not specified.
    :type output_directory: Path | None
    :return: An instance of the undetected_chromedriver Chrome WebDriver.
    :rtype: uc.Chrome
    :raises AbortScriptError: If Chrome initialization fails.
    """
    from genai_pod.generators.generate_gpt import AbortScriptError

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
        logger.error(
            "Failed to initialize Chrome: %s",
            str(e),
            exc_info=logger.level <= logging.DEBUG,
        )
        if "driver" in locals() and driver:
            driver.quit()
        raise AbortScriptError("Chrome initialization failed") from e


def _create_profile_directory(user_data_dir: Path, profile_name: str) -> None:
    """
    Create a user profile directory if it doesn't exist.

    :param user_data_dir: The base directory for user data.
    :type user_data_dir: Path
    :param profile_name: The name of the profile directory to create.
    :type profile_name: str
    """
    profile_path = user_data_dir / profile_name
    profile_path.mkdir(parents=True, exist_ok=True)
    logger.debug("Created profile directory: %s", profile_path)


def _prepare_profile_directory(
    user_data_dir: Path,
    chrome_profile: str,
    output_directory: Path | None,
) -> tuple[Path, str]:
    """
    Prepare the directory structure for the specified Chrome profile.

    If output_directory is provided, session files are cleared to ensure a clean browser state.
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
    """
    Removes session-related files from the given profile directory to start with a clean state.

    :param profile_dir: The directory containing the Chrome profile data.
    :type profile_dir: Path
    """
    session_files = ["Current Session", "Current Tabs", "Last Session", "Last Tabs"]
    for session_file in session_files:
        file_path = profile_dir / session_file
        if file_path.exists():
            file_path.unlink()
            logger.debug("Removed session file: %s", file_path)


def _build_chrome_options(
    user_data_dir: Path,
    profile_name: str,
    output_directory: Path | None,
) -> uc.ChromeOptions:
    """
    Construct and configure ChromeOptions for undetected_chromedriver.

    Additional options for remote debugging, notifications,
    and download settings are applied if output_directory is provided.

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
        # Optionally disable popup blocking (as seen in previous version)
        chrome_options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": str(output_directory),
                "download.prompt_for_download": False,
                "profile.default_content_settings.popups": 0,
                "download.directory_upgrade": True,
            },
        )
        logger.debug("Configured download directory: %s", output_directory)

    return chrome_options


def _launch_chrome(chrome_options: uc.ChromeOptions) -> uc.Chrome:
    """
    Launch the Chrome browser instance using undetected_chromedriver with the specified options.

    For aarch64 architecture, a specific chromedriver path must be provided.

    :param chrome_options: The ChromeOptions instance to configure the driver.
    :type chrome_options: uc.ChromeOptions
    :return: A running instance of the Chrome WebDriver.
    :rtype: uc.Chrome
    :raises RuntimeError: If the chromedriver path is invalid for aarch64.
    """
    import platform

    if platform.machine() == "aarch64":
        path = "/path/to/chromedriver"  # Update with actual path for aarch64
        if not Path(path).exists():
            logger.error("Missing Chromedriver for aarch64 architecture")
            raise RuntimeError("Invalid Chromedriver path")
        return uc.Chrome(options=chrome_options, driver_executable_path=path)

    return uc.Chrome(options=chrome_options)


def _configure_download_behavior(driver: uc.Chrome, output_directory: Path) -> None:
    """
    Configure browser download settings.

    Sets the browser to allow downloads to the specified directory without prompts.
    Note: The previous version navigated to a specific URL after
    configuration – this behavior has been omitted.

    :param driver: The Chrome WebDriver instance.
    :type driver: uc.Chrome
    :param output_directory: The directory where files will be downloaded.
    :type output_directory: Path
    """
    driver.execute_cdp_cmd(
        "Page.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": str(output_directory)},
    )
    logger.debug("Configured download behavior for path: %s", output_directory)


def _load_existing_cookies(driver: uc.Chrome, user_data_dir: Path) -> None:
    """
    Load cookies from a JSON file into the browser and refresh the page.

    If a cookies file exists and is not empty, cookies are loaded
    and the browser is refreshed to apply them.

    :param driver: The Chrome WebDriver instance.
    :type driver: uc.Chrome
    :param user_data_dir: The base directory for user data, where the cookies file is located.
    :type user_data_dir: Path
    """
    cookies_path = user_data_dir / "cookies.json"
    if cookies_path.exists() and cookies_path.stat().st_size > 0:
        logger.debug("Loading cookies from: %s", cookies_path)
        load_cookies(driver, cookies_path)
        driver.refresh()


def write_metadata(title: str, description: str, tags: str, directory: Path) -> None:
    """
    Write metadata to text files.

    Saves the title, tags, and description into separate text files within the specified directory.

    :param title: The title to save.
    :type title: str
    :param description: The description to save.
    :type description: str
    :param tags: The tags to save.
    :type tags: str
    :param directory: The directory where metadata files will be saved.
    :type directory: Path
    """
    directory.mkdir(parents=True, exist_ok=True)

    with (directory / "title.txt").open("a", encoding="utf-8") as f:
        f.write(f"{title}\n")

    with (directory / "tags.txt").open("a", encoding="utf-8") as f:
        f.write(f"{tags}\n")

    with (directory / "description.txt").open("a", encoding="utf-8") as f:
        f.write(f"{description}\n")

    logger.info("Metadata saved to: %s", directory)


def iterate_and_upload(driver: Any, config: UploadConfig) -> None:
    """
    Iterate over subdirectories in the upload path and upload
    their content using the provided upload function.

    If exclude_folders is not set, it defaults to excluding the used and error folder names.
    Ensures that the directories for successfully uploaded and error cases exist.

    :param driver: The WebDriver instance.
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
    subdir: Path, base_path: Path, driver: Any, config: UploadConfig
) -> bool:
    """
    Process a single subdirectory by validating required files
    and attempting to upload its content.

    Reads the image file, title, description, and tags from the subdirectory,
    then calls the upload function.
    Moves the subdirectory to the appropriate
    folder based on the success of the upload.

    :param subdir: The subdirectory containing the files to be uploaded.
    :type subdir: Path
    :param base_path: The base path where the subdirectories are located.
    :type base_path: Path
    :param driver: The WebDriver instance.
    :type driver: Any
    :param config: Configuration settings for the upload process.
    :type config: UploadConfig
    :return: True if the upload was successful, False otherwise.
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


def get_chrome_path() -> str:
    """
    Determine the path to the Chrome executable based on the operating system.

    For Linux systems, if running on aarch64, a different path might be required.

    :return: The path to the Chrome executable.
    :rtype: str
    :raises RuntimeError: If the operating system is unsupported.
    """
    import platform

    system = platform.system().lower()
    if system == "darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if system == "windows":
        return "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
    if system == "linux":
        return "/usr/bin/google-chrome"

    raise RuntimeError(f"Unsupported OS: {system}")


def save_cookies(driver: uc.Chrome, path: Path) -> None:
    """
    Save browser cookies to a JSON file.

    :param driver: The WebDriver instance from which to get cookies.
    :type driver: uc.Chrome
    :param path: The file path where the cookies will be saved.
    :type path: Path
    """
    with path.open("w", encoding="utf-8") as file:
        json.dump(driver.get_cookies(), file)
    logger.debug("Saved cookies to: %s", path)


def load_cookies(driver: uc.Chrome, path: Path) -> None:
    """
    Load cookies from a JSON file into the browser.

    Reads cookies from the specified file and adds them to the driver.
    Logs any issues encountered while adding cookies.

    :param driver: The Chrome WebDriver instance.
    :type driver: uc.Chrome
    :param path: The file path from which the cookies will be loaded.
    :type path: Path
    """
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as file:
        cookies = json.load(file)

    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            logger.debug("Error while adding cookie: %s (%s)", cookie, type(e).__name__)
        except Exception as e:
            logger.debug("Failed to add cookie: %s", str(e))

    logger.debug("Loaded %d cookies", len(cookies))


def chromedata(chrome_profile: str) -> tuple[str, str]:
    """
    Create a chromedata folder with all profiles.

    :param chrome_profile: The name of the Chrome profile.
    :type chrome_profile: str
    :return: A tuple containing the chromedata directory and the profile name.
    :rtype: tuple[str, str]
    """
    chromedata_path = Path(__file__).parents[2] / "chromedata"
    chromedata_path.mkdir(parents=True, exist_ok=True)
    return (str(chromedata_path), chrome_profile)


def clean_string(string: str) -> str:
    """
    Remove specific characters from a string.

    :param string: The string to clean.
    :type string: str
    :return: The cleaned string.
    :rtype: str
    """
    from re import sub

    return sub(r'[\\/*?:"<>|]', "", string)


def find_image_file(subdir: Path) -> Path:
    """
    Find the first image file in the subdirectory.

    Searches for files with extensions .png, .jpg, or .jpeg.

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
    """
    Read and return the stripped content of a file.

    :param file_path: The path to the file to read.
    :type file_path: Path
    :return: The stripped content of the file.
    :rtype: str
    """
    with file_path.open("r", encoding="utf-8") as f:
        content = f.read().strip()
        logger.debug("Read from %s: %s", file_path.name, content)
        return content


def pilling_image(image_path: str, trim_cm: float = 0.15) -> None:
    """
    Process an image by adjusting transparency and blending it with a white background.

    Steps performed:
    1. Opens the image and converts it to RGBA mode.
    2. Applies erosion and Gaussian blur to the alpha channel.
    3. Blends the image with a white background based on alpha values.
    4. Saves the modified image with '_pil' appended to the filename.

    :param image_path: The path to the PNG image file to be processed.
    :type image_path: str
    :param trim_cm: The trimming amount in centimeters. Default is 0.2 cm.
    :type trim_cm: float
    """
    import numpy as np
    from PIL import Image, ImageFilter

    dpi = 300
    erosion_pixels = int(trim_cm * dpi / 2.54)

    with Image.open(image_path).convert("RGBA") as img:
        alpha = img.split()[3]
        for _ in range(erosion_pixels):
            alpha = alpha.filter(ImageFilter.MinFilter(3))
        alpha = alpha.filter(ImageFilter.GaussianBlur(1))
        img.putalpha(alpha)

        arr = np.array(img).astype(np.float32)
        rgb, a = arr[..., :3], arr[..., 3]

        mask = np.clip((a - 64) / 128, 0, 1)[..., None]
        blended = rgb * mask + 255 * (1 - mask)

        final = np.dstack((blended, np.where(a > 64, 255, 0).astype(np.uint8))).astype(
            np.uint8
        )

        Image.fromarray(final, "RGBA").filter(ImageFilter.SMOOTH).filter(
            ImageFilter.SHARPEN
        ).save(image_path.replace(".png", "_pil.png"), dpi=(dpi, dpi))
