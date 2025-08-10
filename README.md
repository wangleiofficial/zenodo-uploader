# Zenodo Command-Line Uploader

[![PyPI version](https://badge.fury.io/py/zenodo-uploader.svg)](https://badge.fury.io/py/zenodo-cli-uploader-wanglei)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zenodo-uploader)
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
```

### `list`: Listing Your Records
Lists all depositions (drafts and published) in your account.

```bash
# List records from the sandbox environment
zenodo-upload list --sandbox
```

### `upload`: Creating a New Record
Creates a new deposition and uploads files. By default, it creates a draft.

```bash
# Create a new draft on the sandbox using values from your config file
zenodo-upload upload \
--file-paths ./report.pdf ./dataset.zip \
--title "My Research Project Results" \
--description "This record contains the final report and raw data." \
--sandbox
```

### `update`: Modifying a Draft
Updates an existing draft deposition.

```bash
# Add a new file to an existing draft in the sandbox
zenodo-upload update 1234567 --add-file ./new_figure.png --sandbox
```

For a full list of options for any subcommand, use `--help`, for example: `zenodo-upload upload --help`.

## As a Python Library

You can import and use the core functions directly in your Python scripts. The package exposes `upload`, `list_depositions`, and `update_deposition`.

### Example 1: Creating a New Upload

```python
from zenodo_uploader import upload

MY_TOKEN = "PASTE_YOUR_SANDBOX_TOKEN_HERE"

metadata = {
    "title": "My Automated Dataset",
    "author": "Script, Python",
    "description": "This upload was performed programmatically.",
}

# This creates a new draft in the sandbox
response_data = upload(
    token=MY_TOKEN,
    file_paths=["./data/report.txt"],
    metadata=metadata,
    sandbox=True,
    publish=False
)
print(f"Draft created: {response_data.get('links', {}).get('latest_draft_html')}")
```

### Example 2: Listing and Updating a Draft

```python
from zenodo_uploader import list_depositions, update_deposition

TOKEN = "YOUR_SANDBOX_TOKEN_HERE"

# First, list depositions to find a draft
print("--- Listing depositions ---")
all_deps = list_depositions(token=TOKEN, sandbox=True)
drafts = [d for d in all_deps if not d['submitted']]

if not drafts:
    print("No drafts found to update.")
else:
    draft_id = drafts[0]['id']
    print(f"\n--- Found draft with ID {draft_id}. Updating it... ---")
    
    # Create a new file to add
    with open("update_log.txt", "w") as f:
        f.write("This file was added during an update.")
        
    # Call the update function to add the file and change the description
    updated_dep = update_deposition(
        token=TOKEN,
        deposition_id=draft_id,
        files_to_add=["update_log.txt"],
        metadata={"description": "Description updated programmatically."},
        sandbox=True
    )
    print("\n--- Update Successful ---")
    print(f"Review the updated draft at: {updated_dep.get('links', {}).get('latest_draft_html')}")
```

## License
This project is licensed under the MIT License.

