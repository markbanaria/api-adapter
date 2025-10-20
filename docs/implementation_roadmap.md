# Implementation Roadmap

## Overview

This document provides a complete roadmap for implementing the Insurance API V1→V2 Adapter using Claude Code in VS Code.

## User Stories (Bottom-Up Order)

| # | Story | Components | Estimated Time |
|---|-------|------------|----------------|
| US001 | Project Setup & Monorepo | All | 1-2 hours |
| US002 | YAML Config Schema & Validator | Backend | 2-3 hours |
| US003 | Jinja2 Transformation Engine | Backend | 3-4 hours |
| US004 | V1 API Orchestrator | Backend | 4-5 hours |
| US005 | V2 Response Builder | Backend | 2-3 hours |
| US006 | FastAPI V2 Endpoints | Backend | 3-4 hours |
| US007 | Sample OpenAPI Specs | Config Generator | 2-3 hours |
| US008 | Qwen 7B Config Generator | Config Generator | 4-6 hours |
| US009 | Mapping Viewer UI | Frontend | 6-8 hours |
| US010 | Backend Config Management API | Backend | 2-3 hours |
| US011 | E2E Testing & Documentation | All | 3-4 hours |

**Total Estimated Time**: 32-45 hours

## Implementation Strategy with Claude Code

### Phase 1: Core Engine (US001-US006)

**Goal**: Build the runtime adapter that can transform V1→V2

#### US001: Project Setup
```bash
# In VS Code with Claude Code
cd /path/to/workspace
claude "Set up the monorepo structure according to US001"
```

**What Claude Code will do**:
- Create directory structure
- Initialize pyproject.toml files
- Initialize package.json
- Create .gitignore
- Set up basic README

**Verify**: Run `pip install -e ".[dev]"` in backend and config-generator

#### US002: YAML Config Schema
```bash
claude "Implement the YAML configuration schema and validator from US002"
```

**What Claude Code will do**:
- Create Pydantic models in `backend/src/adapter/models.py`
- Implement ConfigLoader in `backend/src/adapter/config_loader.py`
- Create example YAML configs
- Write unit tests

**Verify**: Run `pytest backend/tests/test_config_loader.py`

#### US003: Transformation Engine
```bash
claude "Implement the Jinja2 transformation engine from US003"
```

**What Claude Code will do**:
- Create FieldTransformer in `backend/src/adapter/transformer.py`
- Implement sandboxed Jinja2 environment
- Add transformation methods
- Write comprehensive unit tests

**Verify**: Run `pytest backend/tests/test_transformer.py`

#### US004: V1 Orchestrator
```bash
claude "Implement the V1 API orchestrator from US004"
```

**What Claude Code will do**:
- Create V1Orchestrator in `backend/src/adapter/orchestrator.py`
- Implement HTTP client with error handling
- Add parameter mapping logic
- Write async tests

**Verify**: Run `pytest backend/tests/test_orchestrator.py`

#### US005: Response Builder
```bash
claude "Implement the V2 response builder from US005"
```

**What Claude Code will do**:
- Create V2ResponseBuilder in `backend/src/adapter/response_builder.py`
- Implement nested object creation
- Integrate with FieldTransformer
- Write unit tests

**Verify**: Run `pytest backend/tests/test_response_builder.py`

#### US006: FastAPI Endpoints
```bash
claude "Implement the FastAPI V2 endpoints from US006"
```

**What Claude Code will do**:
- Update `backend/src/adapter/main.py` with endpoint registration
- Add error handling and logging
- Create integration tests
- Set up health check

**Verify**: 
```bash
uvicorn adapter.main:app --reload
curl http://localhost:8000/health
```

### Phase 2: Config Generation (US007-US008)

**Goal**: Build the offline AI-powered config generator

#### US007: Sample Specs
```bash
claude "Create the sample OpenAPI specifications from US007"
```

**What Claude Code will do**:
- Create 7 V2 scenario specs in JSON
- Create complete V1 spec in JSON
- Validate OpenAPI format
- Create README explaining each scenario

**Verify**: Validate specs with `swagger-cli validate`

#### US008: Qwen Integration
```bash
claude "Implement the Qwen 7B config generator from US008"
```

