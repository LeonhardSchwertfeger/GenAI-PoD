.. -*- coding: utf-8 -*-
.. Copyright (C) 2024
.. Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
.. Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger

.. _command-line-interface:

Command-line Interface
----------------------

The GenAI tool provides a command-line interface to generate AI images and automate uploads to various web shops like Spreadshirt and Redbubble. It performs tasks such as account verification, image generation, and uploading in the background.

The general pattern for using the GenAI CLI is:

``genai [OPTIONS] COMMAND``

All functionalities of the GenAI tool can be accessed using this interface. See examples below.


Commands
--------

- **verifysite**: Verify account in Chrome for specific websites (e.g., ChatGPT, Spreadshirt).

  .. code-block:: bash

     genai verifysite SITE

  Options for ``SITE``:

  - ``capsolver``: Profile to add CAPTCHA Solver extension to Chrome browser.
  - ``ChatGPT``: Profile to log in to chat.openai.com.
  - ``Spreadshirt``: Profile to log in to Spreadshirt or Redbubble.

- **generate**: Generate and save AI-generated images to disk.

  .. code-block:: bash

     genai generate [OPTIONS] SUBCOMMAND

  Options for ``generate``:

  - ``-o``, ``--output-directory TEXT``: The directory to save the images and metadata to (required).

  Subcommands:

  - ``generategpt``: Generate images using GPT through Selenium.

.. image:: ../assets/generating.gif
   :alt: generating GIF
   :width: 900px
   :align: center

- **upload**: Upload images to web shops.

  .. code-block:: bash

     genai upload [OPTIONS] SUBCOMMAND

  Options for ``upload``:

  - ``--upload-path TEXT``: The directory containing sub-directories with images to upload (required).

  Subcommands:

  - ``spreadshirt``: Upload images to Spreadshirt.
  - ``redbubble``: Upload images to Redbubble.


.. image:: ../assets/Explanation.png
   :alt: Explanation
   :width: 900px
   :align: center


**Command-line Interface Examples**

.. code-block:: bash
    :linenos:
    :caption: Command-line Interface Examples

    # Verify ChatGPT account
    genai verifysite ChatGPT

    # Verify Spreadshirt or Redbubble account
    genai verifysite Spreadshirt

    # Generate images using GPT via web automation
    genai generate --output-directory ./images generategpt

    # Upload images to Spreadshirt
    genai upload --upload-path ./images spreadshirt

    # Upload images to Redbubble
    genai upload --upload-path ./images redbubble

    # Display help information
    genai --help

**Detailed Command Usage**

Below is the detailed usage of each command and its options.

.. click:: genai.cli:cli
   :prog: genai
   :nested: full
