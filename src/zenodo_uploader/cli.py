# src/zenodo_uploader/cli.py (v2.2 - Final, Complete Code with 'configure' command)

import requests
import argparse
import json
import os
import sys
import toml
import logging
from tqdm import tqdm
from typing import List, Optional, Dict, Any

# =============================================================================
# 1. SETUP & CONFIGURATION
# =============================================================================

# --- Constants ---
ZENODO_URLS = {"production": "https://zenodo.org/api", "sandbox": "https://sandbox.zenodo.org/api"}
CONFIG_FILE_NAME = ".zenodo.toml"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stderr)
log = logging.getLogger(__name__)

# --- Helper Functions ---
def gb_to_bytes(gb: float) -> int:
    """Converts gigabytes to bytes."""
    return int(gb * 1024 * 1024 * 1024)

def load_config() -> Dict[str, Any]:
    """Loads configuration from a .zenodo.toml file in the current or home directory."""
    search_paths = [os.path.join(os.getcwd(), CONFIG_FILE_NAME), os.path.join(os.path.expanduser("~"), CONFIG_FILE_NAME)]
    for path in search_paths:
        if os.path.exists(path):
            log.info(f"--- Loading configuration from: {path} ---")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return toml.load(f)
            except Exception as e:
                log.warning(f"Warning: Could not parse config file at {path}. Error: {e}")
    return {}

def _get_api_base(sandbox: bool) -> str:
    """Gets the correct API base URL based on the sandbox flag."""
    return ZENODO_URLS["sandbox"] if sandbox else ZENODO_URLS["production"]

def _upload_file_with_progress(session: requests.Session, file_path: str, bucket_url: str):
    """Uploads a single file to a bucket URL with a progress bar."""
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    try:
        with open(file_path, 'rb') as fp:
            with tqdm.wrapattr(fp, "read", total=file_size, desc=f"   - Uploading {filename}", unit="B", unit_scale=True, unit_divisor=1024) as bar:
                r = session.put(f"{bucket_url}/{filename}", data=bar)
                r.raise_for_status()
    except (requests.exceptions.RequestException, IOError) as e:
        log.error(f"   ✗ ERROR: Failed to upload '{filename}'. Reason: {e.response.text if hasattr(e, 'response') and e.response else e}")
        sys.exit(1)

# =============================================================================
# 2. SUBCOMMAND HANDLERS
# =============================================================================

def handle_list(args: argparse.Namespace):
    """Handles the 'list' subcommand."""
    log.info("Executing 'list' command...")
    BASE_URL = _get_api_base(args.sandbox)
    headers = {"Authorization": f"Bearer {args.token}"}
    
    try:
        r = requests.get(f"{BASE_URL}/deposit/depositions", headers=headers)
        r.raise_for_status()
        depositions = r.json()
        
        if not depositions:
            log.info("No depositions found.")
            return

        log.info(f"Found {len(depositions)} depositions:")
        log.info("-" * 80)
        log.info(f"{'ID':<12} {'Status':<12} {'DOI':<25} {'Title'}")
        log.info("-" * 80)
        for dep in depositions:
            status = 'published' if dep['submitted'] else 'draft'
            title = dep.get('metadata', {}).get('title', 'No Title')
            doi = dep.get('doi', 'N/A')
            log.info(f"{dep['id']:<12} {status:<12} {doi:<25} {title[:60]}")
        log.info("-" * 80)

    except requests.exceptions.RequestException as e:
        log.error(f"✗ ERROR: Failed to list depositions. Reason: {e.response.text if e.response else e}")
        sys.exit(1)

