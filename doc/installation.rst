.. -*- coding: utf-8 -*-
.. Copyright (C) 2024
.. Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
.. Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger

Installation
============

Prerequisites
-------------

- `Python <https://www.python.org />`_: Version 3.11 or higher.
- `ChatGPT Premium Account <https://openai.com/chatgpt/pricing/>`_: (Required for image generation through Selenium).
- `Chrome Browser <https://www.google.com/intl/en_en/chrome/>`_: Required for web automation tasks.
- `Chrome WebDriver <https://developer.chrome.com/docs/chromedriver/downloads?hl=en/>`_: Compatible with your installed Chrome version (used by Selenium).

Clone the Repository
--------------------

Create a Virtual Environment
----------------------------

.. code-block:: bash

   python3 -m venv venv
   source venv/bin/activate  # On Windows use .\venv\Scripts\activate

Install GenAI-PoD
-----------------

.. code-block:: bash

   pip install genai-pod
