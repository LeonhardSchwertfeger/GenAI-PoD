#!/usr/bin/env python3
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
from typing import TYPE_CHECKING, Any

import click
from cloup import STRING, Choice, argument, group, option, pass_context

if TYPE_CHECKING:
    from cloup import Context

logger = logging.getLogger(__name__)


def print_version(
    ctx: Context,
    param: Any,  # pylint: disable=unused-argument
    value: Any,  # noqa: ANN401, ARG001
) -> None:
    """Prints the version of the package"""
    if not value or ctx.resilient_parsing:
        return
    from importlib.metadata import (  # noqa: PLC0415 # pylint: disable=import-outside-toplevel
        version,
    )

    click.echo(version("genai_pod"))
    ctx.exit()


@group()
@option(
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
)
@option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging (debug level)",
)
@pass_context
def cli(ctx: Context, **kwargs: Any) -> None:
    """Main entry point for the command-line application.

    This function initializes the context and logging settings.
    """
    ctx.ensure_object(dict)
    ctx.obj |= kwargs
    ctx.auto_envvar_prefix = "GENAI"

    log_level = logging.DEBUG if kwargs.get("verbose") else logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)8s | %(name)s | %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
        level=log_level,
    )
    logging.getLogger("selenium").setLevel(logging.WARNING)  # reduzing Selenium-Logs
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # reduzing HTTP-Libs
    logger.debug("CLI initialisiert mit Log-Level: %s", logging.getLevelName(log_level))


@cli.group()
@option(
    "-o",
    "--output-directory",
    type=STRING,
    help="The directory to save the images and metadata to.",
    required=True,
)
@option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging (debug level)",
)
@pass_context
def generate(ctx: Context, output_directory: str, verbose: bool) -> None:
    """Group for generate commands."""
    ctx.obj["output_directory"] = output_directory
    ctx.obj["verbose"] = verbose


@generate.command()
@option(
    "--tor-binary-path",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    help="Path to the Tor binary.",
    required=False,
)
@option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging (debug level)",
)
@pass_context
def generategpt(ctx: Context, tor_binary_path: str | click.Path, verbose: bool) -> None:
    """Use GPT to generate images via Selenium."""
    from genai_pod.generators.generate_gpt import (
        AbortScriptError,
        generate_image_selenium_gpt,
    )

    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.debug("Verbose mode is enabled.")

    ctx.obj |= {"tor_binary_path": tor_binary_path}
    while True:
        try:
            params = {
                key: ctx.obj[key]
                for key in ctx.obj
                if key in {"tor_binary_path", "output_directory"}
            }
            generate_image_selenium_gpt(**params)
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

    # Filter out debug parameters
    params = {k: v for k, v in ctx.obj.items() if k not in {"verbose"}}
    params |= kwargs
    upload_spreadshirt(**params)


@upload.command()
@pass_context
def redbubble(ctx: Context, **kwargs: Any) -> None:
    """Upload an image to Redbubble."""
    from genai_pod.uploaders.redbubble import upload_redbubble

    params = {k: v for k, v in ctx.obj.items() if k not in {"verbose"}}
    params |= kwargs
    upload_redbubble(**params)


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
