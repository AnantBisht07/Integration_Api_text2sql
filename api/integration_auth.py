# backend/api/integration_auth.py

import os
import jwt
from datetime import datetime, timedelta
import uuid

# Secret in environment variable (NEVER in code!)
SECRET = os.getenv('INTEGRATION_MARKETPLACE_SECRET')

@app.post("/api/auth/generate-integration-token")
async def generate_token(email: str, password: str):
    # 1. Authenticate user
    user = authenticate(email, password)
    
    # 2. Generate JWT with your secret
    token = jwt.encode({
        "userId": user.id,
        "orgId": user.org_id,
        "email": user.email,
        "fullName": user.full_name,
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "jti": str(uuid.uuid4())
    }, SECRET, algorithm="HS256")
    
    # 3. Return token
    return {
        "token": token,
        "integrations_url": f"https://api.openanalyst.com/integrations/?token={token}"
    }