# User Story 007: Sample OpenAPI Specs (Test Scenarios)

## Story
As a developer, I want sample V1 and V2 OpenAPI specifications for all test scenarios so that the config generator has realistic inputs to work with.

## Acceptance Criteria
- [ ] 7 V2 OpenAPI specs created (one per scenario)
- [ ] Complete V1 OpenAPI spec with all endpoints
- [ ] Specs are valid OpenAPI 3.0 format
- [ ] Specs cover all transformation patterns
- [ ] Specs stored in config-generator/specs/ directory
- [ ] Specs include life insurance and ILP domain models

## Technical Details

### Scenario Specs

#### Scenario 1: Simple Field Rename (config-generator/specs/v2/scenario1-simple-rename.json)

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Policy API V2",
    "version": "2.0.0"
  },
  "paths": {
    "/api/v2/policies/{policyId}": {
      "get": {
        "operationId": "getPolicy",
        "parameters": [
          {
            "name": "policyId",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "Policy details",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "policyNumber": {"type": "string"},
                    "status": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### Scenario 2: Field Combination (config-generator/specs/v2/scenario2-field-combination.json)

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Insured API V2",
    "version": "2.0.0"
  },
  "paths": {
    "/api/v2/insured/{customerId}": {
      "get": {
        "operationId": "getInsured",
        "parameters": [
          {
            "name": "customerId",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "Insured person details",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "fullName": {
                      "type": "string",
                      "description": "Full name of insured person"
                    },
                    "age": {"type": "integer"},
                    "email": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### Scenario 3: Query Param to Path Param (config-generator/specs/v2/scenario3-param-shift.json)

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Coverage API V2",
    "version": "2.0.0"
  },
  "paths": {
    "/api/v2/coverage/{policyId}": {
      "get": {
        "operationId": "getCoverage",
        "parameters": [
          {
            "name": "policyId",
            "in": "path",
            "required": true,
            "schema": {"type": "string"},
            "description": "Policy identifier"
          }
        ],
        "responses": {
          "200": {
            "description": "Coverage details",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "coverageAmount": {"type": "number"},
                    "coverageType": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### Scenario 4: Nested Object Flattening (config-generator/specs/v2/scenario4-flatten.json)

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Policy Summary API V2",
    "version": "2.0.0"
  },
  "paths": {
    "/api/v2/policy-summary/{policyId}": {
      "get": {
        "operationId": "getPolicySummary",
        "parameters": [
          {
            "name": "policyId",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "Flattened policy summary",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "policyNumber": {"type": "string"},
                    "policyType": {"type": "string"},
                    "premium": {"type": "number"},
                    "insuredName": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### Scenario 5: Multiple V1 Endpoints (config-generator/specs/v2/scenario5-multi-endpoint.json)

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Complete Policy API V2",
    "version": "2.0.0"
  },
  "paths": {
    "/api/v2/complete-policy/{policyId}": {
      "get": {
        "operationId": "getCompletePolicy",
        "parameters": [
          {
            "name": "policyId",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "Complete policy with coverage",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "policyNumber": {"type": "string"},
                    "status": {"type": "string"},
                    "coverageAmount": {"type": "number"},
                    "beneficiaries": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "name": {"type": "string"},
                          "relationship": {"type": "string"}
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### Scenario 6: Body to Query Param (config-generator/specs/v2/scenario6-body-to-query.json)

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Policy Search API V2",
    "version": "2.0.0"
  },
  "paths": {
    "/api/v2/policies/search": {
      "post": {
        "operationId": "searchPolicies",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "customerId": {"type": "string"},
                  "policyType": {"type": "string"},
                  "status": {"type": "string"}
                }
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "List of matching policies",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "policyNumber": {"type": "string"},
                      "policyType": {"type": "string"}
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### Scenario 7: Unmappable Field (Stub) (config-generator/specs/v2/scenario7-stub.json)

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Enhanced Policy API V2",
    "version": "2.0.0"
  },
  "paths": {
    "/api/v2/enhanced-policy/{policyId}": {
      "get": {
        "operationId": "getEnhancedPolicy",
        "parameters": [
          {
            "name": "policyId",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "Enhanced policy with digital features",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "policyNumber": {"type": "string"},
                    "status": {"type": "string"},
                    "digitalSignatureUrl": {
                      "type": "string",
                      "nullable": true,
                      "description": "URL to digital signature (not available in V1)"
                    },
                    "mobileAppDeepLink": {
                      "type": "string",
                      "nullable": true,
                      "description": "Deep link to mobile app (not available in V1)"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### Complete V1 Spec (config-generator/specs/v1/complete-v1-api.json)

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Legacy Insurance API V1",
    "version": "1.0.0",
    "description": "Legacy API for life insurance and ILP products"
  },
  "paths": {
    "/api/v1/policy/{id}": {
      "get": {
        "operationId": "getPolicy_v1",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "Policy details",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "policy_num": {"type": "string"},
                    "policy_status": {"type": "string"},
                    "policy_details": {
                      "type": "object",
                      "properties": {
                        "type": {"type": "string"},
                        "premium_amount": {"type": "number"}
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/policy": {
      "get": {
        "operationId": "getPolicyByParam",
        "parameters": [
          {
            "name": "policy_id",
            "in": "query",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "Policy details",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "policy_num": {"type": "string"},
                    "policy_status": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/customer/{customerId}": {
      "get": {
        "operationId": "getCustomer_v1",
        "parameters": [
          {
            "name": "customerId",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "Customer details",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "customer_age": {"type": "integer"},
                    "email_address": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/coverage": {
      "get": {
        "operationId": "getCoverage_v1",
        "parameters": [
          {
            "name": "policy_id",
            "in": "query",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "Coverage details",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "amount": {"type": "number"},
                    "type": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/coverage/{id}": {
      "get": {
        "operationId": "getCoverageById_v1",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "Coverage details",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "amount": {"type": "number"},
                    "type": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/beneficiaries": {
      "get": {
        "operationId": "getBeneficiaries_v1",
        "parameters": [
          {
            "name": "policy_id",
            "in": "query",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "List of beneficiaries",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "beneficiary_name": {"type": "string"},
                      "relation": {"type": "string"}
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/policy/search": {
      "get": {
        "operationId": "searchPolicies_v1",
        "parameters": [
          {
            "name": "customer_id",
            "in": "query",
            "schema": {"type": "string"}
          },
          {
            "name": "type",
            "in": "query",
            "schema": {"type": "string"}
          },
          {
            "name": "status",
            "in": "query",
            "schema": {"type": "string"}
          }
        ],
        "responses": {
          "200": {
            "description": "Matching policies",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "policy_num": {"type": "string"},
                      "policy_type": {"type": "string"}
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

## Testing Checklist
- [ ] All V2 specs are valid OpenAPI 3.0
- [ ] V1 spec is valid OpenAPI 3.0
- [ ] All scenarios represented
- [ ] Specs include realistic insurance domain models
- [ ] Parameter types correctly specified
- [ ] Response schemas defined

## Definition of Done
- 7 V2 scenario specs created
- 1 complete V1 spec created
- All specs validated as valid OpenAPI 3.0
- Specs stored in correct directory structure
- README documenting each scenario