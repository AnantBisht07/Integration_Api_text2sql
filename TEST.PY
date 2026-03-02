#!/usr/bin/env python3
"""
Test ComposeIO Direct Connection
Bypasses the backend to see what ComposeIO actually returns
"""

import requests
import json

def test_composeio_direct():
    """Test ComposeIO connection endpoint directly"""
    
    print("=" * 70)
    print("🔍 Testing ComposeIO Connection Endpoint Directly")
    print("=" * 70)
    
    # Step 1: Login to OA Web to get accessToken
    print("\n📍 Step 1: Login to OA Web")
    
    oa_web_url = "https://web.openanalyst.com/api/v1/userAccount/authenticate"
    auth_payload = {
        "email": "deepak.c@openanalyst.com",
        "method": "password",
        "credentials": {"password": "Deepak1234@"}
    }
    
    session = requests.Session()
    auth_response = session.post(oa_web_url, json=auth_payload, timeout=10)
    
    print(f"   Status: {auth_response.status_code}")
    
    if auth_response.status_code != 200:
        print(f"   ❌ Login failed: {auth_response.text}")
        return
    
    auth_data = auth_response.json()
    access_token = auth_data.get("accessToken") or auth_data.get("access_token")
    
    print(f"   ✅ Got OA Web accessToken")
    print(f"   Token: {access_token[:50]}...")
    
    # Step 2: Verify with /me
    print("\n📍 Step 2: Verify with /me endpoint")
    
    me_url = "https://web.openanalyst.com/api/v1/userAccount/me"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-auth-source": "desktop",
        "Content-Type": "application/json"
    }
    
    me_response = session.get(me_url, headers=headers, timeout=10)
    
    print(f"   Status: {me_response.status_code}")
    
    if me_response.status_code == 200:
        user_data = me_response.json()
        user_id = user_data.get("userId") or user_data.get("user_id") or user_data.get("id")
        org_id = user_data.get("orgId") or user_data.get("org_id")
        email = user_data.get("email")
        
        print(f"   ✅ User verified")
        print(f"   userId: {user_id}")
        print(f"   orgId: {org_id}")
        print(f"   email: {email}")
    else:
        print(f"   ❌ Verification failed: {me_response.text}")
        return
    
    # Step 3: Call ComposeIO /api/integrations/connect
    print("\n📍 Step 3: Call ComposeIO Connect Endpoint")
    
    composeio_url = "https://api.openanalyst.com/integrations/api/integrations/connect"
    
    composeio_headers = {
        "Authorization": f"Bearer {access_token}",
        "x-auth-source": "desktop",
        "Content-Type": "application/json"
    }
    
    composeio_payload = {
        "provider": "gmail",
        "redirect_url": "https://web.openanalyst.com/callback"
    }
    
    print(f"   URL: {composeio_url}")
    print(f"   Payload: {json.dumps(composeio_payload, indent=2)}")
    
    composeio_response = session.post(
        composeio_url,
        headers=composeio_headers,
        json=composeio_payload,
        timeout=10
    )
    
    print(f"   Status: {composeio_response.status_code}")
    print(f"   Response:")
    print(json.dumps(composeio_response.json(), indent=2))
    
    composeio_data = composeio_response.json()
    
    # Step 4: Check if already_connected
    if composeio_data.get("status") == "already_connected":
        print("\n📍 Step 4: Detected 'already_connected' status")
        print("   ⚠️ But no credentials to actually USE the connection!")
        print("   \n   This is the PROBLEM:")
        print("   • ComposeIO says 'already_connected'")
        print("   • But doesn't provide a token/entityId to fetch data")
        print("   • We need to query ComposeIO for the connection details")
        
        # Try to get connection details
        print("\n📍 Step 5: Try to get connection details")
        
        status_url = "https://api.openanalyst.com/integrations/api/integrations/gmail/status"
        
        status_response = session.get(status_url, headers=composeio_headers, timeout=10)
        
        print(f"   URL: {status_url}")
        print(f"   Status: {status_response.status_code}")
        print(f"   Response:")
        print(status_response.text)
        
        # Try to get connected integrations list
        print("\n📍 Step 6: Get connected integrations")
        
        connected_url = "https://api.openanalyst.com/integrations/api/integrations/connected"
        
        connected_response = session.get(connected_url, headers=composeio_headers, timeout=10)
        
        print(f"   URL: {connected_url}")
        print(f"   Status: {connected_response.status_code}")
        print(f"   Response:")
        print(connected_response.text)
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_composeio_direct()