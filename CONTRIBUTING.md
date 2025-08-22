# Contributing to Python Documentation Generator

Thank you for considering contributing to the Python Documentation Generator! This guide outlines the process for contributing to the project, including setting up your environment, reporting issues, and submitting changes.

## How to Contribute

### 1. Reporting Issues
If you encounter a bug or have a feature request, follow these steps:
- Check the [Issues](https://github.com/your-repo/python-docgen/issues) section to see if it has already been reported.
- If not, create a new issue and include:
  - A clear description of the issue or feature request.
  - Steps to reproduce the issue (for bugs).
  - Any relevant logs or screenshots.

Refer to the [BUG_REPORTING.md](BUG_REPORTING.md) file for detailed instructions on reporting bugs.

### 2. Setting Up the Development Environment
To contribute code, set up your development environment:
1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/python-docgen.git
   cd python-docgen
   ```
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the tests to ensure the setup is correct:
   ```bash
   python3 -m unittest discover tests
   ```

### 3. Adding New Features
When adding a new feature:
- Discuss your idea by creating a new issue or commenting on an existing one.
- Follow the project coding standards (PEP 8 for Python).
- Write tests for your feature in the `tests/` directory.
- Update relevant documentation (e.g., `README.md`, `USAGE.md`, or `DEV_GUIDE.md`).

### 4. Submitting Changes
To submit your code changes:
1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes and commit them:
   ```bash
   git add .
   git commit -m "Add feature: your-feature-name"
   ```
3. Push your branch:
   ```bash
   git push origin feature/your-feature-name
   ```
4. Create a pull request (PR) on GitHub:
   - Provide a clear title and description for your PR.
   - Link to any related issues.

### 5. Code Review
- Your PR will be reviewed by maintainers.
- Address any feedback promptly.
- Once approved, your changes will be merged into the main branch.

## Coding Standards
- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code.
- Write clear and concise comments where necessary.
- Use meaningful variable and function names.
- Avoid adding unnecessary dependencies.

## Testing Guidelines
- Add tests for new features or bug fixes in the `tests/` directory.
- Use the `unittest` framework.
- Ensure all tests pass before submitting your PR:
  ```bash
  python3 -m unittest discover tests
  ```

## Documentation
- Update the `README.md`, `USAGE.md`, or `DEV_GUIDE.md` files as needed.
- Write clear and concise documentation for new features or changes.

## Thank You
We appreciate your interest in contributing to the Python Documentation Generator! Your contributions help make this project better for everyone.

Happy coding!