def handle_update(args: argparse.Namespace):
    """Handles the 'update' subcommand."""
    log.info(f"Executing 'update' command for deposition ID: {args.deposition_id}...")
    BASE_URL = _get_api_base(args.sandbox)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {args.token}"})
    deposition_url = f"{BASE_URL}/deposit/depositions/{args.deposition_id}"

    try:
        log.info("   - Fetching deposition details...")
        r = session.get(deposition_url)
        r.raise_for_status()
        dep = r.json()

        if dep['submitted']:
            log.error("✗ ERROR: This deposition has already been published and cannot be modified.")
            sys.exit(1)
        
        bucket_url = dep['links']['bucket']

        if args.add_files:
            log.info(f"\n   - Adding {len(args.add_files)} new file(s)...")
            for file_path in args.add_files:
                if not os.path.exists(file_path):
                    log.error(f"   ✗ ERROR: File to add not found: '{file_path}'")
                    continue
                _upload_file_with_progress(session, file_path, bucket_url)
            log.info("   ✓ New files added successfully.")
        
        metadata_to_update = {k: v for k, v in vars(args).items() if k in ['title', 'description', 'author'] and v is not None}
        if metadata_to_update:
            log.info("\n   - Updating metadata...")
            current_metadata = dep.get('metadata', {})
            if 'title' in metadata_to_update: current_metadata['title'] = args.title
            if 'description' in metadata_to_update: current_metadata['description'] = args.description
            if 'author' in metadata_to_update: current_metadata['creators'] = [{'name': args.author}]
            
            data = {'metadata': current_metadata}
            r_meta = session.put(deposition_url, data=json.dumps(data), headers={"Content-Type": "application/json"})
            r_meta.raise_for_status()
            log.info("   ✓ Metadata updated successfully.")

        log.info(f"\n✅ Update complete. Review your draft at: {dep['links']['latest_draft_html']}")

    except requests.exceptions.RequestException as e:
        log.error(f"✗ ERROR: Update operation failed. Reason: {e.response.text if e.response else e}")
        sys.exit(1)

def handle_upload(args: argparse.Namespace):
    """Handles the 'upload' subcommand."""
    log.info("Executing 'upload' command...")
    BASE_URL = _get_api_base(args.sandbox)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {args.token}"})
    
    log.info("1. Creating new deposition record...")
    try:
        r = session.post(f'{BASE_URL}/deposit/depositions', json={})
        r.raise_for_status()
        dep = r.json()
        deposition_id = dep['id']
        bucket_url = dep['links']['bucket']
        draft_url = dep['links']['latest_draft_html']
        log.info(f"   ✓ Success! Deposition ID: {deposition_id}")
    except requests.exceptions.RequestException as e:
        log.error(f"   ✗ ERROR: Failed to create deposition. Reason: {e.response.text if e.response else e}")
        sys.exit(1)

    log.info(f"\n2. Starting upload of {len(args.file_paths)} files...")
    for file_path in args.file_paths:
        if not os.path.exists(file_path):
            log.error(f"   ✗ ERROR: File not found: '{file_path}'")
            sys.exit(1)
        _upload_file_with_progress(session, file_path, bucket_url)
    log.info("   ✓ All files uploaded successfully!")

    log.info("\n3. Adding metadata...")
    creator = {'name': args.author}
    if args.affiliation: creator['affiliation'] = args.affiliation
    metadata_payload = {'metadata': {
        'title': args.title, 'upload_type': args.upload_type, 'description': args.description,
        'creators': [creator], 'keywords': args.keywords or [], 'version': args.version or ''
    }}
    r_meta = session.put(f"{BASE_URL}/deposit/depositions/{deposition_id}", data=json.dumps(metadata_payload), headers={"Content-Type": "application/json"})
    r_meta.raise_for_status()
    log.info("   ✓ Metadata added successfully!")

    if not args.publish:
        log.info(f"\n✅ Upload complete. Review your draft at: {draft_url}")
    else:
        log.info("\n4. Publishing record...")
        try:
            r_publish = session.post(f"{BASE_URL}/deposit/depositions/{deposition_id}/actions/publish")
            r_publish.raise_for_status()
            final_data = r_publish.json()
            log.info("\n🎉 Published successfully! 🎉")
            log.info(f"   DOI: {final_data['doi']}")
            log.info(f"   View on Zenodo: {final_data['links']['record_html']}")
        except requests.exceptions.RequestException as e:
            log.error(f"   ✗ ERROR: Failed to publish. Reason: {e.response.text if e.response else e}")
            sys.exit(1)

