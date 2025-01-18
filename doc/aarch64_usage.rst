.. -*- coding: utf-8 -*-

.. _aarch64-usage:

Using ``undetected-chromedriver`` on ARM64 Systems (e.g., Raspberry Pi)
=======================================================================

This guide explains how to set up ``undetected-chromedriver`` on ARM64 systems like a Raspberry Pi.
The default setup of ``undetected-chromedriver`` assumes an x86_64 architecture and will fail on ARM systems with the error
``OSError: [Errno 8] Exec format error``.

This guide includes:

1. Checking your system architecture.
2. Installing the ARM-compatible ``chromium-driver``.
3. Copying the driver to a user-writable location.
4. Specifying the correct ``driver_executable_path`` in your Python code.

---

1. Check System Architecture
----------------------------

Before proceeding, confirm your system architecture by running:

.. code-block:: bash

   uname -m

- If you see ``aarch64``, your system uses the ARM64 architecture.
- If it is ``x86_64``, this guide does not apply.

2. Install ``chromium-driver`` for ARM64
----------------------------------------

Install the Chromium driver package using the system's package manager:

.. code-block:: bash

   sudo apt update
   sudo apt install chromium-driver

After installation, verify the installation path:

.. code-block:: bash

   which chromedriver

The path is typically ``/usr/bin/chromedriver``.

3. Copy ``chromedriver`` to a Writable Location
-----------------------------------------------

``undetected-chromedriver`` requires a writable copy of the ``chromedriver`` file.
Copy the driver to a local directory:

.. code-block:: bash

   cp /usr/bin/chromedriver /home/<your-username>/.local/share/undetected_chromedriver/chromedriver_copy

Replace ``<your-username>`` with your actual username.

### Verify Architecture of the Driver

Run the following command to ensure the copied driver is compatible with ARM64:

.. code-block:: bash

   file /home/<your-username>/.local/share/undetected_chromedriver/chromedriver_copy

The output should include ``ARM aarch64``.

4. set path in env
------------------
FIXME: Here should be a tutorial about the cli and how the cli will automatically
make saves the path for the undetected_chromedriver
