# src/zenodo_uploader/__init__.py

# This makes the core functions available directly from the package,
# defining the public API of your package.
# Users can now do `from zenodo_uploader import upload, list_depositions, update_deposition`.

from .cli import upload, list_depositions, update_deposition