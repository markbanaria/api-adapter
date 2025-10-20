import pytest
from adapter.response_builder import V2ResponseBuilder, ResponseBuilderError
from adapter.models import MappingConfig, EndpointConfig, V1ApiCall, FieldMapping


@pytest.fixture
def response_builder():
    return V2ResponseBuilder()


def test_set_nested_value_simple(response_builder):
    """Test setting a simple top-level value"""
    obj = {}
    response_builder._set_nested_value(obj, "name", "John Doe")

    assert obj == {"name": "John Doe"}


def test_set_nested_value_deep(response_builder):
    """Test setting a deeply nested value"""
    obj = {}
    response_builder._set_nested_value(obj, "insured.contact.email", "john@example.com")

    assert obj == {
        "insured": {
            "contact": {
                "email": "john@example.com"
            }
        }
    }


def test_set_nested_value_multiple_fields(response_builder):
    """Test setting multiple nested values"""
    obj = {}
    response_builder._set_nested_value(obj, "insured.name", "John Doe")
    response_builder._set_nested_value(obj, "insured.age", 35)
    response_builder._set_nested_value(obj, "policy.number", "POL123")

    assert obj == {
        "insured": {
            "name": "John Doe",
            "age": 35
        },
        "policy": {
            "number": "POL123"
        }
    }


def test_set_nested_value_overwrite_existing(response_builder):
    """Test overwriting existing values"""
    obj = {"insured": {"name": "Old Name"}}
    response_builder._set_nested_value(obj, "insured.name", "New Name")
    response_builder._set_nested_value(obj, "insured.age", 30)

    assert obj == {
        "insured": {
            "name": "New Name",
            "age": 30
        }
    }


def test_set_nested_value_conflict_error(response_builder):
    """Test error when trying to create nested structure over non-dict"""
    obj = {"insured": "string_value"}

    with pytest.raises(ResponseBuilderError, match="is not a dict"):
        response_builder._set_nested_value(obj, "insured.name", "John")


def test_build_response_simple_mapping(response_builder):
    """Test building a simple V2 response"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_data", endpoint="/v1/data", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="policyNumber",
                source="get_data",
                v1_path="policy_num"
            ),
            FieldMapping(
                v2_path="status",
                source="get_data",
                v1_path="policy_status"
            )
        ]
    )

    v1_responses = {
        "get_data": {
            "policy_num": "POL12345",
            "policy_status": "active"
        }
    }

    result = response_builder.build_response(config, v1_responses)

    assert result == {
        "policyNumber": "POL12345",
        "status": "active"
    }


def test_build_response_nested_fields(response_builder):
    """Test building a V2 response with nested fields"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_policy", endpoint="/v1/policy", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="insured.name",
                source="get_policy",
                transform="{{ get_policy.first_name }} {{ get_policy.last_name }}"
            ),
            FieldMapping(
                v2_path="insured.age",
                source="get_policy",
                v1_path="customer_age"
            ),
            FieldMapping(
                v2_path="policy.number",
                source="get_policy",
                v1_path="policy_num"
            )
        ]
    )

    v1_responses = {
        "get_policy": {
            "first_name": "Jane",
            "last_name": "Smith",
            "customer_age": 42,
            "policy_num": "POL99999"
        }
    }

    result = response_builder.build_response(config, v1_responses)

    assert result == {
        "insured": {
            "name": "Jane Smith",
            "age": 42
        },
        "policy": {
            "number": "POL99999"
        }
    }


def test_build_response_multiple_v1_sources(response_builder):
    """Test building V2 response from multiple V1 sources"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_policy", endpoint="/v1/policy", method="GET"),
            V1ApiCall(name="get_coverage", endpoint="/v1/coverage", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="policyNumber",
                source="get_policy",
                v1_path="policy_num"
            ),
            FieldMapping(
                v2_path="coverageAmount",
                source="get_coverage",
                v1_path="amount"
            ),
            FieldMapping(
                v2_path="coverageType",
                source="get_coverage",
                v1_path="type"
            )
        ]
    )

    v1_responses = {
        "get_policy": {
            "policy_num": "POL12345"
        },
        "get_coverage": {
            "amount": 500000,
            "type": "whole_life"
        }
    }

    result = response_builder.build_response(config, v1_responses)

    assert result == {
        "policyNumber": "POL12345",
        "coverageAmount": 500000,
        "coverageType": "whole_life"
    }


def test_build_response_with_stub(response_builder):
    """Test building V2 response with stub field"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_policy", endpoint="/v1/policy", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="policyNumber",
                source="get_policy",
                v1_path="policy_num"
            ),
            FieldMapping(
                v2_path="digitalSignatureUrl",
                source="stub",
                stub_value=None,
                stub_type="null"
            )
        ]
    )

    v1_responses = {
        "get_policy": {
            "policy_num": "POL12345"
        }
    }

    result = response_builder.build_response(config, v1_responses)

    assert result == {
        "policyNumber": "POL12345",
        "digitalSignatureUrl": None
    }


