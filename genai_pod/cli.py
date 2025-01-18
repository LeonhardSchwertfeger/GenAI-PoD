# -*- coding: utf-8 -*-
# Copyright (C) 2024
# Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
# Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger
#

"""This module implements the command-line interface for the ShirtBusiness project.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
from cloup import (  # type: ignore[import]
    STRING,
    Choice,
    argument,
    group,
    option,
    pass_context,
    version_option,
)
from dotenv import load_dotenv, set_key

if TYPE_CHECKING:
    from cloup import Context

logger = logging.getLogger(__name__)


@group()
@version_option(message="%version%")
@pass_context
def cli(ctx: Context, **kwargs: Any) -> None:
    """Main entry point for the command-line application.

    This function initializes the context and logging settings.
    """
    ctx.ensure_object(dict)
    ctx.obj |= kwargs
    ctx.auto_envvar_prefix = "GENAI"

    logging.basicConfig(
        format="%(asctime)s %(levelname)8s | %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
        level=logging.INFO,
    )


@cli.group()
@option(
    "-o",
    "--output-directory",
    type=STRING,
    help="The directory to save the images and metadata to.",
    required=True,
)
@pass_context
def generate(ctx: Context, output_directory: str) -> None:
    """Group for generate commands."""
    ctx.obj["output_directory"] = output_directory


@generate.command()
@pass_context
def generategpt(ctx: Context, **kwargs: Any) -> None:
    """Use GPT to generate images via Selenium."""
    from genai_pod.generators.generate_gpt import (
        AbortScriptError,
        generate_image_selenium_gpt,
    )

    ctx.obj |= kwargs
    while True:
        try:
            generate_image_selenium_gpt(**ctx.obj)
        except AbortScriptError:
            continue


@cli.group()
@option(
    "--upload-path",
    type=STRING,
    help="The directory containing all subdirectories with images to upload.",
    required=True,
)
@pass_context
def upload(ctx: Context, **kwargs: Any) -> None:
    """Upload images to webshops."""
    ctx.obj |= kwargs


@upload.command()
@pass_context
def spreadshirt(ctx: Context, **kwargs: Any) -> None:
    """Upload an image to Spreadshirt."""
    from genai_pod.uploaders.spreadshirt import upload_spreadshirt

    ctx.obj |= kwargs
    upload_spreadshirt(**ctx.obj)


@upload.command()
@pass_context
def redbubble(ctx: Context, **kwargs: Any) -> None:
    """Upload an image to Redbubble."""
    from genai_pod.uploaders.redbubble import upload_redbubble

    ctx.obj |= kwargs
    upload_redbubble(**ctx.obj)


@cli.command()
@argument(
    "profile_name",
    type=Choice(["capsolver", "ChatGPT", "Spreadshirt"], case_sensitive=False),
    help="The name of the profile to verify.",
)
def verifysite(profile_name: str) -> None:
    """Verify an account in Chrome for capsolver, ChatGPT, or Spreadshirt/Redbubble."""
    from genai_pod.utilitys.verify_sites import verify

    profile_to_site = {
        "capsolver": "https://chromewebstore.google.com/detail/captcha-l%C3%B6ser-auto-hcaptc/"
        "hlifkpholllijblknnmbfagnkjneagid",
        "chatgpt": "https://chat.openai.com/",
        "spreadshirt": "https://www.spreadshirt.de/",
    }

    site = profile_to_site.get(profile_name.lower())
    if site is None:
        logger.error("Unknown profile name: %s", profile_name)
        sys.exit(1)

    try:
        verify(profile_name, site)
        logger.info("Browser successfully opened for %s at %s.", profile_name, site)
    except Exception as e:
        logger.exception("Exception while starting chrome %s", e)
        sys.exit(1)


@cli.command()
@click.option(
    "--path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    help=(
        "Path to the Tor binary. If not specified, "
        "an attempt is made to find Tor in the system PATH."
    ),
)
@click.pass_context
def setting_tor_binary(ctx, path: str):
    """
    Sets the path to the Tor binary and saves it in the .env file.
    """
    tor_exec = Path(path).resolve()

    if not tor_exec.is_file():
        ctx.fail(f"The specified Tor binary {str(tor_exec)} is not a file.")

    env_file = (Path(__file__).parent) / ".env"
    env_file.touch(exist_ok=True)
    load_dotenv(dotenv_path=env_file)

    tor_binary_path = str(tor_exec)
    set_key(str(env_file), "TOR_BINARY_PATH", tor_binary_path)
    logger.info("Saved Tor-Binary in .env: %s", tor_binary_path)


@cli.command()
def show_tor_path():
    """
    Shows the saved Tor binary path in the .env file.
    """
    import os

    env_file = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_file)
    tor_binary_path = os.getenv("TOR_BINARY_PATH")

    if tor_binary_path:
        logger.info("Current Tor-Binary Path: %s", tor_binary_path)
    else:
        logger.info(
            "Tor-Binary path not set. Please use the command "
            "'genai setting_tor_binary --path' to set one."
        )
