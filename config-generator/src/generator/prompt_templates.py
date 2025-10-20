SYSTEM_PROMPT = """You are an expert API mapping specialist for insurance systems. Your task is to analyze V1 (legacy) and V2 (modern) API specifications and generate precise field mappings.

You understand:
- Life insurance and ILP (Investment-Linked Policy) products
- Common field naming conventions in insurance APIs
- Data transformations (field combinations, type conversions, nested structures)
- Parameter location shifts (path, query, body)

Generate mappings in YAML format following the exact schema provided."""


def create_mapping_prompt(v2_spec: dict, v1_spec: dict, v2_endpoint_path: str) -> str:
    """Create a detailed prompt for config generation"""

    # Load transformation specification
    try:
        from pathlib import Path
        spec_path = Path(__file__).parent.parent.parent / "SIMPLE_TRANSFORM_RULES.md"
        simple_rules = spec_path.read_text()

        main_spec_path = Path(__file__).parent.parent.parent / "TRANSFORMATION_SPEC.md"
        transformation_spec = main_spec_path.read_text()
    except Exception:
        simple_rules = "# Rules not found"
        transformation_spec = "# Transformation specification not found - follow basic rules"

    # Extract V2 endpoint details
    v2_endpoint = None
    for path, methods in v2_spec.get("paths", {}).items():
        if path == v2_endpoint_path:
            v2_endpoint = {"path": path, "methods": methods}
            break

    if not v2_endpoint:
        raise ValueError(f"V2 endpoint {v2_endpoint_path} not found in spec")

    # Extract all V1 endpoints
    v1_endpoints = v1_spec.get("paths", {})

    prompt = f"""# Task: Generate API Mapping Configuration

## ⚠️ CRITICAL: TRANSFORM SYNTAX WARNING - READ FIRST ⚠️
BEFORE generating ANY transform, remember:
- ❌ ABSOLUTELY FORBIDDEN: {{ 'key': value }} syntax inside transform
- ❌ FORBIDDEN: transform: '{{%- for item in source -%}}{{{{ ''name'': item.field }}}}{{%- endfor -%}}'
- ✅ REQUIRED: Use literal JSON format with 'source' variable:
```yaml
transform: |
  [
    {{% for item in source %}}
    {{
      "name": "{{{{ item.beneficiary_name }}}}",
      "relationship": "{{{{ item.relation }}}}"
    }}{{%- if not loop.last -%}},{{%- endif %}}
    {{% endfor %}}
  ]
```
- ✅ Template context provides: 'source' (current source data), all V1 call names (getBeneficiaries_v1, etc.)

## Domain Context
- **Industry**: Life Insurance & Investment-Linked Policies (ILP)
- **Goal**: Map legacy V1 API to modern V2 API
- **Approach**: Semantic field matching with transformations

## Transformation Specification
{transformation_spec}

## V2 API Endpoint (TARGET)
```json
{v2_endpoint}
```

## V1 API Endpoints (SOURCE - Complete API)
```json
{v1_endpoints}
```

## Mapping Requirements

### 1. Identify Required V1 Endpoints
- CRITICAL: Only use V1 endpoints that actually exist in the provided V1 API spec
- Do NOT create or assume any endpoints that are not explicitly listed in the V1 spec
- PRIORITY: Always try to use MULTIPLE V1 endpoints to build complete V2 responses
- Analyze which existing V1 endpoints contain data that could be semantically mapped to the V2 response
- For insurance APIs, typically use separate calls for: policy, coverage, beneficiaries, customer data
- List each V1 endpoint with a unique name (e.g., getPolicy_v1, getCoverage_v1, getBeneficiaries_v1)
- ONLY use stub mappings when NO suitable V1 endpoints exist for specific fields

### 2. Follow Transformation Specification
- CRITICAL: Follow the exact format specified in TRANSFORMATION_SPEC.md
- Parameter mapping: v2_param must match V2 exactly, location indicates WHERE it comes FROM
- Field mapping: source = call name only, v1_path = null when using transform
- Use multiple V1 calls to build complete V2 responses

### 3. Map Response Fields
- CRITICAL: Only reference sources that are defined in the v1_calls section above
- Match V2 fields to V1 fields semantically (not just by name)
- All field_mappings must use source names that exist in v1_calls
- For field combinations (e.g., fullName = firstName + lastName):
  - Use Jinja2 syntax: `{{{{ v1_call_name.field1 }}}} {{{{ v1_call_name.field2 }}}}`
- For nested V1 fields (e.g., policy.details.type):
  - Use dot notation in v1_path
- For V2 fields with no V1 equivalent (USE SPARINGLY):
  - FIRST: Double-check if the data exists in ANY of the available V1 endpoints
  - ONLY use stubs when absolutely no V1 data source exists
  - Set source to "stub" and provide appropriate stub_value and stub_type:
    * For arrays: stub_value: [], stub_type: "empty_array"
    * For strings: stub_value: "", stub_type: "empty_string"
    * For nulls: stub_value: null, stub_type: "null"
    * For configurable values: stub_type: "configurable_default"

### 4. Confidence Scoring
- Assign confidence score (0.0-1.0) to overall mapping
- If any field mapping is ambiguous, list it in `ambiguous_mappings` with multiple proposals

## Output Format

Generate YAML in this EXACT format:

```yaml
version: "1.0"
endpoint:
  v2_path: "<V2 endpoint path>"
  v2_method: "<HTTP method in UPPERCASE>"

v1_calls:
  - name: "<unique_identifier>"
    endpoint: "<V1 endpoint path>"
    method: "<HTTP method in UPPERCASE>"
    params:
      path:  # Optional
        - v2_param: "<V2 parameter name>"
          v1_param: "<V1 parameter name>"
          location: "path"  # where this param comes from in V2
      query:  # Optional
        - v2_param: "<V2 parameter name>"
          v1_param: "<V1 parameter name>"
          location: "<path|query|body>"
      body:  # Optional
        - v2_param: "<V2 parameter name>"
          v1_param: "<V1 parameter name>"
          location: "body"
  # ADD MORE V1 CALLS AS NEEDED:
  - name: "<unique_identifier_2>"  # e.g., getCoverage_v1
    endpoint: "<another V1 endpoint path>"
    method: "<HTTP method in UPPERCASE>"
    params:
      # Parameters for this call...
  - name: "<unique_identifier_3>"  # e.g., getBeneficiaries_v1
    endpoint: "<third V1 endpoint path>"
    method: "<HTTP method in UPPERCASE>"
    params:
      # Parameters for this call...

field_mappings:
  - v2_path: "<V2 field path with dots for nesting>"
    source: "<v1_call_name or 'stub'>"  # ONLY the call name from v1_calls, NO dots/fields here!
    v1_path: "<V1 field path with dots>"  # MUST be null if using transform, otherwise field path
    transform: null  # or Jinja2 expression like "{{{{ source.field1 }}}} {{{{ source.field2 }}}}"

  # For unmappable fields:
  - v2_path: "<field_name>"
    source: "stub"
    stub_value: null  # or [] for arrays, "" for strings, etc.
    stub_type: "null"  # must be one of: "null", "configurable_default", "empty_string", "empty_array"

metadata:
  generated_at: "<ISO 8601 timestamp>"
  confidence_score: <0.0-1.0>
  ambiguous_mappings:  # Optional
    - v2_field: "<field_name>"
      proposals:
        - v1_field: "<option1>"
          confidence: <0.0-1.0>
        - v1_field: "<option2>"
          confidence: <0.0-1.0>
```

## CONCRETE EXAMPLE for V2 endpoint /api/v2/complete-policy/{{policyId}}:
```yaml
version: "1.0"
endpoint:
  v2_path: /api/v2/complete-policy/{{policyId}}
  v2_method: GET

v1_calls:
  - name: getPolicy_v1
    endpoint: /api/v1/policy/{{id}}
    method: GET
    params:
      path:
        - v2_param: policyId  # V2 has {{policyId}} in path
          v1_param: id        # V1 needs {{id}} in path
          location: path      # policyId comes from V2 path

  - name: getCoverage_v1
    endpoint: /api/v1/coverage
    method: GET
    params:
      query:
        - v2_param: policyId    # Use the SAME V2 path param
          v1_param: policy_id   # V1 needs policy_id as query
          location: path        # policyId still comes from V2 path

  - name: getBeneficiaries_v1
    endpoint: /api/v1/beneficiaries
    method: GET
    params:
      query:
        - v2_param: policyId    # Use the SAME V2 path param
          v1_param: policy_id   # V1 needs policy_id as query
          location: path        # policyId still comes from V2 path

field_mappings:
  - v2_path: .policyNumber
    source: getPolicy_v1  # ONLY the call name, NO dots
    v1_path: .policy_num  # Field path goes here
  - v2_path: .beneficiaries
    source: getBeneficiaries_v1
    v1_path: null  # MUST be null when using transform
    transform: "{{%- for item in source -%}}{{{{ 'name': item.beneficiary_name, 'relationship': item.relation }}}}{{%- endfor -%}}"
```

## Important Notes
- CRITICAL: Only use endpoints that exist in the V1 API spec above
- CRITICAL: In field_mappings, the 'source' field must ONLY contain the V1 call name (e.g., 'getPolicy_v1'), NOT include field paths
- CRITICAL: Field paths must go in 'v1_path', never in 'source' (Wrong: source: 'getPolicy_v1.policy_num', Right: source: 'getPolicy_v1', v1_path: '.policy_num')
- CRITICAL: When using 'transform', set 'v1_path: null' (not empty array []). When NOT using transform, provide the field path in v1_path
- Use semantic matching (e.g., "policy_num" → "policyNumber")
- If a V2 endpoint cannot be mapped to existing V1 endpoints, use stub mappings
- Example V1-only endpoints available: /api/v1/policy/{{id}}, /api/v1/coverage, /api/v1/beneficiaries
- Common insurance fields:
  - Customer: first_name, last_name, customer_age, email_address
  - Policy: policy_num, policy_status, policy_type, premium_amount
  - Coverage: amount, type
  - ILP: fund_value, unit_price, allocation_rate
- Be conservative with confidence scores (0.95+ only for very clear mappings)
- Always provide reasoning for ambiguous mappings

## ⚠️ CRITICAL: TRANSFORM SYNTAX WARNING ⚠️
BEFORE generating ANY transform, remember:
- ❌ FORBIDDEN: transform: '{{%- for item in source -%}}{{{{ ''name'': item.field, ''other'': item.field }}}}{{%- endfor -%}}'
- ❌ FORBIDDEN: Any {{ }} containing object creation like {{ 'key': value }}
- ✅ REQUIRED: Use literal JSON format from SIMPLE_TRANSFORM_RULES.md:
```yaml
transform: |
  [
    {{% for item in source %}}
    {{
      "name": "{{{{ item.beneficiary_name }}}}",
      "relationship": "{{{{ item.relation }}}}"
    }}{{%- if not loop.last -%}},{{%- endif %}}
    {{% endfor %}}
  ]
```

Generate the YAML configuration now:"""

    return prompt


