import os
import secrets
import subprocess
from readyapi import ReadyAPI, Depends, HTTPException
from pydantic import BaseModel

app = ReadyAPI(
    title="BOSSNET Shield ID Management API",
    description="API for provisioning secure VoIP users.",
)

# In a real app, this would be a proper database (e.g., PostgreSQL)
# For this MVP, we use a simple in-memory dictionary.
db = {}

class User(BaseModel):
    username: str
    email: str

def provision_asterisk_user(username: str, secret: str):
    """
    Appends a new user to pjsip_custom.conf and reloads Asterisk.
    """
    # NOTE: Writing to files and shelling out is a simple MVP approach.
    # A more robust solution would use the Asterisk REST Interface (ARI) or AMI.
    pjsip_config_path = "/etc/asterisk/pjsip_custom.conf"
    
    user_config = f"""
[{username}](user-template)
auth_username={username}
password={secret}
"""
    try:
        # Append user to the custom config file
        with open(pjsip_config_path, "a") as f:
            f.write(user_config)

        # Tell Asterisk to reload the PJSIP module
        # This requires the API container to have Docker CLI or be able to access the Docker socket.
        # For simplicity, we assume this script is run with privileges or via a shared process manager.
        # In our docker-compose, the API service won't do this directly. Instead, we'll
        # manage reloads differently. For now, this illustrates the intent.
        # A better way is using AMI client to send a "pjsip reload" command.
        print(f"Provisioned user {username}. Manual Asterisk reload required ('docker exec <container> asterisk -rx \"pjsip reload\"')")

    except Exception as e:
        # Simple error handling
        raise HTTPException(status_code=500, detail=f"Failed to provision user: {e}")


@app.post("/register", status_code=201)
def register_user(user: User):
    if user.username in db:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Generate a secure, temporary password
    secure_password = secrets.token_urlsafe(16)
    
    # Save user to our "database"
    db[user.username] = {"email": user.email, "password": secure_password}
    
    # Provision the user in Asterisk
    provision_asterisk_user(user.username, secure_password)
    
    return {
        "status": "User registered successfully",
        "username": user.username,
        "sip_server": "your-server-ip:5061",
        "password": secure_password, # Return password to user one time
    }

@app.get("/health")
def health():
    return {"status": "ok", "provisioned_users": len(db)}
