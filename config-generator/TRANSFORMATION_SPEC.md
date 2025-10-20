# API Mapping Configuration Specification

## CRITICAL: Complete Field Mapping Required
- Map ALL fields from the V2 response schema
- Use multiple V1 calls to gather data (getPolicy_v1, getCoverage_v1, getBeneficiaries_v1)
- Only use stubs when NO V1 data exists for a field

## Field Mapping Rules

### Basic Field Mapping
```yaml
# Direct field mapping (no transformation)
- v2_path: .policyNumber
  source: getPolicy_v1
  v1_path: .policy_num
  transform: null
```

### Transform Field Mapping
```yaml
# When using transform, v1_path MUST be null
- v2_path: .beneficiaries
  source: getBeneficiaries_v1
  v1_path: null
  transform: "{{ jinja2_expression }}"
```

## Parameter Mapping Format

### V2 Path Parameter → V1 Query Parameter
```yaml
# V2: /api/v2/policy/{policyId}
# V1: /api/v1/coverage?policy_id=...
params:
  query:
    - v2_param: policyId      # Exact V2 parameter name
      v1_param: policy_id     # V1 parameter name
      location: path          # Where policyId comes FROM in V2
```

### V2 Path Parameter → V1 Path Parameter
```yaml
# V2: /api/v2/policy/{policyId}
# V1: /api/v1/policy/{id}
params:
  path:
    - v2_param: policyId
      v1_param: id
      location: path
```

## Stub Types (Only when NO V1 data exists)

### Valid stub_type Values
```yaml
# For null values
stub_type: "null"
stub_value: null

# For empty strings
stub_type: "empty_string"
stub_value: ""

# For empty arrays
stub_type: "empty_array"
stub_value: []

# For configurable defaults
stub_type: "configurable_default"
stub_value: "DEFAULT_VALUE"
```

## Source Field Rules

### CRITICAL: Source Format
```yaml
# ✅ CORRECT - Only call name
source: getPolicy_v1

# ❌ WRONG - Never include field paths
source: getPolicy_v1.policy_num
```

## Complete Configuration Template - Insurance Policy Example

```yaml
version: "1.0"
endpoint:
  v2_path: /api/v2/complete-policy/{policyId}
  v2_method: GET

v1_calls:
  - name: getPolicy_v1
    endpoint: /api/v1/policy/{id}
    method: GET
    params:
      path:
        - v2_param: policyId
          v1_param: id
          location: path

  - name: getCoverage_v1
    endpoint: /api/v1/coverage
    method: GET
    params:
      query:
        - v2_param: policyId
          v1_param: policy_id
          location: path

  - name: getBeneficiaries_v1
    endpoint: /api/v1/beneficiaries
    method: GET
    params:
      query:
        - v2_param: policyId
          v1_param: policy_id
          location: path

field_mappings:
  # Direct field mappings from policy data
  - v2_path: .policyNumber
    source: getPolicy_v1
    v1_path: .policy_num
    transform: null

  - v2_path: .status
    source: getPolicy_v1
    v1_path: .policy_status
    transform: null

  - v2_path: .premiumAmount
    source: getPolicy_v1
    v1_path: .premium_amount
    transform: null

  # Coverage data
  - v2_path: .coverageAmount
    source: getCoverage_v1
    v1_path: .amount
    transform: null

  - v2_path: .coverageType
    source: getCoverage_v1
    v1_path: .type
    transform: null

  # Array transformation for beneficiaries
  - v2_path: .beneficiaries
    source: getBeneficiaries_v1
    v1_path: null
    transform: |
      [
        {% for item in source %}
        {
          "name": "{{ item.beneficiary_name }}",
          "relationship": "{{ item.relation }}"
        }{% if not loop.last %},{% endif %}
        {% endfor %}
      ]

  # Stub for fields with no V1 equivalent
  - v2_path: .fundValue
    source: stub
    stub_value: null
    stub_type: "null"

metadata:
  generated_at: "ISO_TIMESTAMP"
  confidence_score: 0.0-1.0
```

## Transformation Examples

### Array Transformation
```yaml
# Transform V1 array to V2 format - CORRECT JSON syntax
v1_path: null
transform: |
  [
    {% for item in source %}
    {
      "name": "{{ item.beneficiary_name }}",
      "relationship": "{{ item.relation }}"
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ]

# ❌ WRONG - This exact syntax causes "expected token 'end of print statement'" error
transform: '{%- for item in source -%}{{ ''name'': item.beneficiary_name, ''relationship'': item.relation }}{%- endfor -%}'

# ✅ CORRECT - Use proper JSON format with quoted strings
transform: |
  [
    {% for item in source %}
    {
      "name": "{{ item.beneficiary_name }}",
      "relationship": "{{ item.relation }}"
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ]
```

### String Concatenation
```yaml
# Combine multiple V1 fields
v1_path: null
transform: "{{ source.first_name }} {{ source.last_name }}"
```

### Conditional Mapping
```yaml
# Map based on V1 value
v1_path: null
transform: |
  {% if source.status == 'ACTIVE' %}
  "active"
  {% else %}
  "inactive"
  {% endif %}
```

## Validation Rules

1. **source** field MUST only contain V1 call names from v1_calls section
2. **v1_path** MUST be null when using transform, string otherwise
3. **stub_type** MUST be one of: "null", "empty_string", "empty_array", "configurable_default"
4. **v2_param** MUST exactly match V2 parameter names
5. **location** indicates where v2_param comes FROM in V2 API
6. **transforms** MUST use valid Jinja2 syntax with proper JSON format - NO dictionary syntax inside {{ }}

## Jinja2 Transform Syntax Rules - CRITICAL

- Use `{% %}` for control flow (for loops, if statements)
- Use `{{ }}` for variable output only - NEVER for object creation
- For JSON objects/arrays, write literal JSON with quoted keys
- NEVER use Python dict syntax like `{'key': value}` in transforms
- Always use double quotes for JSON strings
- NEVER use this pattern: `{{ 'key': value }}` - it will cause syntax errors

## BANNED PATTERNS - Will cause "expected token 'end of print statement'" error

```yaml
# ❌ ABSOLUTELY FORBIDDEN - This will fail
transform: '{%- for item in source -%}{{ ''name'': item.field, ''other'': item.other }}{%- endfor -%}'

# ❌ ALSO FORBIDDEN - Any object creation inside {{ }}
transform: '{{ ''key'': value }}'
transform: '{{ {''key'': ''value''} }}'
```

## REQUIRED PATTERN for objects/arrays

```yaml
# ✅ ONLY CORRECT WAY - Use literal JSON structure
transform: |
  [
    {% for item in source %}
    {
      "name": "{{ item.field }}",
      "other": "{{ item.other }}"
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ]
```