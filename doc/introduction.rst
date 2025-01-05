.. -*- coding: utf-8 -*-
.. Copyright (C) 2024
.. Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
.. Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger

Introduction
============

Welcome to **GenAI** — your command-line tool that streamlines the process of generating and preparing images via **ChatGPT** automation. Designed with **print-on-demand (POD)** workflows in mind, GenAI can further handle background removal, upscaling, and uploading designs to popular shops like **Spreadshirt** and **Redbubble**.

.. note::
   This project is **unofficial** and not endorsed by OpenAI, Spreadshirt, Redbubble, or any related entities.
   Always check each platform’s Terms of Service before using automated tools.

Why GenAI?
----------

1. **Automated Image Generation**
   Enjoy hands-free image creation powered by ChatGPT in a real browser session (using Selenium). Generate art, patterns, or any conceptual designs with minimal effort.

2. **Background Removal**
   Automate your background-removal tasks on `remove.bg <https://www.remove.bg/>`_ via Selenium. No manual uploads or clicks required.

3. **Image Upscaling**
   Seamlessly upscale your images with `bigjpg.com <https://bigjpg.com/>`_. Perfect for achieving high-resolution outputs for merchandise.

4. **Automatic Uploads**
   Eliminate tedious uploading steps. GenAI directly interacts with your **Spreadshirt** or **Redbubble** account:
   - Navigates to upload pages
   - Fills out metadata like titles, descriptions, and tags
   - Publishes your design
   All via preconfigured Selenium routines.

5. **Account Verification**
   Tired of constantly logging in or losing sessions? GenAI streamlines session management, ensuring minimal friction when connecting to your web accounts.

Disclaimer
----------

By using GenAI, you acknowledge:

- **No Guarantees**: The software is provided “as is,” and the authors do not guarantee accuracy, reliability, or suitability for any specific purpose.
- **Platform Compliance**: Automated interactions may violate platform rules. Check each site’s policies and proceed responsibly.
- **User Responsibility**: You assume all liability for any outcome, including potential account suspensions, policy violations, or losses.

Features Overview
-----------------

- **Background Removal**: Automated background removal via Selenium on `remove.bg <https://www.remove.bg/>`_.
- **Image Upscaling**: Upscaling via Selenium on `bigjpg.com <https://bigjpg.com/>`_.
- **Automatic Upload**: Streamlined upload to:
  - `Spreadshirt <https://www.spreadshirt.de>`_
  - `Redbubble <https://www.redbubble.com>`_
- **AI Image Generation**: Direct `ChatGPT <https://chatgpt.com>`_ integration via automated browser sessions.
- **Account Verification**: Manage logins and sessions easily, reducing repeated sign-ins.
