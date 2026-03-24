# Contributing to Chatapult

First, thank you for your interest in contributing to Chatapult. Building a robust, async-ready Python API wrapper for Google Chat webhooks is a community effort, and we welcome contributions of all kinds—from bug reports and documentation improvements to new feature implementations.

This document outlines the standard processes and coding guidelines for contributing to the Chatapult repository. By following these steps, you help ensure that the integration process is smooth, efficient, and transparent.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Reporting Bugs and Requesting Features](#reporting-bugs-and-requesting-features)
3. [Development Guidelines](#development-guidelines)
4. [Commit Message Stands](#commit-message-standards)
5. [Pull Request Process](#pull-request-process)

## Code of Conduct

We are committed to providing a welcoming and inspiring community for everyone. Be professional, respectful, and constructive in your communications. Harassment or abusive behavior will not be tolerated.

## Reporting Bugs and Requesting Features

GitHub Issues will be used to track public bugs and feature requests.

### Bug Reports

If you find a bug in the webhook client, please open an issue and include:
* A clear, descriptive title.
* The version of Python and Chatapult you are using.
* Steps to reproduce the unexpected behavior.
* Expected results versus actual results.
* Relevant tracebacks or error messages.

### Feature Requests

When requesting new features (such as support for new Google Workspace API cards or widgets), please provide:
* A clear description of the proposed feature.
* The specific use case or problem it solves.
* Any relevant links to the official Google Chat developer documentation.

## Development Guidelines

To ensure the codebase remains maintainable, highly adoptable, and standard across all contributors, we strictly adhere to automated code quality checks using `pre-commit`.

### Setting Up Pre-Commit Hooks

We use `pre-commit` to automatically run formatting (`black`), linting (`ruff`), and type-checking (`mypy`) every time you make a commit. This catches errors locally before the code is added to the codebase.

1. **Install the pre-commit package:**
```bash
pip install pre-commit
```
2. ** Install the git hooks:** Run this once in your local repository.
```bash
pre-commit install
```

Now, every time you run `git commit`, the hooks will automatically format your code and check for errors.

### Coding Standards

* **Type Hinting:** All new functions, methods, and classes must include strict Python type hints (`typing` module). The `mypy` pre-commit hook will fail if types are missing or incorrect.
* **Manual Hook Execution:** If you want to run the checks manually across all files without making a commit, you can run:
```bash
pre-commit run --all-files
```
* **Testing:** We use `pytest` for our test suite. All new features must include corresponding unit tests. Bug fixes must include a test that verifies the fix. Run the test suite locally using:
```bash
pytest
```
* **Documentation:** If you change the behavior of the API client or add new models, you must update the `README.md` and inline docstrings accordingly.

## Commit Message Standards

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. This leads to more readable project history and allows us to automate release notes.

Format: `<type>(<scope>): <subject>`

**Examples:**
* `feat(client): add async support for sending v2 cards`
* `fix(auth): resolve environment variable loading error`
* `docs(readme): update advanced usage examples`
* `test(models): add unit tests for image widget`

## Pull Request Process

1. **Create a Branch:** Always branch off of `main`. Name your branch descriptively (e.g., `feature/async-client` or `bugfix/rate-limit-retry`).
2. **Draft your PR:** Push your branch to your fork and open a Pull Request against the upstream `main` branch.
3. **Fill out the PR Template:** Provide a clear summary of your changes, the rationale, and link to any related issues (e.g., "Closes #12").
4. **Review:** A maintainer will review your code. Be prepared to make requested changes. Once approved, your PR will be merged.

Thank you for helping make Chatapult the easiest way to integrate Google Chat notifications into Python!
