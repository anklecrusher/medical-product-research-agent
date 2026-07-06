# Codex Local Environment

Use this folder for project-specific Codex setup helpers.

Recommended Windows setup script for the Codex app environment settings:

```powershell
powershell -ExecutionPolicy Bypass -File .codex/setup.ps1
```

Recommended actions:

```powershell
powershell -ExecutionPolicy Bypass -File .codex/actions.ps1 test
```

```powershell
powershell -ExecutionPolicy Bypass -File .codex/actions.ps1 doctor
```

The setup script creates `.venv`, installs Python dependencies from `pyproject.toml`, creates local runtime directories, and runs `npm install` only after a future frontend adds `package.json`.

