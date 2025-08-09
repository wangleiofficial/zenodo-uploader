# Zenodo Command-Line Uploader

[![PyPI version](https://badge.fury.io/py/zenodo-cli-uploader-wanglei.svg)](https://badge.fury.io/py/zenodo-cli-uploader-wanglei)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zenodo-cli-uploader-wanglei)
[![CI/CD Status](https://github.com/your_username/zenodo-uploader/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/your_username/zenodo-uploader/actions/workflows/publish-to-pypi.yml)

A flexible tool to upload files to [Zenodo](https://zenodo.org), available as both a command-line utility and an importable Python library.

This tool supports pre-flight checks for file sizes, uploading multiple files, rich metadata, and an option to save as a draft for manual review before publishing. It can be easily integrated into automated workflows.

## Features

-   Upload multiple files to a single Zenodo record.
-   Set rich metadata including title, author, affiliation, and keywords.
-   Automatically filter out files that exceed a specific size limit.
-   Check total upload size against a limit before starting.
-   Option to upload to the Zenodo Sandbox for testing.
-   Option to save the upload as a draft instead of publishing immediately.
-   Usable as both a standalone CLI tool and a Python library.

## Installation

You can install the tool directly from PyPI:

```bash
pip install zenodo-uploader
```


## Getting a Zenodo Access Token

This tool requires a Personal Access Token to interact with your Zenodo account.

### 1. For the Main Zenodo Site (Production)

1.  Log in to [https://zenodo.org](https://zenodo.org).
2.  Navigate to your **Applications** settings by clicking your email in the top-right corner, then selecting "Applications", or go directly to: [https://zenodo.org/account/settings/applications/](https://zenodo.org/account/settings/applications/).
3.  Scroll down to the "Personal access tokens" section and click **"New token"**.
4.  Give the token a descriptive name (e.g., `my-cli-uploader`).
5.  In the **Scopes** list, you **must** select the following permissions:
    -   `deposit:write`: Allows creating new records and uploading files.
    -   `deposit:actions`: Allows publishing the records.
6.  Click the **"Create"** button.
7.  **Important:** Zenodo will show you the token **only once**. Copy it immediately and save it in a secure place.

### 2. For the Zenodo Sandbox (for Testing)

The process is identical, but you must perform it on the Sandbox website. Tokens from the main site and the sandbox are **not** interchangeable.

1.  Log in to [https://sandbox.zenodo.org](https://sandbox.zenodo.org).
2.  Go to the Sandbox Applications settings: [https://sandbox.zenodo.org/account/settings/applications/](https://sandbox.zenodo.org/account/settings/applications/).
3.  Follow steps 3-7 from the production guide above to create a **sandbox-specific** token.


## Usage
### As a Command-Line Tool
Here is an example of how to use the command to upload two files as a draft to the Zenodo sandbox.


```bash
zenodo-upload \
--token "YOUR_SANDBOX_TOKEN_HERE" \
--file-paths ./report.pdf ./dataset.zip \
--title "My Research Project Results" \
--author "Doe, John" \
--description "This record contains the final report and raw data for my research project." \
--affiliation "University of Science" \
--keywords "research" "data-analysis" "python" \
--version "v1.0" \
--sandbox
--no_publish
```
- Note: By default, the tool saves the upload as a draft. Use the --publish flag to publish immediately.

For a full list of all available options, run:

```bash
zenodo-upload --help
```
### As a Python Library
You can also import and use the core upload function directly in your Python scripts for automation.

```Python
from zenodo_uploader import upload
import os

# Create some dummy files for the example
os.makedirs("data", exist_ok=True)
with open("data/report.txt", "w") as f:
    f.write("This is a test report.")
with open("data/results.csv", "w") as f:
    f.write("col1,col2\n1,2")

# Your Zenodo sandbox token
MY_TOKEN = "PASTE_YOUR_SANDBOX_TOKEN_HERE"
MY_FILES = ["data/report.txt", "data/results.csv"]

try:
    # Call the upload function
    response_data = upload(
        token=MY_TOKEN,
        file_paths=MY_FILES,
        title="My Automated Dataset",
        author="Script, Python",
        description="This upload was performed programmatically using the library.",
        sandbox=True,          # Use the sandbox for testing
        no_publish=True,       # IMPORTANT: Leave as a draft by default
        affiliation="Automation University",
        keywords=["api", "python", "automation"],
        version="1.0.1"
    )
    print("\n--- Library Call Successful ---")
    print(f"Draft created with ID: {response_data.get('id')}")
    print(f"Review it here: {response_data.get('links', {}).get('latest_draft_html')}")

except SystemExit as e:
    # The upload function will call sys.exit(1) on a critical error.
    # You can catch this in your script to handle failures gracefully.
    print(f"\nUpload failed with exit code: {e.code}")
```

## License
This project is licensed under the MIT License.