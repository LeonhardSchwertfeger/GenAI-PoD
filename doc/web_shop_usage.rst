.. -*- coding: utf-8 -*-
.. Copyright (C) 2024
.. Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
.. Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger

Detailed Web Shop Usage Guide
=============================

Spreadshirt Usage
-----------------

1. **Verify Account**

   Start by verifying your Spreadshirt account using the command:

   .. code-block:: bash

      genai verifysite Spreadshirt

   This will open a Chrome window for you to log in. Once done, type ``DONE`` in the console to save the session.

2. **Using Product Templates**

   - Create a product template directly on Spreadshirt if needed. The tool will automatically use the most recently created template for uploads.
   - The template **must contain** at least **50 products**.

3. **Organizing Uploaded Files**

   - Successfully uploaded designs are moved to the ``used_spreadshirt`` folder.
   - Any designs with upload errors are moved to the ``error_spreadshirt`` folder for review.


.. image:: ../assets/upload.gif
   :alt: Example GIF
   :width: 900px
   :align: center


Redbubble Usage
---------------

1. **Verify Account**

   - Start by verifying your Redbubble account with the following command:

     .. code-block:: bash

        genai verifysite Spreadshirt

   - Alternatively, for first-time use, initiate the upload command, which will prompt for a login:

     .. code-block:: bash

        genai upload --upload-path "./images" redbubble

   Once logged in, your session credentials are saved for future uploads.

2. **Redbubble Account Settings**

   - Your Redbubble account must be set to ``English`` as the display language and use ``$ United States Dollar (USD)`` as the currency.
     These can be adjusted in your Redbubble account settings at the bottom of the webpage.
