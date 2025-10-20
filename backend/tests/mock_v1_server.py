from fastapi import FastAPI, HTTPException
from typing import Optional

# Mock V1 API for testing
mock_v1_app = FastAPI(title="Mock V1 API", description="Mock V1 Insurance API for testing")


@mock_v1_app.get("/api/v1/policy/{id}")
async def get_policy(id: str):
    """Mock policy endpoint"""
    if id == "INVALID":
        raise HTTPException(status_code=404, detail="Policy not found")

    return {
        "policy_num": id,
        "policy_status": "active",
        "first_name": "John",
        "last_name": "Doe",
        "policy_details": {
            "type": "whole_life",
            "premium_amount": 500
        }
    }


@mock_v1_app.get("/api/v1/policy")
async def get_policy_by_param(policy_id: str):
    """Mock policy by query param"""
    return {
        "policy_num": policy_id,
        "policy_status": "active",
        "policy_type": "whole_life"
    }


@mock_v1_app.get("/api/v1/customer/{customerId}")
async def get_customer(customerId: str):
    """Mock customer endpoint"""
    if customerId == "INVALID":
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "first_name": "Jane",
        "last_name": "Smith",
        "customer_age": 42,
        "email_address": "jane@example.com"
    }


@mock_v1_app.get("/api/v1/coverage")
async def get_coverage(policy_id: str):
    """Mock coverage endpoint"""
    return {
        "amount": 500000,
        "type": "whole_life"
    }


@mock_v1_app.get("/api/v1/coverage/{id}")
async def get_coverage_by_id(id: str):
    """Mock coverage by path param"""
    return {
        "amount": 1000000,
        "type": "term_life"
    }


@mock_v1_app.get("/api/v1/beneficiaries")
async def get_beneficiaries(policy_id: str):
    """Mock beneficiaries endpoint"""
    return [
        {"beneficiary_name": "Alice Doe", "relation": "spouse"},
        {"beneficiary_name": "Bob Doe", "relation": "child"}
    ]


@mock_v1_app.get("/api/v1/policy/search")
async def search_policies(
    customer_id: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None
):
    """Mock policy search endpoint"""
    return [
        {"policy_num": "POL001", "policy_type": "whole_life"},
        {"policy_num": "POL002", "policy_type": "term_life"}
    ]


@mock_v1_app.get("/health")
async def health_check():
    """Health check endpoint for mock V1 API"""
    return {"status": "healthy", "service": "mock-v1-api"}


@mock_v1_app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Mock V1 Insurance API",
        "version": "1.0",
        "endpoints": [
            "/api/v1/policy/{id}",
            "/api/v1/policy?policy_id={id}",
            "/api/v1/customer/{customerId}",
            "/api/v1/coverage?policy_id={id}",
            "/api/v1/coverage/{id}",
            "/api/v1/beneficiaries?policy_id={id}",
            "/api/v1/policy/search"
        ]
    }