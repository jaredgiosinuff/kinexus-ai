# Contributing to Kinexus AI

Thanks for investing time in the project! These guidelines explain how to propose changes and what we expect before opening a pull request.

## Code of Conduct
We follow the [Contributor Covenant](https://www.contributor-covenant.org/) v2.1. Engage respectfully and report violations to the maintainers.

## Getting Started
1. Fork the repository and create a feature branch: `git checkout -b feature/name`.
2. Follow the [Development Guide](docs/development.md) to set up the local stack.
3. Run `pytest tests/` before submitting changes.

## Development Workflow
- Keep commits focused and descriptive. We prefer [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, `docs:`). Include a scope when it adds clarity (`feat(api):`, `fix(agents):`).
- Update documentation when behavior changes. Use the consolidated docs under `docs/` and move superseded content to `docs/archive/legacy/`.
- For feature branches, push regularly and open drafts if you want early feedback.

## Pull Requests
Before requesting review:
- [ ] `pytest tests/` passes (include coverage if applicable).
- [ ] Code linted/formatted (we suggest `black`, `isort`, and `ruff`).
- [ ] Docs updated (`README.md`, `docs/`, or inline docstrings as needed).
- [ ] Screenshots or logs included when modifying UI or operational tooling.
- [ ] Secret keys and credentials removed from commits.

Describe the change, its motivation, and any follow-up tasks. Link related issues or roadmap items.

## Testing Expectations
- Prefer integration-style tests alongside the modules they exercise (e.g., `tests/test_model_integration.py`).
- Use mocks for external services unless you explicitly rely on LocalStack or the mock Bedrock server.
- If you introduce a new integration, include connection tests under `tests/`.

## Style & Naming
- Python: 4-space indent, snake_case for modules/functions, PascalCase for classes, type hints where practical.
- Frontend (optional): follow Vite/React conventions, prefer TypeScript.
- Configuration files: use lowercase kebab-case filenames.

## Documentation Contributions
- Update or create files in `docs/` to reflect the new reality.
- Archive outdated material by moving it into `docs/archive/legacy/`.
- Use Mermaid for diagrams instead of ASCII art.

## Releasing
Until automated pipelines are in place, coordinate with maintainers before pushing releases. See [docs/deployment.md](docs/deployment.md) for the current manual checklist.

## Getting Help
Open a discussion or ping maintainers through the repository issue tracker if you are blocked. We appreciate questions—it helps us keep docs honest.