**What Claude Code will do**:
- Create QwenClient in `config-generator/src/generator/qwen_client.py`
- Create prompt templates in `config-generator/src/generator/prompt_templates.py`
- Implement ConfigGenerator with YAML parsing
- Create CLI tool
- Write tests

**Verify**:
```bash
# Ensure Qwen is running
ollama serve

# Generate a config
generate-config \
  --v2-spec specs/v2/scenario1-simple-rename.json \
  --v1-spec specs/v1/complete-v1-api.json \
  --endpoint "/api/v2/policies/{policyId}" \
  --output test-output.yaml
```

### Phase 3: UI & Management (US009-US010)

**Goal**: Build the mapping review interface

#### US009: Mapping Viewer UI
```bash
claude "Implement the Next.js mapping viewer UI from US009"
```

**What Claude Code will do**:
- Create Next.js pages and components
- Implement TypeScript types
- Create API client
- Style with Tailwind CSS
- Add interactive features

**Verify**:
```bash
cd frontend
npm run dev
# Open http://localhost:3000
```

#### US010: Config Management API
```bash
claude "Implement the backend config management API from US010"
```

**What Claude Code will do**:
- Create config API routes
- Add CORS middleware
- Implement CRUD operations
- Write API tests

**Verify**: 
```bash
curl http://localhost:8000/configs
```

### Phase 4: Testing & Documentation (US011)

**Goal**: Ensure everything works end-to-end

#### US011: E2E Testing
```bash
claude "Implement end-to-end testing and documentation from US011"
```

**What Claude Code will do**:
- Create mock V1 server
- Write E2E test suite
- Create comprehensive README
- Write troubleshooting guide
- Generate API documentation

**Verify**:
```bash
pytest backend/tests/test_e2e.py -v
```

## Working with Claude Code

### Best Practices

1. **One User Story at a Time**: Complete each US before moving to the next
2. **Verify After Each Step**: Run tests and check functionality
3. **Review Generated Code**: Claude Code produces high-quality code, but always review
4. **Iterate as Needed**: If something doesn't work, ask Claude Code to fix it

### Example Claude Code Commands

```bash
# Implement a user story
claude "Implement US003: Jinja2 Transformation Engine"

# Fix a test failure
claude "The test test_transform_combination is failing with error: ... Please fix it"

# Add a feature
claude "Add a new transformation filter to support date formatting in the FieldTransformer"

# Refactor
claude "Refactor the orchestrator to use parallel V1 calls instead of sequential"
```

### Troubleshooting with Claude Code

If you encounter issues:

```bash
# Share the error
claude "I'm getting this error when running the tests: [paste error]. Please help me fix it."

# Ask for explanation
claude "Can you explain how the parameter mapping works in the orchestrator?"

# Request improvements
claude "The response time is slow. Can you optimize the V1 orchestrator?"
```

## Validation Checkpoints

After completing each phase, verify:

### ✅ Phase 1 Complete
- [ ] All backend tests passing
- [ ] V2 endpoint responds with transformed data
- [ ] Error handling works (404, 500, timeout)
- [ ] Logging includes request IDs

### ✅ Phase 2 Complete
- [ ] Qwen generates valid YAML configs
- [ ] Configs load without errors
- [ ] All 7 scenarios have generated configs

### ✅ Phase 3 Complete
- [ ] UI displays all configs
- [ ] Mapping table shows all fields correctly
- [ ] Edit and approve functionality works
- [ ] YAML export downloads correctly

### ✅ Phase 4 Complete
- [ ] All E2E tests passing
- [ ] README allows new developer to set up system
- [ ] Documentation is comprehensive
- [ ] System runs end-to-end successfully

## Success Metrics

The project is complete when:

1. ✅ All 11 user stories implemented
2. ✅ All unit tests passing (>90% coverage)
3. ✅ All integration tests passing
4. ✅ All E2E tests passing for 7 scenarios
5. ✅ Documentation complete and accurate
6. ✅ System can be deployed and run from scratch

## Next Steps

1. Review this roadmap and all user stories
2. Ensure Qwen 7B is installed: `ollama pull qwen:7b`
3. Open VS Code with Claude Code extension
4. Start with US001 and work through systematically
5. Test after each user story completion

Good luck with your implementation! 🚀
