# Welcome to GenAI-PoD Contributing Guide

Thank you for taking the time to contribute to the [GenAI-PoD](https://github.com/LeonhardSchwertfeger/GenAI-PoD/) project!

Please make sure to read our [Code of Conduct](./CODE_OF_CONDUCT.md) to ensure a respectful and welcoming community.

If you have questions, suggestions, or topics to discuss, feel free to participate in [GenAI-PoD/discussions](https://github.com/LeonhardSchwertfeger/GenAI-PoD/discussions). We look forward to engaging discussions, exchanging strategies, and fostering knowledge sharing!

## Getting Started 🤖

This guide provides an overview of the contribution workflow, including opening an issue, creating a pull request (PR), reviewing, and merging the PR.

### Issues

#### Create a New Issue

If you encounter an issue not listed in the troubleshooting section of [README.md](https://github.com/LeonhardSchwertfeger/GenAI-PoD#readme) or [documentation](), feel free to create a new [issue](https://github.com/LeonhardSchwertfeger/GenAI-PoD/issues). If the issue or feature request does not already exist, this is the best place to share it.

#### Solve an Issue

Browse through the [existing issues](https://github.com/LeonhardSchwertfeger/GenAI-PoD/issues) to find one that interests you. You can also filter issues using labels to focus on specific areas.

### Make Changes

1. **Fork the Repository**
   Create your fork of the repository by clicking the "Fork" button on GitHub.

2. **Clone Your Fork**
   Clone your forked repository locally:

   ```bash
   git clone https://github.com/<your-username>/GenAI-PoD.git
   cd GenAI-PoD
   ```

3. **Set Up the Upstream Remote**
   Add the original repository as the upstream remote:

   ```bash
   git remote add upstream https://github.com/LeonhardSchwertfeger/GenAI-PoD.git
   ```

4. **Synchronize Your Fork**
   Keep your fork updated by syncing it with the upstream repository:

   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

5. **Create a New Branch**
   Create a new branch for your changes:

   ```bash
   git checkout -b feature/your-feature-name
   ```

6. **Implement Your Changes**
   Make your changes locally. Use the provided Makefile for common tasks:

   - Run all unit tests:
     ```bash
     make test
     ```
   - Build the package:
     ```bash
     make build
     ```
   - Install in editable mode for development:
     ```bash
     make dev
     ```

7. **Install Pre-Commit Hooks**
   Ensure all pre-commit hooks pass before pushing:

   ```bash
   pre-commit install
   pre-commit run -a
   ```

8. **Commit Your Changes**
   Once satisfied with your changes, commit them with a meaningful message:
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

### Pull Request

#### Push Your Branch

Push your branch to your fork:

```bash
git push origin feature_or_bug/your-feature-name
```

#### Create a Pull Request

Open a pull request (PR) from your fork to the original repository. Make sure to:

- Address all requirements in the self-review checklist.
- Link the PR to an issue if applicable.
- Respond to requested changes and mark conversations as resolved as needed.

### Your PR is Merged! 🏅

Congratulations! Thank you for contributing to GenAI-PoD. Feel free to pick up the next issue or suggest additional improvements. 🚀
