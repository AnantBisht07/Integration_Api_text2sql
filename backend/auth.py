# backend/auth.py
# FINAL COMPLETE VERSION
# 1. Authenticate user with email/password
# 2. Get accessToken from OA Web
# 3. Verify token with /me endpoint (with x-auth-source: desktop)
# 4. Extract userId, orgId
# 5. Generate integration JWT with marketplace secret
# 6. Return ComposeIO link

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

class CredentialsRequest(BaseModel):
    email: str
    password: str
    provider: str = "gmail"  # gmail, slack, ga4, etc.

@app.get("/")
async def root():
    return {
        "service": "OpenAnalyst Integration Token API",
        "status": "running",
        "version": "4.0.0 - Complete Flow"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/auth/generate-integration-token")
async def generate_integration_token(credentials: CredentialsRequest):
    """
    Complete authentication and integration token generation flow
    
    Steps:
    1. Authenticate with OA Web using email/password
    2. Get accessToken from authentication response
    3. Verify token with /me endpoint (including x-auth-source header)
    4. Extract userId, orgId, email
    5. Generate new JWT signed with INTEGRATION_MARKETPLACE_SECRET
    6. Return ComposeIO integration URL
    
    Request:
    {
        "email": "user@example.com",
        "password": "password123",
        "provider": "gmail"  // Optional: gmail, slack, ga4
    }
    
    Returns:
    {
        "success": true,
        "integration_token": "eyJhbGci...",
        "integrations_url": "https://api.openanalyst.com/integrations/?token=...",
        "user_data": {...}
    }
    """
    
    try:
        print(f"=" * 80)
        print(f"🚀 Starting authentication flow for: {credentials.email}")
        print(f"🎯 Provider: {credentials.provider}")
        print(f"=" * 80)
        
        # ============================================================
        # STEP 1: Authenticate with OA Web
        # ============================================================
        auth_url = f"{OA_WEB_URL}/api/v1/userAccount/authenticate"
        
        auth_payload = {
            "email": credentials.email,
            "method": "password",
            "credentials": {
                "password": credentials.password
            }
        }
        
        print(f"\n📍 STEP 1: Authenticating with OA Web")
        print(f"   URL: {auth_url}")
        
        session = requests.Session()
        auth_response = session.post(auth_url, json=auth_payload, timeout=10)
        
        print(f"   Response Status: {auth_response.status_code}")
        
        if auth_response.status_code != 200:
            print(f"   ❌ Authentication failed!")
            print(f"   Response: {auth_response.text}")
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        auth_data = auth_response.json()
        print(f"   ✅ Authentication successful!")
        
        # ============================================================
        # STEP 2: Extract accessToken
        # ============================================================
        print(f"\n📍 STEP 2: Extracting accessToken")
        
        access_token = auth_data.get("accessToken") or auth_data.get("access_token")
        
        if not access_token:
            print(f"   ❌ No accessToken in response!")
            print(f"   Available keys: {list(auth_data.keys())}")
            raise HTTPException(
                status_code=500,
                detail="No access token in authentication response"
            )
        
        print(f"   ✅ Got accessToken: {access_token[:50]}...")
        
        # ============================================================
        # STEP 3: Verify token with /me endpoint
        # ============================================================
        print(f"\n📍 STEP 3: Verifying token with /me endpoint")
        
        me_url = f"{OA_WEB_URL}/api/v1/userAccount/me"
        
        # IMPORTANT: Include x-auth-source header as per documentation
        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-auth-source": "desktop",  # Required by OA Web
            "Content-Type": "application/json"
        }
        
        print(f"   URL: {me_url}")
        print(f"   Headers: Authorization: Bearer {access_token[:30]}...")
        print(f"            x-auth-source: desktop")
        
        me_response = session.get(me_url, headers=headers, timeout=10)
        
        print(f"   Response Status: {me_response.status_code}")
        
        if me_response.status_code != 200:
            print(f"   ❌ Token verification failed!")
            print(f"   Response: {me_response.text}")
            raise HTTPException(
                status_code=500,
                detail="Could not verify access token"
            )
        
        user_data = me_response.json()
        print(f"   ✅ Token verified! Got user data:")
        print(f"      {user_data}")
        
        # ============================================================
        # STEP 4: Extract user information
        # ============================================================
        print(f"\n📍 STEP 4: Extracting user information")
        
        user_id = (
            user_data.get("userId") or 
            user_data.get("user_id") or 
            user_data.get("id")
        )
        
        org_id = (
            user_data.get("orgId") or 
            user_data.get("org_id") or
            user_data.get("organizationId")
        )
        
        email = user_data.get("email") or credentials.email
        
        full_name = (
            user_data.get("fullName") or 
            user_data.get("full_name") or 
            user_data.get("name") or
            "User"
        )
        
        account_type = (
            user_data.get("accountType") or 
            user_data.get("account_type") or
            "individual"
        )
        
        print(f"   ✅ Extracted:")
        print(f"      userId: {user_id}")
        print(f"      orgId: {org_id}")
        print(f"      email: {email}")
        print(f"      fullName: {full_name}")
        print(f"      accountType: {account_type}")
        
        # Validate required fields
        if not user_id:
            print(f"   ❌ No userId found!")
            raise HTTPException(
                status_code=500,
                detail="Could not retrieve user ID"
            )
        
        # ============================================================
        # STEP 5: Generate integration JWT
        # ============================================================
        print(f"\n📍 STEP 5: Generating integration JWT")
        
        if not JWT_SECRET:
            print(f"   ❌ INTEGRATION_MARKETPLACE_SECRET not set!")
            raise HTTPException(
                status_code=500,
                detail="Server configuration error"
            )
        
        exp_time = datetime.utcnow() + timedelta(minutes=30)
        iat_time = datetime.utcnow()
        
        payload = {
            "userId": user_id,
            "orgId": org_id,
            "email": email,
            "fullName": full_name,
            "accountType": account_type,
            "iat": int(iat_time.timestamp()),
            "exp": int(exp_time.timestamp()),
            "jti": str(uuid.uuid4())
        }
        
        print(f"   Payload:")
        for key, value in payload.items():
            print(f"      {key}: {value}")
        
        integration_token = pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        print(f"   ✅ Integration token generated!")
        print(f"      Token: {integration_token[:50]}...")
        
        # ============================================================
        # STEP 6: Build integration URLs
        # ============================================================
        print(f"\n📍 STEP 6: Building integration URLs")
        
        base_url = f"https://api.openanalyst.com/integrations/?token={integration_token}"
        
        # Provider-specific URLs
        provider_map = {
            "gmail": "gmail",
            "slack": "slack",
            "ga4": "google-analytics",
            "google_analytics": "google-analytics",
            "bigquery": "bigquery"
        }
        
        provider_slug = provider_map.get(credentials.provider.lower())
        
        if provider_slug:
            provider_url = f"https://api.openanalyst.com/integrations/{provider_slug}?token={integration_token}"
        else:
            provider_url = base_url
        
        print(f"   ✅ URLs generated:")
        print(f"      Base URL: {base_url}")
        print(f"      Provider URL ({credentials.provider}): {provider_url}")
        
        # ============================================================
        # STEP 7: Return response
        # ============================================================
        print(f"\n✅ SUCCESS! All steps completed.")
        print(f"=" * 80)
        
        return {
            "success": True,
            "integration_token": integration_token,
            "integrations_url": base_url,
            "provider_url": provider_url,
            "user_data": {
                "userId": user_id,
                "email": email,
                "fullName": full_name,
                "orgId": org_id,
                "accountType": account_type
            },
            "provider": credentials.provider
        }
        
    except requests.exceptions.Timeout:
        print(f"\n⏱️ Request timeout")
        raise HTTPException(
            status_code=504,
            detail="OA Web service timeout"
        )
    except requests.exceptions.RequestException as e:
        print(f"\n🌐 Network error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="OA Web service unavailable"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)