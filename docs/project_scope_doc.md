# **PROJECT SCOPE: Insurance API V1→V2 Adapter**
## Life & ILP Products

### **1. PROJECT OVERVIEW**

**Purpose**: Create a FastAPI-based adapter that exposes modern V2 insurance APIs by transforming and orchestrating calls to legacy V1 APIs.

**Key Principle**: Configuration-driven transformation using AI-generated mappings, with zero runtime AI dependency.

---

### **2. SYSTEM COMPONENTS**

#### **2.1 Config Generator (Offline Tool)**
- **Technology**: Python CLI using Qwen 7B (local)
- **Input**: 
  - V2 OpenAPI spec (single endpoint at a time)
  - Complete V1 OpenAPI spec (all endpoints for field discovery)
  - Domain context (life insurance, ILP products)
- **Output**: 
  - Mapping configuration (YAML) with confidence scores
  - Multiple mapping proposals for ambiguous cases
- **Process**: Stepwise Python script that:
  1. Loads OpenAPI specs
  2. Constructs prompt with full context
  3. Calls Qwen 7B locally
  4. Validates generated config

#### **2.2 Mapping Viewer (Web UI)**
- **Technology**: Next.js web application
- **Features**:
  - Visual mapping review: V2 field → V1 source(s)
  - Side-by-side diff view
  - Approve/reject/edit individual mappings
  - Confidence score indicators
  - Export approved configs
- **Views**:
  - Endpoint-level overview
  - Field-level detail with JSONPath/param names
  - Transformation logic display

#### **2.3 FastAPI Adapter Server (Runtime)**
- **Technology**: FastAPI with async support
- **Responsibilities**:
  - Host V2 endpoints as per spec
  - Load YAML mapping configs on startup
  - Orchestrate V1 API calls (sequential/parallel as needed)
  - Apply field transformations
  - Handle errors with proper HTTP status codes
  - Structured JSON logging for request tracking

#### **2.4 Stub Service (Integrated)**
- **Technology**: FastAPI endpoints (same app)
- **Purpose**: Provide configurable default values for V2 fields unmappable to V1
- **Configuration**: YAML-defined defaults per endpoint/field

---

### **3. MAPPING CAPABILITIES**

The system must handle these transformation patterns:

| Pattern | Example |
|---------|---------|
| **Simple rename** | `v1.customer_name` → `v2.insured.fullName` |
| **Field combination** | `v1.first_name + " " + v1.last_name` → `v2.insured.name` |
| **Parameter location shift** | V1 query param `?policyId=123` → V2 path `/policies/123` |
| **Nested flattening** | `v1.policy.details.type` → `v2.policyType` |
| **Multi-endpoint aggregation** | V2 `/policy-summary` calls V1 `/policy` + `/coverage` |
| **1:1 passthrough** | Direct field mapping with same structure |
| **Unmappable fields** | V2 fields → Stub service defaults |

---

### **4. TRANSFORMATION EXPRESSION SYNTAX**

**Approach**: **JSONPath + Jinja2-style expressions**

```yaml
transformations:
  - v2_field: "insured.fullName"
    expression: "{{ v1.firstName }} {{ v1.lastName }}"
    
  - v2_field: "premium.annual"
    expression: "{{ v1.monthly_premium * 12 }}"
    
  - v2_field: "policyStatus"
    expression: "{{ 'active' if v1.status == 1 else 'inactive' }}"
```

**Rationale**: 
- Readable and familiar to developers
- Supports simple logic without full Python eval
- Easy for AI to generate
- Safe to execute (sandboxed)

---

### **5. CONFIGURATION SCHEMA**

```yaml
version: "1.0"
endpoint:
  v2_path: "/api/v2/policies/{policyId}"
  v2_method: "GET"
  
v1_calls:
  - name: "get_policy"
    endpoint: "/api/v1/policy"
    method: "GET"
    params:
      query:
        - v2_param: "policyId"
          v1_param: "policy_id"
          location: "path"  # shift from path to query
    
  - name: "get_coverage"
    endpoint: "/api/v1/coverage/{id}"
    method: "GET"
    params:
      path:
        - v2_param: "policyId"
          v1_param: "id"

field_mappings:
  - v2_path: "policyNumber"
    source: "get_policy"
    v1_path: "policy_num"
    transform: null
    
  - v2_path: "insured.name"
    source: "get_policy"
    v1_path: null
    transform: "{{ get_policy.first_name }} {{ get_policy.last_name }}"
    
  - v2_path: "coverageAmount"
    source: "get_coverage"
    v1_path: "amount"
    transform: null
    
  - v2_path: "digitalSignatureUrl"  # unmappable
    source: "stub"
    stub_value: null
    stub_type: "configurable_default"

metadata:
  generated_at: "2025-10-19T10:30:00Z"
  confidence_score: 0.92
  ambiguous_mappings:
    - v2_field: "effectiveDate"
      proposals:
        - {v1_field: "start_date", confidence: 0.7}
        - {v1_field: "issue_date", confidence: 0.6}
```

---

### **6. ERROR HANDLING**

#### **Error Strategy**: Fail-fast with clear HTTP status codes

| Scenario | HTTP Code | Response |
|----------|-----------|----------|
| V1 API returns 404 | 404 | `{"error": "Policy not found in legacy system", "code": "V1_NOT_FOUND"}` |
| V1 API returns 500 | 502 | `{"error": "Legacy system error", "code": "V1_SERVER_ERROR", "details": "..."}` |
| V1 API timeout | 504 | `{"error": "Legacy system timeout", "code": "V1_TIMEOUT"}` |
| Field mapping fails | 500 | `{"error": "Transformation error", "code": "MAPPING_ERROR", "field": "..."}` |
| Missing required V1 field | 500 | `{"error": "Required field missing from V1", "code": "V1_INCOMPLETE_DATA"}` |
| Invalid V2 request | 400 | `{"error": "Invalid request", "code": "INVALID_REQUEST"}` |

