# backend/auth.py
# CORRECTED VERSION with proper data extraction

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import jwt
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

@app.post("/api/auth/generate-integration-token")
async def generate_integration_token(credentials: CredentialsRequest):
    """Generate JWT token for integration marketplace"""
    
    try:
        # Step 1: Authenticate with OpenAnalyst
        auth_url = "https://web.openanalyst.com/api/v1/userAccount/authenticate"
        
        auth_payload = {
            "email": credentials.email,
            "method": "password",
            "credentials": {
                "password": credentials.password
            }
        }
        
        print(f"🔐 Authenticating user: {credentials.email}")
        
        response = requests.post(auth_url, json=auth_payload, timeout=10)
        
        print(f"📡 Auth response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Authentication failed: {response.text}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        auth_data = response.json()
        
        # CRITICAL: Log what we got back
        print(f"📦 Auth response data: {auth_data}")
        
        # Step 2: Extract user data with fallbacks
        user_id = auth_data.get("userId") or auth_data.get("user_id") or auth_data.get("id")
        org_id = auth_data.get("orgId") or auth_data.get("org_id") or auth_data.get("organizationId")
        email = auth_data.get("email") or credentials.email
        full_name = auth_data.get("fullName") or auth_data.get("full_name") or auth_data.get("name") or "User"
        account_type = auth_data.get("accountType") or auth_data.get("account_type") or "individual"
        
        print(f"👤 Extracted data:")
        print(f"   - userId: {user_id}")
        print(f"   - orgId: {org_id}")
        print(f"   - email: {email}")
        print(f"   - fullName: {full_name}")
        
        # Step 3: Check JWT secret
        if not JWT_SECRET:
            print("❌ INTEGRATION_MARKETPLACE_SECRET not set!")
            raise HTTPException(status_code=500, detail="Server configuration error")
        
        # Step 4: Generate JWT token
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
        
        print(f"📝 JWT payload: {payload}")
        
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        print(f"✅ Token generated successfully!")
        print(f"🔑 Token (first 50 chars): {token[:50]}...")
        
        # Step 5: Return response
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
        
    except requests.exceptions.Timeout:
        print("⏱️ Request timeout")
        raise HTTPException(status_code=504, detail="Authentication service timeout")
    except requests.exceptions.RequestException as e:
        print(f"🌐 Network error: {str(e)}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable")
    except Exception as e:
        print(f"💥 Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)