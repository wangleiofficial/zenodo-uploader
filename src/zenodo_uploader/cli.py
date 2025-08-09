# src/zenodo_uploader/cli.py

import requests
import argparse
import json
import os
import sys
from typing import List, Optional, Dict, Any

# --- Configuration ---
ZENODO_URLS = {
    "production": "https://zenodo.org/api",
    "sandbox": "https://sandbox.zenodo.org/api"
}

def gb_to_bytes(gb: float) -> int:
    """Converts gigabytes to bytes."""
    return int(gb * 1024 * 1024 * 1024)

# =============================================================================
# 1. CORE REUSABLE FUNCTION (THE LIBRARY API)
# =============================================================================

def upload(
    token: str,
    file_paths: List[str],
    title: str,
    author: str,
    description: str,
    affiliation: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    version: Optional[str] = None,
    upload_type: str = 'dataset',
    max_file_size_gb: float = 50.0,
    total_size_limit_gb: float = 50.0,
    no_publish: bool = True,
    sandbox: bool = False
) -> Dict[str, Any]:
    """
    Core function to upload files to Zenodo. Designed to be imported and used in other Python scripts.

    Args:
        token: Your personal access token from Zenodo.
        file_paths: A list of local file paths to upload.
        title: Title of the upload.
        author: Primary author name (e.g., 'Doe, John').
        description: A description of the upload content.
        affiliation: Optional author's institutional affiliation.
        keywords: Optional list of keywords.
        version: Optional version number for the data or software.
        upload_type: Type of content ('dataset', 'software', etc.).
        max_file_size_gb: Max size for a single file. Files larger than this are skipped.
        total_size_limit_gb: Max total size for all files.
        no_publish: If True, saves the record as a draft. If False, publishes it.
        sandbox: If True, uses the Zenodo sandbox environment.

    Returns:
        A dictionary containing the final deposition data from Zenodo.

    Raises:
        SystemExit: If a critical error occurs (e.g., failed request, file not found),
                    it prints an error and exits, making it suitable for command-line usage.
                    When used as a library, these can be caught with a try/except block.
    """
    env = "sandbox" if sandbox else "production"
    BASE_URL = ZENODO_URLS[env]
    print(f"--- Using {env.upper()} environment ---")

    # --- Step 0: Pre-flight checks and file filtering ---
    # ... (This logic remains the same as before) ...
    print("0. Checking file sizes and total capacity...")
    valid_files_to_upload = []
    total_size_bytes = 0
    max_file_size_bytes = gb_to_bytes(max_file_size_gb)
    total_size_limit_bytes = gb_to_bytes(total_size_limit_gb)
    for file_path in file_paths:
        if not os.path.exists(file_path):
            print(f"   ✗ ERROR: File not found: '{file_path}'")
            sys.exit(1)
        file_size = os.path.getsize(file_path)
        if file_size > max_file_size_bytes:
            print(f"   ! WARNING: File '{os.path.basename(file_path)}' exceeds size limit. Skipping.")
            continue
        valid_files_to_upload.append(file_path)
        total_size_bytes += file_size
    if total_size_bytes > total_size_limit_bytes:
        print(f"   ✗ ERROR: Total file size exceeds the limit.")
        sys.exit(1)
    if not valid_files_to_upload:
        print("   ! WARNING: No valid files to upload.")
        return {}
    
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    
    # --- Step 1: Create a new Deposition ---
    print("\n1. Creating new deposition record...")
    try:
        r = requests.post(f'{BASE_URL}/deposit/depositions', headers=headers, json={})
        r.raise_for_status()
        deposition_data = r.json()
        deposition_id = deposition_data['id']
        bucket_url = deposition_data['links']['bucket']
        draft_url = deposition_data['links']['latest_draft_html']
        print(f"   ✓ Success! Deposition ID: {deposition_id}")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ ERROR: Failed to create deposition. Reason: {e.response.text if e.response else e}")
        sys.exit(1)

    # --- Step 2: Upload files ---
    # ... (This logic remains the same as before) ...
    print(f"\n2. Starting upload of {len(valid_files_to_upload)} files...")
    for file_path in valid_files_to_upload:
        filename = os.path.basename(file_path)
        print(f"   - Uploading: {filename}...")
        with open(file_path, 'rb') as fp:
            requests.put(f"{bucket_url}/{filename}", data=fp, headers={"Authorization": f"Bearer {token}"}).raise_for_status()
    print("   ✓ All files uploaded successfully!")

    # --- Step 3: Add metadata ---
    print("\n3. Adding metadata...")
    creator = {'name': author}
    if affiliation:
        creator['affiliation'] = affiliation
    
    metadata_payload = {'metadata': {
        'title': title, 'upload_type': upload_type, 'description': description, 'creators': [creator]
    }}
    if version: metadata_payload['metadata']['version'] = version
    if keywords: metadata_payload['metadata']['keywords'] = keywords
        
    r = requests.put(f'{BASE_URL}/deposit/depositions/{deposition_id}', data=json.dumps(metadata_payload), headers=headers)
    r.raise_for_status()
    print("   ✓ Metadata added successfully!")

    # --- Step 4: Publish or leave as draft ---
    final_data = None
    if no_publish:
        print("\n✅ Upload complete. Record has been saved as a draft.")
        print(f"   Review and publish manually at: {draft_url}")
        final_data = r.json() # Return the latest draft data
    else:
        print("\n4. Publishing record...")
        r = requests.post(f'{BASE_URL}/deposit/depositions/{deposition_id}/actions/publish', headers=headers)
        r.raise_for_status()
        final_data = r.json()
        print("\n🎉 Published successfully! 🎉")
        print(f"   DOI: {final_data['doi']}")
        print(f"   View on Zenodo: {final_data['links']['record_html']}")
        
    return final_data


