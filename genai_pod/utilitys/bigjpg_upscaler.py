# -*- coding: utf-8 -*-
# Copyright (C) 2024
# Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
# Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger
#
"""This module provides functionality for automating the upscaling of images using the Bigjpg site.

Features:
- Automates browser interactions with Bigjpg using Selenium WebDriver.
- Configures the WebDriver to use the Tor network for anonymity.
- Handles common issues such as warnings, oversized images and retries during
  the upscaling process.
- Downloads and processes upscaled images, saving them to a specified directory.
- Monitors the progress of upscaling with a dynamic progress bar and manages
  errors such as stalled progress.

Logs provide detailed information about the process, aiding in debugging and monitoring.
"""

from __future__ import annotations

import logging
import subprocess  # noqa: S404
from base64 import b64decode
from io import BytesIO
from pathlib import Path
from shutil import which
from time import sleep, time
from typing import Any

from PIL import Image
from requests import RequestException, exceptions, get
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager  # type: ignore[import]


def start_tor() -> subprocess.Popen:
    """Start the Tor service by calling the Tor executable.

    :return: The process object representing the running Tor service.
    :rtype: subprocess.Popen
    """
    logging.info("Starting Tor service...")
    tor_executable = which("tor")
    if not tor_executable:
        raise FileNotFoundError("Tor executable not found in PATH.")
    return subprocess.Popen(  # noqa: S603
        [tor_executable],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def stop_tor(tor_process: subprocess.Popen) -> None:
    """Stop the Tor service by terminating the process.

    :param tor_process: The process object representing the Tor service.
    :type tor_process: subprocess.Popen
    :return: None
    :rtype: None
    """
    logging.info("Stopping Tor service...")
    tor_process.terminate()
    tor_process.wait()


def setup_driver() -> webdriver.Chrome:
    """Set up the Selenium WebDriver with Chrome and Tor proxy.

    Configures the WebDriver to use Tor for anonymity and positions
    the browser window on the appropriate screen.

    :return: The configured Selenium WebDriver instance.
    :rtype: webdriver.Chrome
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-search-engine-choice-screen")
    chrome_options.add_argument("--proxy-server=socks5://127.0.0.1:9050")
    chrome_options.add_argument("-lang=de-DE")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.page_load_strategy = "eager"

    chromedriver_path = Path(ChromeDriverManager().install())
    logging.info("chromedriver_path %s,", chromedriver_path)
    driver = webdriver.Chrome(
        service=Service(chromedriver_path),
        options=chrome_options,
    )
    driver.maximize_window()
    return driver


def _download_and_process_image(
    image_url: str,
    title: str,
    output_directory: Path,
) -> Path:
    """Download an image from a URL and save it to the output directory.

    Handles both data URLs and standard URLs.

    :param image_url: The URL of the image to download.
    :type image_url: str
    :param title: The title to use for the saved image file.
    :type title: str
    :param output_directory: The directory where the image will be saved.
    :type output_directory: Path
    :return: The path to the saved image file.
    :rtype: Path
    :raises Exception: If the image cannot be downloaded or processed.
    """
    try:
        if image_url.startswith("data:image"):
            image_data = b64decode(image_url.split(",", 1)[1])
        else:
            response = get(image_url, timeout=20)
            response.raise_for_status()
            image_data = response.content
        image = Image.open(BytesIO(image_data))
        raw_image = Path(output_directory) / f"{title}.png"
        image.save(raw_image)
        logging.info("Image saved successfully to %s", raw_image)
        return raw_image
    except (OSError, RequestException, ValueError) as e:
        logging.exception("Failed to download the image: %s", e)
        raise


def check_warning_modal(driver: webdriver.Chrome) -> str:
    """Check if any warning modals are present on the page.

    :param driver: The Selenium WebDriver instance.
    :type driver: webdriver.Chrome
    :return:
        - "warning" if a warning modal is present.
        - "image_too_big" if the image is too large.
        - "no_warning" if neither is present.
    :rtype: str
    """
    warning = next(
        iter(driver.find_elements(By.CSS_SELECTOR, "#modal_alert .modal-title")), None
    )
    if warning and warning.text == "Warnung":
        logging.warning("Warning modal detected!")
        return "warning"

    error = driver.find_elements(
        By.CSS_SELECTOR, 'div.pic_mask.danger[style="display: block;"]'
    )
    if error:
        logging.info("Image is too big!")
        return "image_too_big"

    return "no_warning"


def upload_image(driver: webdriver.Chrome, image_path: str) -> None:
    """Upload an image to the website using the provided WebDriver.

    :param driver: The Selenium WebDriver instance.
    :type driver: webdriver.Chrome
    :param image_path: The path to the image to upload.
    :type image_path: str
    :return: None
    :rtype: None
    """
    driver.execute_script(
        """
        const input = document.getElementById('fileupload');
        input.style.display = 'block';
    """,
    )
    driver.find_element(By.ID, "fileupload").send_keys(str(image_path))


def initiate_upscaling(driver: webdriver.Chrome) -> None:
    """Initiate the upscaling process on the website using JavaScript execution.

    Automates clicks on necessary UI elements to start upscaling.

    :param driver: The Selenium WebDriver instance.
    :type driver: webdriver.Chrome
    :return: None
    :rtype: None
    """
    driver.execute_script(
        """
        const checkStartButtonOrDownload = setInterval(() => {
            const startButton = document.querySelector(
                'button.btn.btn-sm.btn-primary.big_begin'
            );
            if (startButton && startButton.style.display !== 'none') {
                startButton.click();
                clearInterval(checkStartButtonOrDownload);

                const waitForModal = setInterval(() => {
                    const modal = document.getElementById('modal_big');
                    if (modal && modal.style.display === 'block') {
                        clearInterval(waitForModal);
                        document.querySelector('input[name="x2"][value="2"]').click();
                        document.querySelector('input[name="noise"][value="3"]').click();
                        setTimeout(() => {
                            document.getElementById('big_ok').click();
                        }, 2000);
                    }
                }, 100);
            }
        }, 1000);
    """,
    )


def monitor_progress(driver: webdriver.Chrome) -> str | None:
    """Monitor the progress of the upscaling process.

    Displays a progress bar and checks for any warnings during the process.

    :param driver: The Selenium WebDriver instance.
    :type driver: webdriver.Chrome
    :return:
        - "success" if the process completes successfully.
        - "warning" if a warning modal is detected.
        - "image_too_big" if the image is too large.
        - None if an unexpected issue occurs.
    :raises Exception: If the progress is stuck at 0% for over 1 minute.
    """
    zero_start = None
    below_start = None
    with tqdm(
        total=100,
        desc="Progress",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}",
        dynamic_ncols=True,
    ) as pbar:
        while True:
            width = driver.execute_script(
                'return document.querySelector(".progress-bar-primary")?.style.width;',
            )
            percent = int(width.strip("%")) if width else 0
            pbar.update(percent - pbar.n)

            if percent >= 100:
                logging.info("Upscaling was successful")
                return "success"

            if percent == 0:
                if zero_start is None:
                    zero_start = time()
                elif time() - zero_start >= 60:
                    raise Exception("Stuck for over 1min at 0%.")
            else:
                zero_start = None

            if percent < 100:
                if below_start is None:
                    below_start = time()
                elif time() - below_start >= 240:
                    raise Exception("Stuck for 4 minutes under 100%.")
            else:
                below_start = None

            status = check_warning_modal(driver)
            if status == "warning":
                return "warning"
            if status == "image_too_big":
                return "image_too_big"

            sleep(1)


def get_download_url(driver: webdriver.Chrome) -> Any:
    """Retrieve the download URL of the upscaled image.

    :param driver: The Selenium WebDriver instance.
    :type driver: webdriver.Chrome
    :return: The download URL if available, None otherwise.
    :rtype: str or None
    """
    return driver.execute_script(
        """
        const downloadLink = document.querySelector(
            'a.btn.btn-sm.btn-success.big_download'
        );
        return downloadLink ? downloadLink.href : null;
    """,
    )


def upscale_bigjpg(image_path: str, out_dir: Path) -> str | None:
    """Upscale an image using Bigjpg through Selenium automation.

    :param image_path: string path to the image
    :type image_path: str
    :param out_dir: destination output folder
    :type out_dir: Path
    :return: str | None
    """
    logging.info("*** Start upscaling ***")
    retry_limit = 3
    result = None

    for retry in range(retry_limit):
        driver = setup_driver()
        try:
            navigate_to_bigjpg(driver)
            if handle_initial_status(driver):
                return image_path

            sleep(10)
            upload_image(driver, image_path)

            if handle_post_upload_status(driver):
                return image_path

            initiate_upscaling(driver)
            logging.info("Initiated upscaling...")
            sleep(10)

            status = monitor_progress(driver)
            if status == "success":
                download_url = get_download_url(driver)
                if download_url:
                    result = str(
                        _download_and_process_image(
                            download_url, f"{Path(image_path).stem}_upscaled", out_dir
                        )
                    )
                    break
                logging.error("Download URL not found.")
            elif status == "warning":
                logging.info("Warning detected during progress, restarting...")
                raise Exception("Warning detected during progress.")
            elif status == "image_too_big":
                logging.info("Image is too big during progress. Aborting upscaling.")
                return image_path

        except RuntimeError:
            logging.exception("UpscaleError encountered")
        except Exception:
            logging.exception("Unexpected Error while upscaling")
        finally:
            driver.quit()

        if retry < retry_limit - 1:
            logging.info("Retrying...")
            sleep(5)

    if not result:
        logging.error("Retry limit reached. Exiting...")
        return image_path

    return result


def handle_initial_status(driver: webdriver.Chrome) -> bool:
    """Handle the initial status after navigating to Bigjpg.

    :param driver: The Selenium WebDriver instance.
    :type driver: webdriver.Chrome
    :return: bool
    """
    status_initial = check_warning_modal(driver)
    if status_initial == "image_too_big":
        logging.info("Image is too big. Aborting upscaling.")
        return True
    if status_initial == "warning":
        logging.info("Warning detected. Restarting the process.")
        raise Exception("Warning modal detected.")
    return False


def handle_post_upload_status(driver: webdriver.Chrome) -> bool:
    """Handle the status after uploading the image.

    :param driver: The Selenium WebDriver instance.
    :type driver: webdriver.Chrome
    :return: bool
    """
    status_after_upload = check_warning_modal(driver)
    if status_after_upload == "image_too_big":
        logging.info("Image is too big after upload. Aborting upscaling.")
        return True
    if status_after_upload == "warning":
        logging.info("Warning detected after upload. Restarting the process.")
        raise Exception("Warning modal detected after upload.")
    return False


def navigate_to_bigjpg(driver: webdriver.Chrome) -> None:
    """Navigate to the Bigjpg website.

    :param driver: The Selenium WebDriver instance.
    :type driver: webdriver.Chrome
    :raises TimeoutError: If bigjpg.com could'nt be loaded
    :return: None
    :rtype: None
    """
    try:
        driver.get("https://bigjpg.com")
        driver.set_page_load_timeout(30)
    except exceptions.Timeout as exc:
        raise TimeoutError(
            "The page couldn't be loaded within the expected time."
        ) from exc


def upscale(image_path: str, output_directory: Path) -> str | None:
    """Main function to upscale an image using the Bigjpg service.

    Starts the Tor service, handles retries and orchestrates the upscaling process.

    :param image_path: The path to the image to upscale.
    :type image_path: str
    :param output_directory: The directory where the upscaled image will be saved.
    :type output_directory: Path
    :return: The path to the upscaled image or the original image_path if aborted.
    """
    tor_process = None
    try:
        while True:
            tor_process = start_tor()
            sleep(20)
            result = upscale_bigjpg(str(image_path), output_directory)
            stop_tor(tor_process)
            tor_process = None

            if result and result != image_path:
                return result
            if result == image_path:
                logging.info(
                    "Upscaling aborted due to oversized image or repeated warnings."
                )
                return result

            logging.info("Restarting the whole process...")
    finally:
        if tor_process:
            stop_tor(tor_process)
