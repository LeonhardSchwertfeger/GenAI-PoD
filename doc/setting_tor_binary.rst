.. -*- coding: utf-8 -*-

.. _setting_tor_binary.rst:

Setting the Tor Binary Path
===========================

This is a guide on how to set and manage the Tor-Binary path for the ``genai`` CLI tool.


Overview
--------

The ``genai`` CLI allows users to specify the location of the Tor-Binary file to ensure compatibility
with their system setup. This can be done using the ``setting-tor-binary`` command. Once set, the path is saved in a ``.env`` file for future use.

Commands
--------

1. Setting the Tor-Binary Path
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~

   To specify the location of the Tor-Binary, use the following command:

   .. code-block:: bash

      genai setting-tor-binary --path "/path/to/tor"

   **Parameters**

   - ``--path``: The full path to the Tor binary file.

   **Expected Output**

   .. code-block:: text

      Saved Tor-Binary in .env: /path/to/tor

   **Error Handling**

   If the specified path is invalid or the file does not exist, you will see an error message:

   .. code-block:: text

      The specified Tor-Binary /path/to/tor is not a file.

2. Viewing the Current Tor Binary Path
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   To view the saved Tor-Binary path, use the ``show-tor-path`` command:

   .. code-block:: bash

      genai show-tor-path

   **Expected Output**

   If a Tor binary path is set, the command will display:

   .. code-block:: text

      Current Tor-Binary Path: /usr/bin/tor

   If no path is set, you will see:

   .. code-block:: text

      Tor-Binary path not set. Please use the command 'genai setting-tor-binary --path' to set one.

Notes for ARM64 Systems
-----------------------

It is recommended to download the Tor binary from the following SourceForge page for ARM64 system (e.g., Raspberry Pi):

`https://sourceforge.net/projects/tor-browser-ports/files/13.0.9/ <https://sourceforge.net/projects/tor-browser-ports/files/13.0.9/>`_

After downloading and installing the binary, use the ``setting-tor-binary`` command to specify the Tor-Binary location in the folder.
