import pytest
from adapter.transformer import FieldTransformer, TransformationError
from adapter.models import FieldMapping


@pytest.fixture
def transformer():
    return FieldTransformer()


def test_simple_field_combination(transformer):
    """Test combining two fields with a space"""
    context = {
        "get_policy": {
            "firstName": "John",
            "lastName": "Doe"
        }
    }

    result = transformer.transform(
        "{{ get_policy.firstName }} {{ get_policy.lastName }}",
        context,
        "insured.name"
    )

    assert result == "John Doe"


def test_arithmetic_transformation(transformer):
    """Test simple arithmetic"""
    context = {
        "get_policy": {
            "monthly_premium": 100
        }
    }

    result = transformer.transform(
        "{{ get_policy.monthly_premium * 12 }}",
        context,
        "premium.annual"
    )

    assert result == 1200


def test_conditional_transformation(transformer):
    """Test if-else conditional"""
    context = {
        "get_policy": {
            "status": 1
        }
    }

    result = transformer.transform(
        "{{ 'active' if get_policy.status == 1 else 'inactive' }}",
        context,
        "policyStatus"
    )

    assert result == "active"


def test_conditional_transformation_false_case(transformer):
    """Test if-else conditional - false case"""
    context = {
        "get_policy": {
            "status": 0
        }
    }

    result = transformer.transform(
        "{{ 'active' if get_policy.status == 1 else 'inactive' }}",
        context,
        "policyStatus"
    )

    assert result == "inactive"


def test_nested_object_access(transformer):
    """Test accessing nested objects"""
    data = {
        "policy": {
            "details": {
                "type": "whole_life"
            }
        }
    }

    result = transformer.get_nested_value(data, "policy.details.type")
    assert result == "whole_life"


def test_missing_field_returns_none(transformer):
    """Test that missing nested fields return None"""
    data = {"policy": {"name": "Test"}}

    result = transformer.get_nested_value(data, "policy.details.type")
    assert result is None


def test_undefined_variable_error(transformer):
    """Test that undefined variables raise clear errors"""
    context = {"get_policy": {"name": "Test"}}

    with pytest.raises(TransformationError, match="Undefined variable"):
        transformer.transform(
            "{{ get_policy.nonexistent }}",
            context,
            "test_field"
        )


def test_apply_mapping_direct(transformer):
    """Test direct field mapping without transformation"""
    v1_responses = {
        "get_policy": {
            "policy_num": "POL12345"
        }
    }

    mapping = FieldMapping(
        v2_path="policyNumber",
        source="get_policy",
        v1_path="policy_num"
    )

    result = transformer.apply_mapping(v1_responses, mapping)
    assert result == "POL12345"


def test_apply_mapping_with_transform(transformer):
    """Test field mapping with transformation"""
    v1_responses = {
        "get_policy": {
            "first_name": "Jane",
            "last_name": "Smith"
        }
    }

    mapping = FieldMapping(
        v2_path="insured.name",
        source="get_policy",
        transform="{{ get_policy.first_name }} {{ get_policy.last_name }}"
    )

    result = transformer.apply_mapping(v1_responses, mapping)
    assert result == "Jane Smith"


def test_apply_mapping_stub(transformer):
    """Test stub field mapping"""
    v1_responses = {}

    mapping = FieldMapping(
        v2_path="digitalSignatureUrl",
        source="stub",
        stub_value=None,
        stub_type="null"
    )

    result = transformer.apply_mapping(v1_responses, mapping)
    assert result is None


def test_type_coercion_int(transformer):
    """Test automatic type coercion to int"""
    context = {"value": "42"}
    result = transformer.transform("{{ value }}", context)
    assert result == 42
    assert isinstance(result, int)


def test_type_coercion_float(transformer):
    """Test automatic type coercion to float"""
    context = {"value": "3.14"}
    result = transformer.transform("{{ value }}", context)
    assert result == 3.14
    assert isinstance(result, float)


def test_type_coercion_bool(transformer):
    """Test automatic type coercion to bool"""
    context = {"value": "true"}
    result = transformer.transform("{{ value }}", context)
    assert result is True
    assert isinstance(result, bool)


