# src/zenodo_uploader/__init__.py

# This makes the 'upload' function available directly from the package,
# so users can do `from zenodo_uploader import upload`
# instead of the more verbose `from zenodo_uploader.cli import upload`.
# It defines the public API of your package.

from .cli import upload