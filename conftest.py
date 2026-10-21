"""Present so pytest puts the repository root on sys.path.

Without a conftest.py at the root, pytest inserts the directory of each test file, so a
test under `tests/` cannot `import agent`. This file is the whole reason it can, and it
holds no fixtures.
"""
