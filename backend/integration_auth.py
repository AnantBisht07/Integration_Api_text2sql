import jwt
import os
from datetime import datetime, timedelta
import uuid

# Secret stored in environment variable (NOT in code!)
JWT_SECRET = os.getenv('INTEGRATION_MARKETPLACE_SECRET')

@app.post("/api/auth/generate-integration-token")
async def generate_integration_token(credentials: dict):
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
    
    # Authenticate user
    user = authenticate_user(credentials['email'], credentials['password'])
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate token
    exp_time = datetime.utcnow() + timedelta(minutes=30)
    
    payload = {
        "userId": user.id,
        "orgId": user.org_id,
        "email": user.email,
        "fullName": user.full_name,
        "accountType": user.account_type,
        "iat": datetime.utcnow(),
        "exp": exp_time,
        "jti": str(uuid.uuid4())
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    return {
        "token": token,
        "integrations_url": f"https://api.openanalyst.com/integrations/?token={token}"
    }