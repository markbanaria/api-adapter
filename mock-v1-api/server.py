#!/usr/bin/env python3
"""
Mock V1 API Server for Demo
Provides sample insurance API endpoints that the V2 adapter will orchestrate
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Dict, Any, List

app = FastAPI(
    title="Insurance V1 API (Mock)",
    description="Mock V1 API endpoints for demonstration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample data
POLICIES = {
    "12345": {
        "policy_num": "POL-12345",
        "policy_status": "active",
        "customer_id": "CUST-001",
        "policy_type": "life",
        "created_date": "2023-01-15"
    },
    "67890": {
        "policy_num": "POL-67890",
        "policy_status": "pending",
        "customer_id": "CUST-002",
        "policy_type": "auto",
        "created_date": "2023-02-20"
    }
}

COVERAGE_DATA = {
    "12345": {
        "policy_id": "12345",
        "amount": 500000,
        "premium_amount": 2500,
        "coverage_type": "life",
        "deductible": 0
    },
    "67890": {
        "policy_id": "67890",
        "amount": 25000,
        "premium_amount": 1200,
        "coverage_type": "collision",
        "deductible": 500
    }
}

BENEFICIARIES_DATA = {
    "12345": [
        {
            "policy_id": "12345",
            "beneficiary_name": "Jane Doe",
            "relation": "spouse",
            "percentage": 60
        },
        {
            "policy_id": "12345",
            "beneficiary_name": "John Doe Jr",
            "relation": "child",
            "percentage": 40
        }
    ],
    "67890": [
        {
            "policy_id": "67890",
            "beneficiary_name": "Mary Smith",
            "relation": "spouse",
            "percentage": 100
        }
    ]
}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Insurance V1 API (Mock)",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "GET /api/v1/policy/{id}",
            "GET /api/v1/coverage",
            "GET /api/v1/beneficiaries"
        ]
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/api/v1/policy/{policy_id}")
async def get_policy(policy_id: str):
    """Get policy details by ID"""
    print(f"V1 API: Getting policy {policy_id}")

    if policy_id not in POLICIES:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy = POLICIES[policy_id]
    print(f"V1 API: Returning policy data: {policy}")
    return policy

@app.get("/api/v1/coverage")
async def get_coverage(policy_id: str = Query(..., description="Policy ID")):
    """Get coverage details by policy ID"""
    print(f"V1 API: Getting coverage for policy {policy_id}")

    if policy_id not in COVERAGE_DATA:
        raise HTTPException(status_code=404, detail="Coverage not found")

    coverage = COVERAGE_DATA[policy_id]
    print(f"V1 API: Returning coverage data: {coverage}")
    return coverage

@app.get("/api/v1/beneficiaries")
async def get_beneficiaries(policy_id: str = Query(..., description="Policy ID")):
    """Get beneficiaries by policy ID"""
    print(f"V1 API: Getting beneficiaries for policy {policy_id}")

    if policy_id not in BENEFICIARIES_DATA:
        return []  # No beneficiaries found, return empty list

    beneficiaries = BENEFICIARIES_DATA[policy_id]
    print(f"V1 API: Returning {len(beneficiaries)} beneficiaries")
    return beneficiaries

if __name__ == "__main__":
    print("🚀 Starting Mock V1 Insurance API on http://localhost:8001")
    print("📚 API Documentation: http://localhost:8001/docs")
    print("❤️  Health check: http://localhost:8001/health")
    print("")
    print("Available endpoints:")
    print("  GET /api/v1/policy/{id} - Get policy details")
    print("  GET /api/v1/coverage?policy_id={id} - Get coverage details")
    print("  GET /api/v1/beneficiaries?policy_id={id} - Get beneficiaries")
    print("")
    print("Sample data available for policy IDs: 12345, 67890")
    print("=" * 50)

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )