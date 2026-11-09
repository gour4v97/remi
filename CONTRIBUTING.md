# Contributing to Remi

Thank you for your interest in contributing to **Remi**! We welcome bug reports, feature suggestions, documentation improvements, and code contributions.

---

## Code of Conduct

Please review and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/gour4v97/remi.git
   cd remi
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install in editable mode with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Run the test suite:
   ```bash
   pytest
   # Or without pytest installed:
   python -m unittest discover -s tests -p "test_*.py"
   ```

---

## Coding Standards

- **Formatting & Linting:** Code should follow modern Python 3.11+ conventions. Run `ruff format` and `ruff check`.
- **Type Annotations:** Use Python type hints throughout all new modules.
- **Documentation:** Include clear docstrings for all public classes, functions, and registry extensions.
- **Cross-Platform Safety:** Ensure all Win32-specific imports (`winreg`, `ctypes.windll`, `user32`) are safely guarded with try/except fallbacks so test suites can run on any OS.

---

## Pull Request Guidelines

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Write unit tests for new functionality in `tests/`.
3. Verify that all tests pass locally.
4. Push your branch and open a Pull Request against `main`.