def handle_configure(args: argparse.Namespace):
    """Handles the interactive configuration setup."""
    log.info("--- Interactive Configuration Setup ---")
    log.info("This will help you create a .zenodo.toml configuration file.")

    if args.local:
        config_path = os.path.join(os.getcwd(), CONFIG_FILE_NAME)
        log.info(f"Configuration will be saved locally in: {config_path}")
    else:
        config_path = os.path.join(os.path.expanduser("~"), CONFIG_FILE_NAME)
        log.info(f"Configuration will be saved globally in your home directory: {config_path}")

    existing_config = {}
    if os.path.exists(config_path):
        log.warning(f"\nWarning: Configuration file already exists at {config_path}.")
        with open(config_path, 'r') as f:
            existing_config = toml.load(f)
        overwrite = input("Do you want to overwrite it? (y/n): ").lower()
        if overwrite != 'y':
            log.info("Configuration cancelled.")
            return

    def get_current_value(path_keys):
        value = existing_config
        for key in path_keys:
            value = value.get(key, {})
        return value if isinstance(value, str) else ""

    log.info("\nPlease provide the following details. Press Enter to keep the current value.")
    
    prod_token_current = get_current_value(['tokens', 'production'])
    prod_token = input(f"Enter your Production Zenodo Token [{'*' * 10 if prod_token_current else 'empty'}]: ") or prod_token_current

    sandbox_token_current = get_current_value(['tokens', 'sandbox'])
    sandbox_token = input(f"Enter your Sandbox Zenodo Token [{'*' * 10 if sandbox_token_current else 'empty'}]: ") or sandbox_token_current
    
    author_current = get_current_value(['default', 'author'])
    author = input(f"Enter your default Author Name (e.g., Doe, John) [{author_current}]: ") or author_current

    affiliation_current = get_current_value(['default', 'affiliation'])
    affiliation = input(f"Enter your default Affiliation [{affiliation_current}]: ") or affiliation_current

    new_config = {
        'default': {'author': author, 'affiliation': affiliation},
        'tokens': {'production': prod_token, 'sandbox': sandbox_token}
    }
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            toml.dump(new_config, f)
        log.info(f"\n✓ Configuration successfully saved to {config_path}")
    except Exception as e:
        log.error(f"\n✗ ERROR: Failed to write configuration file. Reason: {e}")
        sys.exit(1)


# =============================================================================
# 4. MAIN CLI ENTRY POINT
# =============================================================================
def main():
    """Main function to parse arguments, select token, and route to subcommands."""
    config = load_config()
    default_config = config.get("default", {})
    tokens_config = config.get("tokens", {})

    parser = argparse.ArgumentParser(description="A tool to upload, update, and manage records on Zenodo.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose (DEBUG) logging.")
    
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--token", help="Your Zenodo access token. Overrides config file.")
    common_parser.add_argument("--sandbox", action='store_true', help="Use the Zenodo sandbox environment.")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Parser for the "configure" command ---
    parser_configure = subparsers.add_parser("configure", help="Create or update the .zenodo.toml configuration file interactively.")
    parser_configure.add_argument("--local", action="store_true", help="Create config file in the current directory.")
    parser_configure.set_defaults(func=handle_configure)

    # --- Parser for the "upload" command ---
    parser_upload = subparsers.add_parser("upload", help="Create a new record and upload files.", parents=[common_parser])
    parser_upload.add_argument("--file-paths", required=True, nargs='+', help="One or more paths to the files to upload.")
    parser_upload.add_argument("--title", required=True, help="Title of the upload.")
    parser_upload.add_argument("--author", default=default_config.get("author"), required=not default_config.get("author"), help="Primary author name.")
    parser_upload.add_argument("--description", required=True, help="A description of the upload content.")
    parser_upload.add_argument("--affiliation", default=default_config.get("affiliation"), help="Author's affiliation.")
    parser_upload.add_argument("--keywords", nargs='*', help="Keywords for the data.")
    parser_upload.add_argument("--version", help="Version number.")
    parser_upload.add_argument("--upload-type", default='dataset', help="The type of content.")
    parser_upload.add_argument("--publish", action='store_true', default=False, help="Publish the record immediately.")
    parser_upload.set_defaults(func=handle_upload)

    # --- Parser for the "update" command ---
    parser_update = subparsers.add_parser("update", help="Update an existing draft deposition.", parents=[common_parser])
    parser_update.add_argument("deposition_id", help="The ID of the Zenodo deposition to update.")
    parser_update.add_argument("--add-file", dest="add_files", nargs='+', help="Add one or more files.")
    parser_update.add_argument("--title", help="Update the title.")
    parser_update.add_argument("--description", help="Update the description.")
    parser_update.add_argument("--author", help="Update the author.")
    parser_update.set_defaults(func=handle_update)
    
    # --- Parser for the "list" command ---
    parser_list = subparsers.add_parser("list", help="List your existing depositions.", parents=[common_parser])
    parser_list.set_defaults(func=handle_list)

    args = parser.parse_args()
    
    if args.verbose:
        log.setLevel(logging.DEBUG)
    
    if args.command == 'configure':
        args.func(args)
        return

    token_to_use = args.token
    if not token_to_use:
        env = "sandbox" if args.sandbox else "production"
        token_to_use = tokens_config.get(env)

    if not token_to_use:
        parser.error(f"A Zenodo '{env}' token is required. Provide it via --token, set it in .zenodo.toml, or run 'zenodo-upload configure' to set it up.")

    args.token = token_to_use
    args.func(args)

if __name__ == "__main__":
    main()