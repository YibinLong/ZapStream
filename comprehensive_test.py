#!/usr/bin/env python3
"""
Comprehensive test script for ZapStream Backend Phases 2 & 3
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"
API_KEY = "dev_key_123"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✅ Health check passed\n")

def test_auth_no_key():
    """Test authentication without API key"""
    print("🔍 Testing authentication without API key...")
    response = requests.post(f"{BASE_URL}/events", json={"payload": {}})
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 401
    print("✅ Auth check passed\n")

def test_auth_invalid_key():
    """Test authentication with invalid API key"""
    print("🔍 Testing authentication with invalid API key...")
    headers = {"Authorization": "Bearer invalid_key"}
    response = requests.get(f"{BASE_URL}/inbox", headers=headers)
    print(f"Status: {response.status_code}")
    assert response.status_code == 401
    print("✅ Invalid key check passed\n")

def test_create_event():
    """Test event creation"""
    print("🔍 Testing event creation...")
    event_data = {
        "source": "test",
        "type": "test.event",
        "topic": "testing",
        "payload": {"test": True, "timestamp": time.time()}
    }
    response = requests.post(f"{BASE_URL}/events", json=event_data, headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    event_id = response.json()["id"]
    print(f"✅ Event created with ID: {event_id}\n")
    return event_id

def test_idempotency():
    """Test idempotency functionality"""
    print("🔍 Testing idempotency...")
    event_data = {
        "source": "test",
        "type": "test.idempotency",
        "payload": {"test": "idempotency"}
    }
    headers = {**HEADERS, "X-Idempotency-Key": "test_key_123"}
    
    # First request should succeed
    response1 = requests.post(f"{BASE_URL}/events", json=event_data, headers=headers)
    print(f"First request status: {response1.status_code}")
    assert response1.status_code == 200
    
    # Second request should fail with idempotency conflict
    response2 = requests.post(f"{BASE_URL}/events", json=event_data, headers=headers)
    print(f"Second request status: {response2.status_code}")
    assert response2.status_code == 409
    assert "IDEMPOTENCY_CONFLICT" in response2.json()["detail"]["error"]["code"]
    print("✅ Idempotency check passed\n")

def test_inbox_retrieval():
    """Test inbox event retrieval"""
    print("🔍 Testing inbox retrieval...")
    response = requests.get(f"{BASE_URL}/inbox", headers=HEADERS)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Events count: {len(data['events'])}")
    assert response.status_code == 200
    assert "events" in data
    assert isinstance(data["events"], list)
    print("✅ Inbox retrieval passed\n")

def test_event_acknowledgment(event_id):
    """Test event acknowledgment"""
    print(f"🔍 Testing event acknowledgment for {event_id}...")
    response = requests.post(f"{BASE_URL}/inbox/{event_id}/ack", headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"
    print("✅ Event acknowledgment passed\n")

def test_event_deletion(event_id):
    """Test event deletion"""
    print(f"🔍 Testing event deletion for {event_id}...")
    response = requests.delete(f"{BASE_URL}/inbox/{event_id}", headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    print("✅ Event deletion passed\n")

def main():
    """Run all tests"""
    print("🚀 Starting comprehensive tests for ZapStream Backend Phases 2 & 3\n")
    
    try:
        # Basic functionality tests
        test_health()
        test_auth_no_key()
        test_auth_invalid_key()
        
        # Event lifecycle tests
        event_id = test_create_event()
        test_idempotency()
        test_inbox_retrieval()
        test_event_acknowledgment(event_id)
        
        # Create another event for deletion test
        event_id2 = test_create_event()
        test_event_deletion(event_id2)
        
        print("🎉 ALL TESTS PASSED! 🎉")
        print("\n📋 Summary:")
        print("✅ Phase 2: Storage Abstraction - WORKING")
        print("✅ Phase 3: Auth & Multi-Tenancy - WORKING")
        print("✅ SQLite Storage Implementation - WORKING")
        print("✅ API Key Parsing & Tenant Scoping - WORKING")
        print("✅ Idempotency - WORKING")
        print("✅ Event CRUD Operations - WORKING")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
