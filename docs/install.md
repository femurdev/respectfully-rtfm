Installation (editable install)

1. Download or clone the repository to your machine.

2. From the project root directory, install the package in editable mode using python3:

   python3 -m pip install -e .

3. Verify installation by running:

   python3 -c "import r2tfm; print(r2tfm.__version__)"

If you are using zsh and need to ensure the package source path is visible to Python (PYTHONPATH), locate the package path and export it:

1. Find the package directory path (editable installs point to the project source):

   python3 -c "import os, r2tfm; print(os.path.dirname(r2tfm.__file__))"

2. Export it in zsh (replace the printed path):

   export PYTHONPATH="/path/to/project:$PYTHONPATH"

Notes

- Use python3 explicitly for all commands above.
- Editable installs make development iterations easy (changes to source are reflected without reinstalling).