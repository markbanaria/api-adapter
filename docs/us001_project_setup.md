# User Story 001: Project Setup & Monorepo Structure

## Story
As a developer, I want to set up the monorepo structure with proper tooling so that all components can be developed and tested independently.

## Acceptance Criteria
- [ ] Monorepo root created with proper .gitignore
- [ ] Backend (FastAPI) project initialized with pyproject.toml
- [ ] Config-generator (Python CLI) project initialized with pyproject.toml
- [ ] Frontend (Next.js) project initialized with package.json
- [ ] Directory structure matches the scope document
- [ ] README.md with setup instructions created
- [ ] All three projects can run independently
- [ ] Pre-commit hooks configured (optional but recommended)

## Technical Details

### Directory Structure
```
insurance-api-adapter/
├── README.md
├── .gitignore
├── docs/
│   ├── SCOPE.md
│   └── user-stories/
├── backend/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/
│   │   └── adapter/
│   │       └── __init__.py
│   ├── configs/
│   └── tests/
├── config-generator/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/
│   │   └── generator/
│   │       └── __init__.py
│   ├── specs/
│   │   ├── v1/
│   │   └── v2/
│   └── tests/
└── frontend/
    ├── package.json
    ├── README.md
    └── src/
```

### Backend pyproject.toml
```toml
[project]
name = "insurance-api-adapter"
version = "0.1.0"
description = "FastAPI adapter for V1 to V2 insurance APIs"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.5.0",
    "pyyaml>=6.0.1",
    "jinja2>=3.1.2",
    "httpx>=0.25.0",
    "python-json-logger>=2.0.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "pytest-cov>=4.1.0",
    "black>=23.11.0",
    "ruff>=0.1.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Config-Generator pyproject.toml
```toml
[project]
name = "config-generator"
version = "0.1.0"
description = "AI-powered config generator using Qwen 7B"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0.1",
    "pydantic>=2.5.0",
    "openai>=1.3.0",  # For local LLM API compatibility
    "rich>=13.7.0",   # For CLI output
    "click>=8.1.7",   # For CLI
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "black>=23.11.0",
    "ruff>=0.1.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
generate-config = "generator.cli:main"
```

### Frontend package.json (Next.js)
```json
{
  "name": "mapping-viewer",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "next": "^14.2.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "typescript": "^5",
    "eslint": "^8",
    "eslint-config-next": "14.2.0"
  }
}
```

### Root .gitignore
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.venv/
*.egg-info/
dist/
build/

# Node
node_modules/
.next/
out/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
backend/configs/*.yaml
!backend/configs/example.yaml
config-generator/specs/*.json
!config-generator/specs/example-*.json
```

## Testing
- [ ] `cd backend && pip install -e ".[dev]"` works
- [ ] `cd config-generator && pip install -e ".[dev]"` works
- [ ] `cd frontend && npm install` works
- [ ] `cd backend && pytest` runs (even with no tests yet)
- [ ] `cd frontend && npm run dev` starts Next.js dev server

## Definition of Done
- All directories created
- All package files have correct dependencies
- README with quick start instructions exists
- Each component can be installed/run independently
