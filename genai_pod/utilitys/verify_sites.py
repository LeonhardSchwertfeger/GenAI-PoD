#!/usr/bin/env python3
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

logger = logging.getLogger(__name__)


def verify(profile_name: str, site: str) -> None:
    """Start a Chrome browser with specified settings and load a website.

    :param profile_name: The name of the Chrome profile to use.
    :type profile_name: str
    :param site: The URL of the website to load.
    :type site: str
    """
    from pathlib import Path

    from genai_pod.utils import load_cookies, save_cookies, start_chrome

    driver = start_chrome(profile_name, None)
    driver.get(site)

    # Now loading cookies after navigation
    cookies_path = Path("chromedata") / "cookies.json"
    if cookies_path.exists():
        load_cookies(driver, cookies_path)
        driver.refresh()

    input("Press ENTER when you are done with the browser and want to save cookies...")

    save_cookies(driver, cookies_path)
    logger.info("Cookies saved")
    driver.quit()
