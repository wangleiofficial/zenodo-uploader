# src/zenodo_uploader/cli.py

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
# 2. CORE LIBRARY FUNCTIONS
# =============================================================================

def list_depositions(token: str, sandbox: bool = False) -> List[Dict[str, Any]]:
    """Lists all depositions for a user. Returns the raw list of deposition dictionaries."""
    BASE_URL = _get_api_base(sandbox)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{BASE_URL}/deposit/depositions", headers=headers)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        log.error(f"✗ ERROR: Failed to list depositions. Reason: {e.response.text if e.response else e}")
        sys.exit(1)

def update_deposition(
    token: str, 
    deposition_id: int,
    metadata: Optional[Dict[str, Any]] = None,
    files_to_add: Optional[List[str]] = None,
    sandbox: bool = False
) -> Dict[str, Any]:
    """Updates an existing draft deposition. Returns the final deposition dictionary."""
    BASE_URL = _get_api_base(sandbox)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})
    deposition_url = f"{BASE_URL}/deposit/depositions/{deposition_id}"
    
    try:
        log.info(f"   - Fetching deposition {deposition_id} details...")
        r = session.get(deposition_url)
        r.raise_for_status()
        dep = r.json()

        if dep['submitted']:
            log.error("✗ ERROR: This deposition has already been published and cannot be modified.")
            sys.exit(1)
        
        bucket_url = dep['links']['bucket']

        if files_to_add:
            log.info(f"\n   - Adding {len(files_to_add)} new file(s)...")
            for file_path in files_to_add:
                if not os.path.exists(file_path):
                    log.error(f"   ✗ ERROR: File to add not found: '{file_path}'")
                    continue
                _upload_file_with_progress(session, file_path, bucket_url)
            log.info("   ✓ New files added successfully.")
        
        if metadata:
            log.info("\n   - Updating metadata...")
            current_metadata = dep.get('metadata', {})
            # Simple merge for top-level keys like 'title', 'description', etc.
            current_metadata.update(metadata)
            # Special handling for creators if 'author' is provided
            if 'author' in metadata:
                current_metadata['creators'] = [{'name': metadata['author']}]
            
            data = {'metadata': current_metadata}
            r_meta = session.put(deposition_url, data=json.dumps(data), headers={"Content-Type": "application/json"})
            r_meta.raise_for_status()
            log.info("   ✓ Metadata updated successfully.")

        # Fetch the final state
        r_final = session.get(deposition_url)
        r_final.raise_for_status()
        return r_final.json()

    except requests.exceptions.RequestException as e:
        log.error(f"✗ ERROR: Update operation failed. Reason: {e.response.text if e.response else e}")
        sys.exit(1)

def upload(token: str, file_paths: List[str], metadata: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Creates a new deposition and uploads files."""
    sandbox = kwargs.get('sandbox', False)
    publish = kwargs.get('publish', False)

    env = "sandbox" if sandbox else "production"
    BASE_URL = _get_api_base(sandbox)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    log.info(f"--- Using {env.upper()} environment ---")
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

    log.info(f"\n2. Starting upload of {len(file_paths)} files...")
    for file_path in file_paths:
        if not os.path.exists(file_path):
            log.error(f"   ✗ ERROR: File not found: '{file_path}'")
            sys.exit(1)
        _upload_file_with_progress(session, file_path, bucket_url)
    log.info("   ✓ All files uploaded successfully!")

    log.info("\n3. Adding metadata...")
    creator = {'name': metadata['author']}
    if metadata.get('affiliation'):
        creator['affiliation'] = metadata['affiliation']
    
    metadata_payload = {'metadata': {
        'title': metadata.get('title'), 'upload_type': metadata.get('upload_type', 'dataset'), 
        'description': metadata.get('description'), 'creators': [creator]
    }}
    if metadata.get('version'): metadata_payload['metadata']['version'] = metadata.get('version')
    if metadata.get('keywords'): metadata_payload['metadata']['keywords'] = metadata.get('keywords')

    r_meta = session.put(f"{BASE_URL}/deposit/depositions/{deposition_id}", data=json.dumps(metadata_payload), headers={"Content-Type": "application/json"})
    r_meta.raise_for_status()
    log.info("   ✓ Metadata added successfully!")

    final_data = r_meta.json()
    if not publish:
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
    
    return final_data

# =============================================================================
# 3. SUBCOMMAND HANDLERS
# =============================================================================

def handle_list(args: argparse.Namespace):
    """CLI handler for the 'list' subcommand."""
    log.info("Executing 'list' command...")
    depositions = list_depositions(token=args.token, sandbox=args.sandbox)
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

def handle_update(args: argparse.Namespace):
    """CLI handler for the 'update' subcommand."""
    log.info(f"Executing 'update' command for deposition ID: {args.deposition_id}...")
    metadata_to_update = {
        k: v for k, v in vars(args).items() 
        if k in ['title', 'description', 'author'] and v is not None
    }
    final_dep = update_deposition(
        token=args.token,
        deposition_id=args.deposition_id,
        files_to_add=args.add_files,
        metadata=metadata_to_update if metadata_to_update else None,
        sandbox=args.sandbox
    )
    log.info(f"\n✅ Update complete. Review your draft at: {final_dep['links']['latest_draft_html']}")

def handle_upload(args: argparse.Namespace):
    """CLI handler for the 'upload' subcommand."""
    log.info("Executing 'upload' command...")
    metadata = {
        'title': args.title, 'author': args.author, 'description': args.description,
        'affiliation': args.affiliation, 'keywords': args.keywords, 'version': args.version,
        'upload_type': args.upload_type
    }
    options = {'publish': args.publish, 'sandbox': args.sandbox}
    upload(token=args.token, file_paths=args.file_paths, metadata=metadata, **options)

def handle_configure(args: argparse.Namespace):
    """Handler for the interactive configuration setup."""
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

    parser_configure = subparsers.add_parser("configure", help="Create or update the .zenodo.toml configuration file interactively.")
    parser_configure.add_argument("--local", action="store_true", help="Create config file in the current directory.")
    parser_configure.set_defaults(func=handle_configure)

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

    parser_update = subparsers.add_parser("update", help="Update an existing draft deposition.", parents=[common_parser])
    parser_update.add_argument("deposition_id", help="The ID of the Zenodo deposition to update.")
    parser_update.add_argument("--add-file", dest="add_files", nargs='+', help="Add one or more files.")
    parser_update.add_argument("--title", help="Update the title.")
    parser_update.add_argument("--description", help="Update the description.")
    parser_update.add_argument("--author", help="Update the author.")
    parser_update.set_defaults(func=handle_update)
    
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