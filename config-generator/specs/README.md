# OpenAPI Specifications for Insurance API Adapter

This directory contains OpenAPI 3.0 specifications for testing the V1→V2 insurance API adapter.

## V1 Specification

### complete-v1-api.json
The complete legacy V1 API specification containing all endpoints used by the existing insurance system. This includes:
- Policy management endpoints (path and query parameter variations)
- Customer information endpoints
- Coverage details endpoints
- Beneficiary management
- Policy search functionality

## V2 Scenarios

Each V2 specification represents a different transformation scenario that the adapter must handle:

### Scenario 1: Simple Field Rename (scenario1-simple-rename.json)
- **Transformation**: Direct field mapping with name changes
- **Example**: `policy_num` → `policyNumber`, `policy_status` → `status`
- **V1 Endpoint**: `/api/v1/policy/{id}`
- **V2 Endpoint**: `/api/v2/policies/{policyId}`

### Scenario 2: Field Combination (scenario2-field-combination.json)
- **Transformation**: Combining multiple V1 fields into single V2 field
- **Example**: `first_name` + `last_name` → `fullName`
- **V1 Endpoint**: `/api/v1/customer/{customerId}`
- **V2 Endpoint**: `/api/v2/insured/{customerId}`

### Scenario 3: Query to Path Parameter (scenario3-param-shift.json)
- **Transformation**: Converting V1 query parameters to V2 path parameters
- **Example**: `?policy_id=123` → `/coverage/123`
- **V1 Endpoint**: `/api/v1/coverage?policy_id={id}`
- **V2 Endpoint**: `/api/v2/coverage/{policyId}`

### Scenario 4: Nested Object Flattening (scenario4-flatten.json)
- **Transformation**: Extracting nested V1 fields to flat V2 structure
- **Example**: `policy_details.type` → `policyType`, `policy_details.premium_amount` → `premium`
- **V1 Endpoint**: `/api/v1/policy/{id}`
- **V2 Endpoint**: `/api/v2/policy-summary/{policyId}`

### Scenario 5: Multiple V1 Endpoints (scenario5-multi-endpoint.json)
- **Transformation**: Combining data from multiple V1 calls into single V2 response
- **Example**: Aggregate policy, coverage, and beneficiaries into one response
- **V1 Endpoints**:
  - `/api/v1/policy/{id}`
  - `/api/v1/coverage?policy_id={id}`
  - `/api/v1/beneficiaries?policy_id={id}`
- **V2 Endpoint**: `/api/v2/complete-policy/{policyId}`

### Scenario 6: Body to Query Parameter (scenario6-body-to-query.json)
- **Transformation**: Converting V1 GET with query params to V2 POST with body
- **Example**: Query parameters become JSON request body fields
- **V1 Endpoint**: `/api/v1/policy/search?customer_id=&type=&status=`
- **V2 Endpoint**: `/api/v2/policies/search` (POST)

### Scenario 7: Unmappable Field Stub (scenario7-stub.json)
- **Transformation**: V2 fields with no V1 equivalent return null/default values
- **Example**: `digitalSignatureUrl` and `mobileAppDeepLink` (null stubs)
- **V1 Endpoint**: `/api/v1/policy/{id}`
- **V2 Endpoint**: `/api/v2/enhanced-policy/{policyId}`

## Usage

These specifications are used by:
1. **Config Generator**: As input to the Qwen 7B model for generating transformation configurations
2. **Testing**: To validate that the adapter correctly handles all transformation scenarios
3. **Documentation**: As reference for understanding the API evolution

## Validation

All specs are valid OpenAPI 3.0 format and can be validated using:
```bash
npx @apidevtools/swagger-cli validate specs/v1/complete-v1-api.json
npx @apidevtools/swagger-cli validate specs/v2/scenario*.json
```

## Insurance Domain Model

The specifications model a typical life insurance and Investment-Linked Policy (ILP) system with:
- Policy management (numbers, status, types)
- Customer/Insured information
- Coverage details (amounts, types)
- Beneficiary management
- Premium tracking
- Digital features (mobile app integration, e-signatures)