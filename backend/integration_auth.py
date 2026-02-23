# backend/integration_auth.py
# Complete standalone FastAPI application for integration token generation

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import jwt
import os
from datetime import datetime, timedelta
import uuid
import requests

# Create FastAPI app instance
app = FastAPI(title="Integration Token API")

# Get secret from environment variable
JWT_SECRET = os.getenv('INTEGRATION_MARKETPLACE_SECRET')

# Request model
class CredentialsRequest(BaseModel):
    email: str
    password: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "OpenAnalyst Integration Token API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}

@app.post("/api/auth/generate-integration-token")
async def generate_integration_token(credentials: CredentialsRequest):
    """
    Generate JWT token for integration marketplace
    
    Request body:
    {
        "email": "user@example.com",
        "password": "password123"
    }
    
    Returns:
    {
        "token": "eyJhbGci...",
        "integrations_url": "https://api.openanalyst.com/integrations/?token=..."
    }
    """
    
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
        
        print(f"Authenticating user: {credentials.email}")
        
        response = requests.post(auth_url, json=auth_payload, timeout=10)
        
        if response.status_code != 200:
            print(f"Authentication failed: {response.status_code}")
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        auth_data = response.json()
        print(f"Authentication successful for: {credentials.email}")
        
        # Step 2: Check if JWT secret is configured
        if not JWT_SECRET:
            print("ERROR: INTEGRATION_MARKETPLACE_SECRET not set!")
            raise HTTPException(
                status_code=500,
                detail="Server configuration error - secret key not found"
            )
        
        # Step 3: Generate JWT token
        exp_time = datetime.utcnow() + timedelta(minutes=30)
        
        payload = {
            "userId": auth_data.get("userId"),
            "orgId": auth_data.get("orgId"),
            "email": auth_data.get("email"),
            "fullName": auth_data.get("fullName"),
            "accountType": auth_data.get("accountType", "individual"),
            "iat": datetime.utcnow(),
            "exp": exp_time,
            "jti": str(uuid.uuid4())
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        print(f"JWT token generated successfully for: {credentials.email}")
        
        # Step 4: Return token
        return {
            "success": True,
            "token": token,
            "integrations_url": f"https://api.openanalyst.com/integrations/?token={token}",
            "user_data": {
                "userId": auth_data.get("userId"),
                "email": auth_data.get("email"),
                "fullName": auth_data.get("fullName"),
                "orgId": auth_data.get("orgId")
            }
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Authentication service timeout"
        )
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable"
        )
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

# For local testing
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)