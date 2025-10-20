# Active Context - Insurance API Adapter Project

## Project Status: Phase 1 - Foundation Complete

### Completed User Stories

#### ✅ US001: Project Setup & Monorepo Structure
- **Status**: Complete
- **Components**: All
- **What was built**:
  - Monorepo directory structure created
  - Backend Python project (FastAPI) with pyproject.toml and hatchling build system
  - Config-generator Python CLI project with pyproject.toml and entry points
  - Frontend Next.js project with TypeScript and package.json
  - Root .gitignore with proper exclusions for Python, Node, and project-specific files
  - Individual README files for each component
  - Root README with quick start instructions
- **Verification**: All three projects can install dependencies and run independently

#### ✅ US002: YAML Configuration Schema & Validator
- **Status**: Complete
- **Components**: Backend
- **What was built**:
  - Complete Pydantic models for configuration validation in `backend/src/adapter/models.py`
  - ConfigLoader class for YAML file processing in `backend/src/adapter/config_loader.py`
  - 4 example YAML configuration files covering different transformation scenarios
  - Comprehensive unit tests with 100% pass rate
  - Robust error handling for YAML syntax errors and validation failures
  - Field validation for Jinja2 transforms, source references, and required fields
- **Verification**: All example configs validate successfully, 11 unit tests pass

#### ✅ US003: Jinja2 Transformation Engine
- **Status**: Complete
- **Components**: Backend
- **What was built**:
  - FieldTransformer class with sandboxed Jinja2 environment in `backend/src/adapter/transformer.py`
  - Support for all transformation patterns: field combination, arithmetic, conditionals, nested access
  - Robust error handling with TransformationError and clear error messages
  - Type coercion for string results (int, float, bool)
  - Custom Jinja2 filters (to_upper, to_lower)
  - Complete apply_mapping method for field mappings with transforms and direct mappings
  - Comprehensive unit tests covering 27 test cases with 100% pass rate
- **Verification**: All transformation patterns work, 38 total backend tests pass

#### ✅ US004: V1 API Orchestrator
- **Status**: Complete
- **Components**: Backend
- **What was built**:
  - V1Orchestrator class with async HTTP client in `backend/src/adapter/orchestrator.py`
  - Complete parameter mapping system (path, query, body) with location shifting support
  - HTTP error handling with proper status code mapping (404→404, 500→502, timeout→504)
  - Request correlation logging with UUID generation for traceability
  - V1OrchestratorError custom exception with status codes and details
  - Support for sequential V1 call execution with fail-fast behavior
  - URL building with both {param} and :param placeholder styles
  - Comprehensive async unit tests covering 21 test cases with 100% pass rate
- **Verification**: All orchestration patterns work, 59 total backend tests pass

#### ✅ US007: Sample OpenAPI Specs (Test Scenarios)
- **Status**: Complete
- **Components**: Config Generator
- **What was built**:
  - 7 V2 scenario specifications covering all transformation patterns:
    1. Simple field rename (policy_num → policyNumber)
    2. Field combination (first_name + last_name → fullName)
    3. Query to path parameter conversion
    4. Nested object flattening
    5. Multiple V1 endpoints aggregation
    6. Body to query parameter transformation
    7. Unmappable fields with null stubs
  - Complete V1 API specification with all legacy endpoints
  - Comprehensive README explaining each scenario and transformation pattern
  - All specs are valid OpenAPI 3.0 format
  - Stored in proper directory structure: config-generator/specs/v1/ and config-generator/specs/v2/

### Current Architecture

```
api-adapter/
├── backend/                 # FastAPI adapter service
│   ├── src/adapter/        # Main package (empty, ready for implementation)
│   ├── configs/            # YAML configuration storage
│   ├── tests/              # Test directory
│   └── pyproject.toml      # Python dependencies and build config
├── config-generator/       # AI-powered config generator
│   ├── src/generator/      # Main package (empty, ready for implementation)
│   ├── specs/              # ✅ OpenAPI specifications (COMPLETE)
│   │   ├── v1/complete-v1-api.json
│   │   ├── v2/scenario1-7.json
│   │   └── README.md
│   ├── tests/              # Test directory
│   └── pyproject.toml      # Python dependencies with AI libs
├── frontend/               # Next.js mapping viewer
│   ├── src/                # Source directory (empty, ready for implementation)
│   └── package.json        # Node.js dependencies
└── docs/                   # Project documentation
    ├── US001-011 specs     # All user story specifications
    └── implementation_roadmap.md
```

### Technology Stack Confirmed
- **Backend**: FastAPI, Pydantic, Jinja2, httpx, uvicorn
- **Config Generator**: Python CLI with click, rich, openai (for local LLM), PyYAML
- **Frontend**: Next.js 14, React 18, TypeScript, ESLint
- **Build Tools**: Hatchling (Python), npm (Node.js)
- **AI Model**: Qwen 7B (to be integrated in US008)

### Key Domain Concepts Established
- **Insurance Products**: Life insurance and Investment-Linked Policies (ILP)
- **Core Entities**: Policies, Customers/Insured, Coverage, Beneficiaries
- **Transformation Patterns**: Field renaming, combination, parameter shifting, flattening, aggregation, stubbing
- **API Evolution**: V1 (legacy, snake_case, nested) → V2 (modern, camelCase, flat)

### Dependencies Ready
- ✅ Backend: FastAPI ecosystem, async HTTP, templating, validation
- ✅ Config Generator: AI client libs, CLI tools, YAML processing
- ✅ Frontend: Modern React/Next.js stack with TypeScript

### Next Phase: Core Engine Implementation
Ready to implement US002-US006 (YAML schema, transformation engine, orchestrator, response builder, FastAPI endpoints).

---

## Next Story: US002 - YAML Config Schema & Validator

### Overview
Implement the configuration schema and validation system that will define how V1→V2 transformations are configured.

### Key Components to Build
- Pydantic models for configuration validation
- ConfigLoader for YAML file processing
- Example configuration files
- Unit tests for validation logic

### Entry Point
File: `backend/src/adapter/models.py` - Define the configuration data models