**Request Correlation**: Every request gets a unique `X-Request-ID` logged with:
- V2 endpoint called
- All V1 endpoints called
- Timestamps
- Success/failure status

---

### **7. LOGGING & OBSERVABILITY**

**Structured JSON Logging** (most scalable):

```json
{
  "timestamp": "2025-10-19T10:30:00Z",
  "request_id": "req_abc123",
  "v2_endpoint": "GET /api/v2/policies/POL001",
  "v1_calls": [
    {"endpoint": "GET /api/v1/policy?policy_id=POL001", "status": 200, "duration_ms": 45},
    {"endpoint": "GET /api/v1/coverage/POL001", "status": 200, "duration_ms": 32}
  ],
  "total_duration_ms": 89,
  "status": "success"
}
```

**Benefits**: Easy to parse, index in ELK/Datadog, query for analytics.

---

### **8. DEPLOYMENT ARCHITECTURE**

```
┌─────────────────┐
│   Web Browser   │
│  (Mapping UI)   │
└────────┬────────┘
         │
    ┌────▼────────────────┐
    │  FastAPI Server     │
    │  ┌──────────────┐   │
    │  │ V2 Endpoints │   │
    │  └──────┬───────┘   │
    │         │           │
    │  ┌──────▼────────┐  │
    │  │ Config Engine │  │
    │  │ (YAML Loader) │  │
    │  └──────┬────────┘  │
    │         │           │
    │  ┌──────▼────────┐  │
    │  │ Stub Service  │  │
    │  └───────────────┘  │
    └─────────┬───────────┘
              │
    ┌─────────▼───────────┐
    │   V1 API Cluster    │
    │  (Legacy Services)  │
    └─────────────────────┘

┌──────────────────┐
│ Config Generator │ (Offline)
│  (Qwen 7B CLI)   │
└──────────────────┘
```

---

### **9. PROJECT STRUCTURE (Monorepo)**

```
insurance-api-adapter/
├── README.md
├── docs/
│   ├── SCOPE.md (this file)
│   └── user-stories/
│       ├── US001-project-setup.md
│       ├── US002-yaml-config-schema.md
│       └── ...
├── backend/                    # FastAPI application
│   ├── pyproject.toml
│   ├── src/
│   │   ├── adapter/
│   │   │   ├── config_loader.py
│   │   │   ├── transformer.py
│   │   │   └── orchestrator.py
│   │   ├── api/
│   │   │   ├── v2_endpoints.py
│   │   │   └── stub_service.py
│   │   └── main.py
│   ├── configs/                # YAML mapping configs
│   └── tests/
├── config-generator/           # Qwen 7B CLI tool
│   ├── pyproject.toml
│   ├── src/
│   │   ├── spec_loader.py
│   │   ├── qwen_client.py
│   │   ├── prompt_templates.py
│   │   └── config_generator.py
│   ├── specs/                  # Sample OpenAPI specs
│   │   ├── v1/
│   │   └── v2/
│   └── tests/
└── frontend/                   # Next.js mapping viewer
    ├── package.json
    ├── src/
    │   ├── app/
    │   ├── components/
    │   └── lib/
    └── public/
```

---

### **10. TEST SCENARIOS TO CREATE**

You'll need to generate sample OpenAPI specs for:

1. **Scenario 1**: Simple field rename (1:1 mapping)
2. **Scenario 2**: Field combination (firstName + lastName)
3. **Scenario 3**: Query param → Path param
4. **Scenario 4**: Nested object flattening
5. **Scenario 5**: 1 V2 endpoint → 2 V1 endpoints
6. **Scenario 6**: Body param → Query param
7. **Scenario 7**: V2 field unmappable (uses stub)

---

### **11. OUT OF SCOPE (V1)**

- Authentication/authorization (assume handled upstream)
- Rate limiting
- Caching (initially - can add if needed)
- Database persistence of configs (file-based only)
- Real-time config reloading (requires restart)
- V1 API pagination handling
- Webhook/async V1 calls

---

### **12. IMPLEMENTATION APPROACH**

**Bottom-Up Development**: Build from core engine to UI to avoid hidden fallbacks, unreversed hard-coding, or mocks.

**Order of Implementation**:
1. Core transformation engine
2. Config loader and validator
3. V1 API orchestrator
4. FastAPI V2 endpoint generator
5. Stub service
6. Config generator (Qwen integration)
7. Mapping viewer UI

---

### **13. SUCCESS CRITERIA**

- [ ] All 7 test scenarios successfully transform V1→V2
- [ ] Config generator produces valid YAML with >80% confidence
- [ ] Mapping viewer allows approval/rejection of AI proposals
- [ ] Runtime adapter handles all error scenarios correctly
- [ ] Request tracking logs all V1 calls per V2 request
- [ ] Zero hardcoded transformations (all config-driven)

---

### **14. TECH STACK SUMMARY**

| Component | Technology |
|-----------|-----------|
| Runtime API | FastAPI (Python 3.11+) |
| Config Generator | Python CLI + Qwen 7B |
| Mapping Viewer | Next.js 14+ (React) |
| Config Format | YAML |
| Transformation Engine | Jinja2 templates |
| Logging | Structured JSON |
| Testing | pytest, Jest |
| Monorepo | Shared root with separate package.json/pyproject.toml |

---

### **NEXT STEPS**

1. ✅ Review and approve this scope document
2. Generate user story files (US001-US0XX)
3. Set up monorepo structure
4. Begin bottom-up implementation in VS Code with Claude Code
