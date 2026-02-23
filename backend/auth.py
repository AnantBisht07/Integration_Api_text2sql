# backend/auth.py
# ROBUST VERSION - Tries multiple methods to get userId and orgId

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import jwt as pyjwt
import os
from datetime import datetime, timedelta
import uuid
import requests

app = FastAPI(title="Integration Token API")

JWT_SECRET = os.getenv('INTEGRATION_MARKETPLACE_SECRET')

class CredentialsRequest(BaseModel):
    email: str
    password: str

@app.get("/")
async def root():
    return {
        "service": "OpenAnalyst Integration Token API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

def try_get_user_data(access_token, session):
    """
    Try multiple methods to get user data
    Returns: dict with userId, orgId, email, fullName
    """
    
    # Method 1: Try /me endpoint
    print("📍 Method 1: Trying /api/v1/userAccount/me")
    try:
        me_response = session.get(
            "https://web.openanalyst.com/api/v1/userAccount/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        if me_response.status_code == 200:
            data = me_response.json()
            print(f"✅ /me endpoint worked! Data: {data}")
            return data
        else:
            print(f"❌ /me endpoint failed: {me_response.status_code}")
    except Exception as e:
        print(f"❌ /me endpoint error: {e}")
    
    # Method 2: Try decoding the accessToken itself
    print("📍 Method 2: Decoding accessToken JWT")
    try:
        # Decode without verification to see what's inside
        decoded = pyjwt.decode(access_token, options={"verify_signature": False})
        print(f"✅ Decoded accessToken: {decoded}")
        
        # Check if it has userId
        if decoded.get("userId") or decoded.get("user_id") or decoded.get("id"):
            print("✅ Found userId in accessToken!")
            return decoded
    except Exception as e:
        print(f"❌ Token decode error: {e}")
    
    # Method 3: Try /users/me
    print("📍 Method 3: Trying /api/v1/users/me")
    try:
        users_response = session.get(
            "https://web.openanalyst.com/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        if users_response.status_code == 200:
            data = users_response.json()
            print(f"✅ /users/me worked! Data: {data}")
            return data
    except Exception as e:
        print(f"❌ /users/me error: {e}")
    
    # Method 4: Try /user/profile
    print("📍 Method 4: Trying /api/v1/user/profile")
    try:
        profile_response = session.get(
            "https://web.openanalyst.com/api/v1/user/profile",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        if profile_response.status_code == 200:
            data = profile_response.json()
            print(f"✅ /user/profile worked! Data: {data}")
            return data
    except Exception as e:
        print(f"❌ /user/profile error: {e}")
    
    print("❌ All methods failed to get user data")
    return None

@app.post("/api/auth/generate-integration-token")
async def generate_integration_token(credentials: CredentialsRequest):
    """Generate JWT token for integration marketplace"""
    
    try:
        # Step 1: Authenticate
        auth_url = "https://web.openanalyst.com/api/v1/userAccount/authenticate"
        
        auth_payload = {
            "email": credentials.email,
            "method": "password",
            "credentials": {
                "password": credentials.password
            }
        }
        
        print(f"🔐 Authenticating user: {credentials.email}")
        
        session = requests.Session()
        auth_response = session.post(auth_url, json=auth_payload, timeout=10)
        
        if auth_response.status_code != 200:
            print(f"❌ Authentication failed: {auth_response.text}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        auth_data = auth_response.json()
        print(f"📦 Auth response keys: {auth_data.keys()}")
        
        # Step 2: Get access token
        access_token = auth_data.get("accessToken") or auth_data.get("access_token")
        
        if not access_token:
            print(f"❌ No accessToken! Full response: {auth_data}")
            raise HTTPException(status_code=500, detail="No access token in auth response")
        
        print(f"🎫 Got access token: {access_token[:50]}...")
        
        # Step 3: Try to get user data using multiple methods
        user_data = try_get_user_data(access_token, session)
        
        if not user_data:
            # Fallback: use auth_data
            print("⚠️ Using auth_data as fallback")
            user_data = auth_data
        
        # Step 4: Extract fields with all possible variations
        user_id = (
            user_data.get("userId") or 
            user_data.get("user_id") or 
            user_data.get("id") or
            user_data.get("_id") or
            user_data.get("sub")  # JWT standard claim
        )
        
        org_id = (
            user_data.get("orgId") or 
            user_data.get("org_id") or 
            user_data.get("organizationId") or
            user_data.get("organization_id") or
            user_data.get("orgid")
        )
        
        email = user_data.get("email") or credentials.email
        
        full_name = (
            user_data.get("fullName") or 
            user_data.get("full_name") or 
            user_data.get("name") or
            user_data.get("displayName") or
            "User"
        )
        
        account_type = (
            user_data.get("accountType") or 
            user_data.get("account_type") or 
            "individual"
        )
        
        print(f"👤 Final extracted data:")
        print(f"   - userId: {user_id}")
        print(f"   - orgId: {org_id}")
        print(f"   - email: {email}")
        print(f"   - fullName: {full_name}")
        
        # Step 5: Validate
        if not user_id:
            print("❌ CRITICAL: Could not find userId anywhere!")
            print(f"📦 Available data: {user_data}")
            raise HTTPException(
                status_code=500, 
                detail="Could not retrieve user ID. Please contact support."
            )
        
        # Step 6: Generate JWT
        if not JWT_SECRET:
            raise HTTPException(status_code=500, detail="Server configuration error")
        
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
        
        print(f"📝 Final JWT payload: {payload}")
        
        token = pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        print(f"✅ Token generated successfully!")
        
        return {
            "success": True,
            "token": token,
            "integrations_url": f"https://api.openanalyst.com/integrations/?token={token}",
            "user_data": {
                "userId": user_id,
                "email": email,
                "fullName": full_name,
                "orgId": org_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)