# =============================================================================
# 2. COMMAND-LINE INTERFACE (CLI) WRAPPER
# =============================================================================

def main():
    """
    Main function to parse command-line arguments.
    This function acts as a wrapper around the core 'upload' function.
    """
    parser = argparse.ArgumentParser(
        description="A tool to upload files to Zenodo from the command line."
    )
    
    # Define all arguments, same as before
    parser.add_argument("--token", required=True, help="Your personal access token from Zenodo.")
    parser.add_argument("--file-paths", required=True, nargs='+', help="Paths to the files to upload.")
    parser.add_argument("--title", required=True, help="Title of the upload.")
    parser.add_argument("--author", required=True, help="Primary author name (e.g., 'Doe, John').")
    parser.add_argument("--description", required=True, help="A description of the upload content.")
    parser.add_argument("--affiliation", help="The author's institutional affiliation.")
    parser.add_argument("--keywords", nargs='*', help="Keywords to describe the data.")
    parser.add_argument("--version", help="Version number for the data or software.")
    parser.add_argument("--upload-type", default='dataset', help="The type of content being uploaded.")
    parser.add_argument("--max-file-size", type=float, default=50.0, help="Max size for a single file in GB.")
    parser.add_argument("--total-size-limit", type=float, default=50.0, help="Max total size for all files in GB.")
    parser.add_argument("--publish", action='store_true', help="Publish the record immediately instead of saving as a draft.")
    parser.add_argument("--sandbox", action='store_true', help="Use the Zenodo sandbox environment for testing.")

    args = parser.parse_args()
    
    # Call the core 'upload' function with the parsed arguments.
    # Note that the CLI argument is --publish, while the function expects no_publish.
    # We invert the boolean logic here.
    try:
        upload(
            token=args.token,
            file_paths=args.file_paths,
            title=args.title,
            author=args.author,
            description=args.description,
            affiliation=args.affiliation,
            keywords=args.keywords,
            version=args.version,
            upload_type=args.upload_type,
            max_file_size_gb=args.max_file_size,
            total_size_limit_gb=args.total_size_limit,
            no_publish=(not args.publish), # Invert logic for the function call
            sandbox=args.sandbox
        )
    except SystemExit as e:
        # The upload function calls sys.exit(1) on failure. We catch it here
        # to ensure the script terminates with the correct status code.
        sys.exit(e.code)


if __name__ == "__main__":
    main()