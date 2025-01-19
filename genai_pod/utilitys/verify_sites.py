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

import logging
from pathlib import Path

from genai_pod.utils import save_cookies, start_chrome

logger = logging.getLogger(__name__)


def verify(profile_name: str, site: str) -> None:
    """Start a Chrome browser with specified settings and load a website.

    :param profile_name: The name of the Chrome profile to use.
    :type profile_name: str
    :param site: The URL of the website to load.
    :type site: str
    """
    driver = start_chrome(profile_name, None)
    driver.refresh()
    driver.get(site)

    input("Press ENTER when you are done with the browser and want to save cookies...")

    try:
        save_cookies(driver, Path("chromedata") / "cookies.json")
        logger.info("Cookies saved")
    except Exception as e:
        logger.exception("Failed to save cookies: %s", e)

    driver.quit()
