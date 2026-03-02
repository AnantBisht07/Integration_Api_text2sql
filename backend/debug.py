#!/usr/bin/env python3
"""
Debug ComposeIO Connection Issues
Tests if user is actually connected to Gmail
"""

import requests
import json

def test_composeio_connection(access_token, provider="gmail"):
    """Test if ComposeIO recognizes the user's connection"""
    
    print("=" * 70)
    print("🔍 Testing ComposeIO Connection")
    print("=" * 70)
    
    # Test 1: Check integration status
    print("\n📍 Test 1: Check Integration Status")
    status_url = f"https://api.openanalyst.com/integrations/api/integrations/{provider}/status"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-auth-source": "desktop",
        "Content-Type": "application/json"
    }
    
    print(f"   URL: {status_url}")
    print(f"   Token: {access_token[:50]}...")
    
    response = requests.get(status_url, headers=headers, timeout=10)
    
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "active":
            print("   ✅ User IS connected to Gmail!")
        else:
            print(f"   ❌ User NOT connected. Status: {data.get('status')}")
    else:
        print(f"   ❌ API Error: {response.text}")
    
    # Test 2: Try to execute a tool
    print("\n📍 Test 2: Try Fetching Emails")
    execute_url = "https://api.openanalyst.com/integrations/api/tools/execute"
    
    payload = {
        "action": "GMAIL_FETCH_EMAILS",
        "params": {
            "q": "is:inbox",
            "max_results": 1
        }
    }
    
    print(f"   URL: {execute_url}")
    print(f"   Action: GMAIL_FETCH_EMAILS")
    
    response = requests.post(execute_url, headers=headers, json=payload, timeout=10)
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print("   ✅ Successfully fetched emails!")
            print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
        else:
            print(f"   ❌ Execution failed: {data.get('error')}")
            print(f"   Full response: {json.dumps(data, indent=2)}")
    else:
        print(f"   ❌ API Error: {response.text}")
    
    # Test 3: List connected integrations
    print("\n📍 Test 3: List Connected Integrations")
    connected_url = "https://api.openanalyst.com/integrations/api/integrations/connected"
    
    response = requests.get(connected_url, headers=headers, timeout=10)
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        integrations = data.get("integrations", [])
        
        print(f"   Total connected: {len(integrations)}")
        
        for integration in integrations:
            provider_name = integration.get("provider")
            status = integration.get("status")
            connected_email = integration.get("connected_email", "N/A")
            
            print(f"   • {provider_name}: {status} ({connected_email})")
        
        # Check if Gmail is in the list
        gmail_connected = any(i.get("provider") == "gmail" for i in integrations)
        
        if gmail_connected:
            print(f"   ✅ Gmail IS in connected integrations list!")
        else:
            print(f"   ❌ Gmail NOT in connected integrations list!")
    else:
        print(f"   ❌ API Error: {response.text}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 debug_composeio.py <accessToken>")
        print("\nExample:")
        print("python3 debug_composeio.py eyJhbGci...")
        sys.exit(1)
    
    access_token = sys.argv[1]
    provider = sys.argv[2] if len(sys.argv) > 2 else "gmail"
    
    test_composeio_connection(access_token, provider)       