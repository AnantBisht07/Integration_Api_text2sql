# backend/auth.py
# COMPLETE FLOW WITH COMPOSEIO
# 1. Authenticate user → Get accessToken
# 2. Verify token with /me → Get userId/orgId
# 3. Generate JWT with INTEGRATION_MARKETPLACE_SECRET
# 4. Call ComposeIO to get connection link
# 5. Return ComposeIO auth_url

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import jwt as pyjwt
import os
from datetime import datetime, timedelta
import uuid
import requests

app = FastAPI(title="Integration Token API")

# Environment variables
JWT_SECRET = os.getenv('INTEGRATION_MARKETPLACE_SECRET')
OA_WEB_URL = os.getenv('OA_WEB_URL', 'https://web.openanalyst.com')
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'https://api.openanalyst.com/integrations')

class CredentialsRequest(BaseModel):
    email: str
    password: str
    provider: str = "gmail"  # gmail, slack, google_analytics, googledocs

@app.get("/")
async def root():
    return {
        "service": "OpenAnalyst Integration Token API",
        "status": "running",
        "version": "5.0.0 - ComposeIO Integration"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/auth/generate-integration-token")
async def generate_integration_token(credentials: CredentialsRequest):
    """
    Complete authentication and ComposeIO connection flow
    
    Steps:
    1. Authenticate with OA Web
    2. Verify token with /me endpoint
    3. Generate JWT with marketplace secret
    4. Call ComposeIO to get connection link
    5. Return auth_url for user to connect provider
    
    Request:
    {
        "email": "user@example.com",
        "password": "password123",
        "provider": "gmail"
    }
    
    Returns:
    {
        "success": true,
        "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
        "provider": "gmail",
        "user_data": {...}
    }
    """
    
    try:
        print(f"=" * 80)
        print(f"🚀 Starting ComposeIO connection flow")
        print(f"   User: {credentials.email}")
        print(f"   Provider: {credentials.provider}")
        print(f"=" * 80)
        
        # ================================================================
        # STEP 1: Authenticate with OA Web
        # ================================================================
        print(f"\n📍 STEP 1: Authenticating with OA Web")
        
        auth_url = f"{OA_WEB_URL}/api/v1/userAccount/authenticate"
        auth_payload = {
            "email": credentials.email,
            "method": "password",
            "credentials": {"password": credentials.password}
        }
        
        session = requests.Session()
        auth_response = session.post(auth_url, json=auth_payload, timeout=10)
        
        if auth_response.status_code != 200:
            print(f"   ❌ Authentication failed!")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        auth_data = auth_response.json()
        access_token = auth_data.get("accessToken") or auth_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=500, detail="No access token in response")
        
        print(f"   ✅ Authentication successful!")
        print(f"   Access token: {access_token[:50]}...")
        
        # ================================================================
        # STEP 2: Verify token with /me endpoint
        # ================================================================
        print(f"\n📍 STEP 2: Verifying token with /me endpoint")
        
        me_url = f"{OA_WEB_URL}/api/v1/userAccount/me"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-auth-source": "desktop",
            "Content-Type": "application/json"
        }
        
        me_response = session.get(me_url, headers=headers, timeout=10)
        
        if me_response.status_code != 200:
            print(f"   ❌ Token verification failed!")
            raise HTTPException(status_code=500, detail="Could not verify access token")
        
        user_data = me_response.json()
        
        user_id = user_data.get("userId") or user_data.get("user_id") or user_data.get("id")
        org_id = user_data.get("orgId") or user_data.get("org_id")
        email = user_data.get("email") or credentials.email
        full_name = user_data.get("fullName") or user_data.get("full_name") or "User"
        
        if not user_id:
            raise HTTPException(status_code=500, detail="Could not retrieve user ID")
        
        print(f"   ✅ Token verified!")
        print(f"   User ID: {user_id}")
        print(f"   Org ID: {org_id}")
        print(f"   Email: {email}")
        
        # ================================================================
        # STEP 3: Generate JWT with marketplace secret
        # ================================================================
        print(f"\n📍 STEP 3: Generating JWT for ComposeIO")
        
        # Generate JWT (60 second expiry as per docs)
        iat_time = datetime.utcnow() - timedelta(seconds=5)  # Backdate for clock skew
        exp_time = datetime.utcnow() + timedelta(seconds=60)  # 60 second expiry
        
        jwt_payload = {
            "user_id": user_id,
            "email": email,
            "iat": int(iat_time.timestamp()),
            "exp": int(exp_time.timestamp()),
            "iss": "openanalyst-desktop"
        }
        
        integration_jwt = pyjwt.encode(jwt_payload, JWT_SECRET, algorithm="HS256")
        
        print(f"   ✅ JWT generated!")
        print(f"   Token: {integration_jwt[:50]}...")
        
        # ================================================================
        # STEP 4: Call ComposeIO to get connection link
        # ================================================================
        print(f"\n📍 STEP 4: Calling ComposeIO for connection link")
        
        composeio_url = f"{MCP_SERVER_URL}/api/integrations/connect"
        
        composeio_headers = {
            "Authorization": f"Bearer {integration_jwt}",
            "Content-Type": "application/json"
        }
        
        composeio_payload = {
            "provider": credentials.provider,
            "redirect_url": f"{OA_WEB_URL}/callback"
        }
        
        print(f"   URL: {composeio_url}")
        print(f"   Provider: {credentials.provider}")
        
        composeio_response = session.post(
            composeio_url,
            headers=composeio_headers,
            json=composeio_payload,
            timeout=10
        )
        
        print(f"   Response status: {composeio_response.status_code}")
        
        if composeio_response.status_code != 200:
            print(f"   ❌ ComposeIO request failed!")
            print(f"   Response: {composeio_response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get connection link from ComposeIO: {composeio_response.text}"
            )
        
        composeio_data = composeio_response.json()
        
        # Check if already connected
        if composeio_data.get("status") == "already_connected":
            print(f"   ℹ️ User already connected to {credentials.provider}")
            return {
                "success": True,
                "status": "already_connected",
                "message": f"Your {credentials.provider} account is already connected!",
                "provider": credentials.provider,
                "user_data": {
                    "userId": user_id,
                    "email": email,
                    "fullName": full_name,
                    "orgId": org_id
                }
            }
        
        # Get auth_url
        auth_url = composeio_data.get("auth_url")
        
        if not auth_url:
            print(f"   ❌ No auth_url in ComposeIO response!")
            print(f"   Response: {composeio_data}")
            raise HTTPException(
                status_code=500,
                detail="ComposeIO did not return an auth URL"
            )
        
        print(f"   ✅ Got ComposeIO connection link!")
        print(f"   Auth URL: {auth_url[:80]}...")
        
        # ================================================================
        # STEP 5: Return response
        # ================================================================
        print(f"\n✅ SUCCESS! Returning connection link to user")
        print(f"=" * 80)
        
        return {
            "success": True,
            "auth_url": auth_url,
            "provider": credentials.provider,
            "user_data": {
                "userId": user_id,
                "email": email,
                "fullName": full_name,
                "orgId": org_id
            },
            "message": f"Click the auth_url to connect your {credentials.provider} account"
        }
        
    except requests.exceptions.Timeout:
        print(f"\n⏱️ Request timeout")
        raise HTTPException(status_code=504, detail="Service timeout")
    except requests.exceptions.RequestException as e:
        print(f"\n🌐 Network error: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)