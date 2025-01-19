# -*- coding: utf-8 -*-
# Copyright (C) 2024
# Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
# Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger
#

from unittest.mock import patch

from genai_pod.cli import cli


@patch("click.Path.convert", return_value="/path/to/tor-binary")
@patch("os.path.exists", return_value=True)
@patch("os.path.isdir", return_value=True)
@patch("genai_pod.generators.generate_gpt.generate_image_selenium_gpt")
def test_cli_generate_generategpt_success(
    mock_generate, mock_isdir, mock_exists, mock_path, runner
):
    mock_generate.side_effect = SystemExit(0)
    result = runner.invoke(
        cli,
        [
            "generate",
            "--output-directory",
            "/path/to/output",
            "generategpt",
            "--tor-binary-path",
            "/path/to/tor-binary",
        ],
    )
    assert result.exit_code == 0
    mock_generate.assert_called_once_with(
        output_directory="/path/to/output", tor_binary_path="/path/to/tor-binary"
    )


@patch("genai_pod.generators.generate_gpt.generate_image_selenium_gpt")
def test_cli_generate_generategpt_exception(mock_generate, runner):
    mock_generate.side_effect = Exception("Test Exception")
    result = runner.invoke(
        cli,
        [
            "generate",
            "--output-directory",
            "/path/to/output",
            "generategpt",
            "--tor-binary-path",
            "/path/to/tor-binary",
        ],
    )
    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)
    assert result.exception.code == 2


@patch("genai_pod.uploaders.spreadshirt.upload_spreadshirt")
def test_cli_upload_spreadshirt_success(mock_upload, runner):
    mock_upload.return_value = None
    result = runner.invoke(
        cli, ["upload", "--upload-path", "/path/to/uploads", "spreadshirt"]
    )
    assert result.exit_code == 0
    mock_upload.assert_called_once_with(upload_path="/path/to/uploads")


@patch("genai_pod.uploaders.redbubble.upload_redbubble")
def test_cli_upload_redbubble_success(mock_upload, runner):
    mock_upload.return_value = None
    result = runner.invoke(
        cli, ["upload", "--upload-path", "/path/to/uploads", "redbubble"]
    )
    assert result.exit_code == 0
    mock_upload.assert_called_once_with(upload_path="/path/to/uploads")


@patch("genai_pod.utilitys.verify_sites.verify")
def test_cli_verifysite_capsolver_success(mock_start_chrome, runner):
    mock_start_chrome.return_value = None
    result = runner.invoke(cli, ["verifysite", "capsolver"])
    assert result.exit_code == 0
    mock_start_chrome.assert_called_once_with(
        "capsolver",
        "https://chromewebstore.google.com/detail/captcha-l%C3%B6ser-auto-hcaptc/"
        "hlifkpholllijblknnmbfagnkjneagid",
    )


def test_cli_verifysite_unknown_profile(runner):
    result = runner.invoke(cli, ["verifysite", "unknownprofile"])
    assert result.exit_code == 2
    assert (
        "Invalid value for '{capsolver|ChatGPT|Spreadshirt}': 'unknownprofile'"
        in result.output
    )


def test_cli_missing_required_option_generate(runner):
    result = runner.invoke(cli, ["generate", "generategpt"])
    assert result.exit_code == 2
    assert (
        "Missing option '--output-directory'" in result.output
        or "Missing option '-o'" in result.output
    )


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Main entry point for the command-line application" in result.output


def test_cli_generate_help(runner):
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "Group for generate commands." in result.output


def test_cli_upload_help(runner):
    result = runner.invoke(cli, ["upload", "--help"])
    assert result.exit_code == 0
    assert "Upload images to webshops." in result.output