def create_correction_prompt(original_prompt: str, previous_config: str, validation_errors: str) -> str:
    """Create a correction prompt for iterative improvement"""

    correction_prompt = f"""# TASK: Fix Configuration Errors

## ⚠️ CRITICAL: You generated a config with validation errors that must be fixed.

## ORIGINAL TASK
{original_prompt}

## YOUR PREVIOUS ATTEMPT (WITH ERRORS)
```yaml
{previous_config}
```

## VALIDATION ERRORS FOUND
{validation_errors}

## INSTRUCTIONS FOR CORRECTION
1. **CAREFULLY READ** all validation errors above
2. **FIX EACH ERROR** following the suggested fixes
3. **MAINTAIN** all correct parts of your previous config
4. **ENSURE** the corrected config follows ALL specification rules
5. **DOUBLE-CHECK** transform syntax uses literal JSON format

## SPECIFIC FIXES REQUIRED:
- If you see "FORBIDDEN_SYNTAX" errors: Replace `{{{{ 'key': value }}}}` with literal JSON
- If you see "INVALID_SOURCE" errors: Use only source names from v1_calls section
- If you see "MISSING_FIELD" errors: Add the required fields
- If you see "CONFLICTING_FIELDS" errors: Set v1_path to null when using transform

## GENERATE THE CORRECTED YAML CONFIGURATION NOW:
Fix all the errors identified above and regenerate the complete, valid YAML configuration.
"""

    return correction_prompt