def test_build_response_with_missing_v1_field(response_builder):
    """Test building V2 response with missing V1 field (should be None)"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_data", endpoint="/v1/data", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="policyNumber",
                source="get_data",
                v1_path="policy_num"
            ),
            FieldMapping(
                v2_path="optionalField",
                source="get_data",
                v1_path="missing_field"
            )
        ]
    )

    v1_responses = {
        "get_data": {
            "policy_num": "POL12345"
            # missing_field is not present
        }
    }

    result = response_builder.build_response(config, v1_responses)

    assert result == {
        "policyNumber": "POL12345",
        "optionalField": None
    }


def test_build_response_transformation_error(response_builder):
    """Test that transformation errors are handled"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_data", endpoint="/v1/data", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="computed",
                source="get_data",
                transform="{{ get_data.nonexistent_field }}"
            )
        ]
    )

    v1_responses = {
        "get_data": {"other_field": "value"}
    }

    with pytest.raises(ResponseBuilderError, match="Failed to map required field"):
        response_builder.build_response(config, v1_responses)


def test_build_response_complex_nested_structure(response_builder):
    """Test building complex nested structure"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_policy", endpoint="/v1/policy", method="GET"),
            V1ApiCall(name="get_customer", endpoint="/v1/customer", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="policy.number",
                source="get_policy",
                v1_path="policy_num"
            ),
            FieldMapping(
                v2_path="policy.type",
                source="get_policy",
                v1_path="policy_type"
            ),
            FieldMapping(
                v2_path="insured.personal.name",
                source="get_customer",
                transform="{{ get_customer.first_name }} {{ get_customer.last_name }}"
            ),
            FieldMapping(
                v2_path="insured.personal.age",
                source="get_customer",
                v1_path="age"
            ),
            FieldMapping(
                v2_path="insured.contact.email",
                source="get_customer",
                v1_path="email"
            ),
            FieldMapping(
                v2_path="insured.contact.phone",
                source="get_customer",
                v1_path="phone"
            )
        ]
    )

    v1_responses = {
        "get_policy": {
            "policy_num": "POL12345",
            "policy_type": "whole_life"
        },
        "get_customer": {
            "first_name": "John",
            "last_name": "Doe",
            "age": 35,
            "email": "john@example.com",
            "phone": "+1234567890"
        }
    }

    result = response_builder.build_response(config, v1_responses)

    assert result == {
        "policy": {
            "number": "POL12345",
            "type": "whole_life"
        },
        "insured": {
            "personal": {
                "name": "John Doe",
                "age": 35
            },
            "contact": {
                "email": "john@example.com",
                "phone": "+1234567890"
            }
        }
    }


def test_build_response_arithmetic_transformation(response_builder):
    """Test response building with arithmetic transformation"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_policy", endpoint="/v1/policy", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="policyNumber",
                source="get_policy",
                v1_path="policy_num"
            ),
            FieldMapping(
                v2_path="annualPremium",
                source="get_policy",
                transform="{{ get_policy.monthly_premium * 12 }}"
            )
        ]
    )

    v1_responses = {
        "get_policy": {
            "policy_num": "POL12345",
            "monthly_premium": 150
        }
    }

    result = response_builder.build_response(config, v1_responses)

    assert result == {
        "policyNumber": "POL12345",
        "annualPremium": 1800
    }


def test_build_response_array_values(response_builder):
    """Test building response with array values"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_policy", endpoint="/v1/policy", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="policyNumber",
                source="get_policy",
                v1_path="policy_num"
            ),
            FieldMapping(
                v2_path="beneficiaries",
                source="get_policy",
                v1_path="beneficiary_list"
            )
        ]
    )

    v1_responses = {
        "get_policy": {
            "policy_num": "POL12345",
            "beneficiary_list": [
                {"name": "Jane Doe", "relationship": "spouse"},
                {"name": "John Jr", "relationship": "child"}
            ]
        }
    }

    result = response_builder.build_response(config, v1_responses)

    assert result == {
        "policyNumber": "POL12345",
        "beneficiaries": [
            {"name": "Jane Doe", "relationship": "spouse"},
            {"name": "John Jr", "relationship": "child"}
        ]
    }


def test_build_response_empty_config(response_builder):
    """Test building response with no field mappings"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_data", endpoint="/v1/data", method="GET")
        ],
        field_mappings=[
            # This is required to be non-empty, so we'll add a minimal mapping
            FieldMapping(v2_path="placeholder", source="get_data", v1_path="any")
        ]
    )

    v1_responses = {
        "get_data": {"any": "value"}
    }

    result = response_builder.build_response(config, v1_responses)

    assert result == {"placeholder": "value"}


def test_build_response_boolean_values(response_builder):
    """Test building response with boolean values"""
    config = MappingConfig(
        version="1.0",
        endpoint=EndpointConfig(v2_path="/api/v2/test", v2_method="GET"),
        v1_calls=[
            V1ApiCall(name="get_policy", endpoint="/v1/policy", method="GET")
        ],
        field_mappings=[
            FieldMapping(
                v2_path="isActive",
                source="get_policy",
                transform="{{ 'true' if get_policy.status == 'active' else 'false' }}"
            ),
            FieldMapping(
                v2_path="isPremium",
                source="get_policy",
                v1_path="premium_flag"
            )
        ]
    )

    v1_responses = {
        "get_policy": {
            "status": "active",
            "premium_flag": True
        }
    }

    result = response_builder.build_response(config, v1_responses)

    assert result == {
        "isActive": True,  # Type coercion converts "true" to boolean
        "isPremium": True
    }