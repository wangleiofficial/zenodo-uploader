# Zenodo Command-Line Uploader

[![PyPI version](https://badge.fury.io/py/zenodo-cli-uploader-wanglei.svg)](https://badge.fury.io/py/zenodo-cli-uploader-wanglei)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zenodo-cli-uploader-wanglei)
[![CI/CD Status](https://github.com/wangleiofficial/zenodo-uploader/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/wangleiofficial/zenodo-uploader/actions/workflows/publish-to-pypi.yml)

A flexible and powerful tool to upload files to [Zenodo](https://zenodo.org), available as both a command-line utility and an importable Python library.

This tool supports creating new depositions, updating existing drafts, listing records, and interactive configuration. It is designed for both manual use and integration into automated workflows.

## Features ✨

-   **Create new depositions** with multiple files.
-   **List** all your existing records (both drafts and published).
-   **Update** existing drafts by adding files or modifying metadata.
-   **Interactive setup command** (`configure`) to easily create your configuration file.
-   **Configuration file support** (`.zenodo.toml`) for persistent settings (tokens, author info).
-   **Progress bars** during file uploads for an improved user experience.
-   **Professional logging system** with a `--verbose` option for debugging.
-   Usable as both a standalone CLI tool and a Python library.

## Installation

You can install the tool directly from PyPI:

```bash
pip install zenodo-uploader
```

## Configuration (Recommended)

For the best experience, run the interactive setup command first. It will securely store your tokens and default information.

```bash
zenodo-upload configure
```
This will create a `.zenodo.toml` file in your home directory. The tool will automatically use the settings from this file.

Here is an example of the `.zenodo.toml` file structure:
```toml
[default]
author = "Your Name"
affiliation = "Your University"

[tokens]
production = "YOUR_PRODUCTION_TOKEN_HERE"
sandbox = "YOUR_SANDBOX_TOKEN_HERE"
```

## Getting a Zenodo Access Token

This tool requires a Personal Access Token to interact with your Zenodo account.

### 1. For the Main Zenodo Site (Production)

1.  Log in to [https://zenodo.org](https://zenodo.org).
2.  Navigate to your **Applications** settings: [https://zenodo.org/account/settings/applications/](https://zenodo.org/account/settings/applications/).
3.  Click **"New token"**.
4.  Give the token a name and select the **`deposit:write`** and **`deposit:actions`** scopes.
5.  Click **"Create"** and copy the token immediately.

### 2. For the Zenodo Sandbox (for Testing)

The process is identical on the Sandbox website: [https://sandbox.zenodo.org/account/settings/applications/](https://sandbox.zenodo.org/account/settings/applications/). Sandbox and production tokens are not interchangeable.

## Command-Line Usage

The tool now uses subcommands: `configure`, `list`, `upload`, and `update`.

### `configure`: Interactive Setup
Creates the `.zenodo.toml` configuration file for you.

```bash
# Run the interactive setup wizard
zenodo-upload configure

# Create the config file in the current directory instead of the home directory
zenodo-upload configure --local
```

### `list`: Listing Your Records
Lists all depositions (drafts and published) in your account.

```bash
# List records from the production site
zenodo-upload list

# List records from the sandbox environment
zenodo-upload list --sandbox
```

### `upload`: Creating a New Record
Creates a new deposition and uploads files. By default, it creates a draft. Use `--publish` to publish immediately.

```bash
# Create a new draft on the sandbox using values from your config file
zenodo-upload upload \
--file-paths ./report.pdf ./dataset.zip \
--title "My Research Project Results" \
--description "This record contains the final report and raw data." \
--sandbox

# Create and immediately publish a record on the production site
zenodo-upload upload \
--file-paths ./final_paper.pdf \
--title "Final Published Paper" \
--description "Official version of the paper." \
--publish
```

### `update`: Modifying a Draft
Updates an existing draft deposition by adding files or changing metadata. This command cannot be used on already-published records.

```bash
# Add a new file to an existing draft in the sandbox
zenodo-upload update 1234567 --add-file ./new_figure.png --sandbox

# Update the title of an existing draft
zenodo-upload update 1234567 --title "A Better Title for My Project"
```

For a full list of options for any subcommand, use `--help`, for example:
```bash
zenodo-upload upload --help
```

## As a Python Library

You can import and use the core `upload` function for creating new depositions programmatically.

```python
from zenodo_uploader import upload
import os

# Create dummy files for the example
os.makedirs("data", exist_ok=True)
with open("data/report.txt", "w") as f:
    f.write("This is a test report.")

# Your Zenodo sandbox token (can also be loaded from a config file)
MY_TOKEN = "PASTE_YOUR_SANDBOX_TOKEN_HERE"
MY_FILES = ["data/report.txt"]

metadata = {
    "title": "My Automated Dataset",
    "author": "Script, Python",
    "description": "This upload was performed programmatically.",
    "affiliation": "Automation University",
    "keywords": ["api", "python", "automation"],
    "version": "1.0.1",
    "upload_type": "dataset"
}

try:
    response_data = upload(
        token=MY_TOKEN,
        file_paths=MY_FILES,
        metadata=metadata,
        sandbox=True,
        publish=False  # Creates a draft
    )
    print("\n--- Library Call Successful ---")
    print(f"Draft created with ID: {response_data.get('id')}")
    print(f"Review it here: {response_data.get('links', {}).get('latest_draft_html')}")

except SystemExit as e:
    print(f"\nUpload failed with exit code: {e.code}")

```

## License

This project is licensed under the MIT License.