def test_type_coercion_bool_false(transformer):
    """Test automatic type coercion to bool - false case"""
    context = {"value": "false"}
    result = transformer.transform("{{ value }}", context)
    assert result is False
    assert isinstance(result, bool)


def test_no_type_coercion_for_non_strings(transformer):
    """Test that non-string values are not coerced"""
    context = {"value": 42}
    result = transformer.transform("{{ value }}", context)
    assert result == 42
    assert isinstance(result, int)


def test_string_stays_string(transformer):
    """Test that regular strings stay as strings"""
    context = {"value": "hello world"}
    result = transformer.transform("{{ value }}", context)
    assert result == "hello world"
    assert isinstance(result, str)


def test_complex_transformation_with_filters(transformer):
    """Test transformation with custom filters"""
    context = {
        "get_customer": {
            "name": "john doe"
        }
    }

    result = transformer.transform(
        "{{ get_customer.name | to_upper }}",
        context,
        "customerName"
    )

    assert result == "JOHN DOE"


def test_list_access_transformation(transformer):
    """Test accessing list elements in transformation"""
    context = {
        "get_beneficiaries": [
            {"beneficiary_name": "Jane Doe", "relation": "spouse"},
            {"beneficiary_name": "John Jr", "relation": "child"}
        ]
    }

    # Test accessing first beneficiary name
    result = transformer.transform(
        "{{ get_beneficiaries[0].beneficiary_name }}",
        context,
        "first_beneficiary"
    )

    assert result == "Jane Doe"


def test_missing_source_error(transformer):
    """Test error when V1 source is missing"""
    v1_responses = {
        "get_policy": {"name": "test"}
    }

    mapping = FieldMapping(
        v2_path="field",
        source="missing_source",
        v1_path="field"
    )

    with pytest.raises(TransformationError, match="not found in responses"):
        transformer.apply_mapping(v1_responses, mapping)


def test_missing_v1_path_and_transform(transformer):
    """Test error when both v1_path and transform are missing"""
    v1_responses = {
        "get_policy": {"name": "test"}
    }

    mapping = FieldMapping(
        v2_path="field",
        source="get_policy"
        # No v1_path or transform
    )

    with pytest.raises(TransformationError, match="has no v1_path and no transform"):
        transformer.apply_mapping(v1_responses, mapping)


def test_template_syntax_error(transformer):
    """Test handling of invalid Jinja2 syntax"""
    context = {"value": "test"}

    with pytest.raises(TransformationError, match="Invalid transformation syntax"):
        transformer.transform(
            "{{ unclosed_bracket",
            context,
            "test_field"
        )


def test_nested_value_with_non_dict(transformer):
    """Test get_nested_value with non-dict intermediate value"""
    data = {
        "policy": "not_a_dict"
    }

    result = transformer.get_nested_value(data, "policy.details.type")
    assert result is None


def test_empty_path_returns_data(transformer):
    """Test get_nested_value with empty path"""
    data = {"test": "value"}

    result = transformer.get_nested_value(data, "")
    assert result == {"test": "value"}


def test_single_key_path(transformer):
    """Test get_nested_value with single key"""
    data = {"test": "value"}

    result = transformer.get_nested_value(data, "test")
    assert result == "value"


def test_division_transformation(transformer):
    """Test division arithmetic"""
    context = {
        "get_policy": {
            "annual_premium": 1200
        }
    }

    result = transformer.transform(
        "{{ get_policy.annual_premium / 12 }}",
        context,
        "monthly_premium"
    )

    assert result == 100.0


def test_addition_transformation(transformer):
    """Test addition arithmetic"""
    context = {
        "get_policy": {
            "base_premium": 100,
            "addon_premium": 50
        }
    }

    result = transformer.transform(
        "{{ get_policy.base_premium + get_policy.addon_premium }}",
        context,
        "total_premium"
    )

    assert result == 150


def test_subtraction_transformation(transformer):
    """Test subtraction arithmetic"""
    context = {
        "get_policy": {
            "gross_premium": 150,
            "discount": 20
        }
    }

    result = transformer.transform(
        "{{ get_policy.gross_premium - get_policy.discount }}",
        context,
        "net_premium"
    )

    assert result == 130