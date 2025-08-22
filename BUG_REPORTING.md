# Bug Reporting Guide

Thank you for taking the time to report a bug in the Python Documentation Generator. We value your feedback and contributions to improving this tool.

---

## Steps to Report a Bug

### 1. Search for Existing Issues
Before creating a new bug report, please check the [Issues](https://github.com/your-repo/python-docgen/issues) section of the repository to see if the bug has already been reported. If it has, you can add any additional information to the existing issue.

### 2. Create a New Bug Report
If the bug has not been reported, create a new issue on GitHub. Include the following details:

#### A. Summary
Provide a concise summary of the issue.

#### B. Environment Details
- Python version (e.g., Python 3.9.7).
- Operating system (e.g., Ubuntu 20.04, Windows 10).
- Terminal or IDE used (e.g., VS Code, PyCharm, Terminal).

#### C. Steps to Reproduce
List the steps to reproduce the issue, including:
1. The command you ran (e.g., `python3 docgen.py --path /path/to/code --format json`).
2. Any relevant input files or directory structure.

#### D. Expected Behavior
Describe what you expected to happen.

#### E. Actual Behavior
Describe what actually happened. Include error messages, logs, or screenshots if applicable.

#### F. Additional Context
Add any other relevant information, such as:
- Was the issue intermittent or consistent?
- Any recent changes to your environment or codebase.

---

## Example Bug Report

### Summary
The `--format json` flag outputs an empty JSON file even though the input contains valid Python code.

### Environment Details
- Python version: 3.9.7
- OS: macOS Monterey 12.0.1
- Terminal: iTerm2

### Steps to Reproduce
1. Clone the repository.
2. Create a test Python file (`test.py`) with the following content:
   ```python
   def sample_function():
       """This is a sample function."""
       pass
   ```
3. Run the command:
   ```bash
   python3 docgen.py --path test.py --format json
   ```

### Expected Behavior
The JSON output should include the `sample_function` with its name, docstring, and signature.

### Actual Behavior
The JSON output is an empty array (`[]`).

### Additional Context
This issue occurs consistently across multiple Python versions.

---

## Bug Triage Process
Once a bug is reported, the maintainers will:
1. Reproduce the issue using the provided steps.
2. Assign a priority level to the bug.
3. Investigate and resolve the issue, providing updates in the GitHub issue thread.

---

## Thank You
We appreciate your help in improving the Python Documentation Generator! If you have any questions or need assistance, feel free to reach out on the repository's Discussions page.