# Contributing to Kinexus AI

Thank you for your interest in contributing to Kinexus AI! This document provides guidelines and information for contributors.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Process](#development-process)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Community](#community)

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally: `git clone https://github.com/YOUR_USERNAME/kinexus-ai.git`
3. **Set up development environment** following the [Development Guide](docs/DEVELOPMENT_GUIDE.md)
4. **Create a feature branch**: `git checkout -b feature/your-feature-name`

## How to Contribute

### Types of Contributions

- **Bug Reports**: Help us identify and fix issues
- **Feature Requests**: Suggest new functionality
- **Code Contributions**: Submit bug fixes or new features
- **Documentation**: Improve or add documentation
- **Testing**: Write tests or test new features
- **Integrations**: Add support for new external systems

### Bug Reports

When filing a bug report, please include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, versions, etc.)
- Screenshots if applicable

### Feature Requests

For feature requests, please provide:
- Clear description of the proposed feature
- Use case and business justification
- Possible implementation approach
- Impact on existing functionality

## Development Process

### Branch Naming
- `feature/description` for new features
- `bugfix/description` for bug fixes
- `docs/description` for documentation updates
- `refactor/description` for code refactoring

### Commit Messages
Follow conventional commit format:
```
type(scope): description

body (optional)

footer (optional)
```

Examples:
- `feat(agents): add content generation capability`
- `fix(api): resolve authentication timeout issue`
- `docs(readme): update installation instructions`

### Code Standards

- Follow the [Development Guide](docs/DEVELOPMENT_GUIDE.md) for coding standards
- Write tests for new functionality
- Ensure all tests pass
- Maintain or improve code coverage
- Use type hints in Python code
- Follow security best practices

## Pull Request Process

1. **Update documentation** for any functionality changes
2. **Add tests** for new features or bug fixes
3. **Ensure all checks pass** (tests, linting, security scans)
4. **Request review** from maintainers
5. **Address feedback** promptly and professionally

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
```

## Issue Guidelines

### Before Creating an Issue
1. **Search existing issues** to avoid duplicates
2. **Check documentation** for known solutions
3. **Test with latest version** if possible

### Issue Labels
- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention needed
- `security`: Security-related issues
- `performance`: Performance improvements

## Community

### Communication Channels
- **GitHub Discussions**: For general questions and discussions
- **Discord**: [KinexusAI Community](https://discord.gg/kinexusai)
- **Email**: support@kinexusai.com for sensitive issues

### Meeting Schedule
- **Community Calls**: Monthly on first Wednesday at 2 PM UTC
- **Contributor Sync**: Bi-weekly on Thursdays at 4 PM UTC
- **Office Hours**: Weekly on Fridays at 3 PM UTC

### Recognition
Contributors are recognized through:
- **Contributors page** on our website
- **GitHub achievements** and badges
- **Annual contributor awards**
- **Conference speaking opportunities**

## Development Setup

Detailed setup instructions are available in the [Development Guide](docs/DEVELOPMENT_GUIDE.md).

Quick start:
```bash
git clone https://github.com/kinexusai/kinexus-ai.git
cd kinexus-ai
pip install -r requirements-dev.txt
pre-commit install
```

## Testing

Run the full test suite:
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests with coverage
pytest --cov=src tests/
```

## Documentation

Documentation improvements are always welcome:
- **API documentation**: Update docstrings
- **User guides**: Improve clarity and completeness
- **Developer docs**: Add examples and best practices
- **Tutorials**: Create step-by-step guides

## Security

Please report security vulnerabilities responsibly:
- **Do not** create public issues for security problems
- **Email** security@kinexusai.com with details
- **Use** GPG key for sensitive communications
- **Allow** time for fix before public disclosure

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (Apache 2.0).

## Questions?

If you have questions not covered here:
1. Check the [Documentation](docs/)
2. Search [GitHub Discussions](https://github.com/kinexusai/kinexus-ai/discussions)
3. Join our [Discord community](https://discord.gg/kinexusai)
4. Email us at contributors@kinexusai.com

Thank you for contributing to Kinexus AI! 🚀