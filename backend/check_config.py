#!/usr/bin/env python3
"""
Quick configuration checker
Run this to see what the app sees
"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

print("=" * 60)
print("Configuration Check")
print("=" * 60)

# Check if we're in the right directory
print(f"\nCurrent directory: {os.getcwd()}")

load_dotenv(dotenv_path = Path(__file__).parent / '.env')

# Check service account key path
creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'Not set')
print(f"\nGOOGLE_APPLICATION_CREDENTIALS: {creds_path}")

if creds_path and creds_path != 'Not set':
    # Resolve relative paths
    if not os.path.isabs(creds_path):
        full_path = os.path.join(os.getcwd(), creds_path)
    else:
        full_path = creds_path
    
    print(f"Resolved path: {full_path}")
    print(f"File exists: {os.path.exists(full_path)}")
    
    if os.path.exists(full_path):
        print(f"File size: {os.path.getsize(full_path)} bytes")
        print("✅ Service account key file is accessible")
    else:
        print("❌ Service account key file NOT FOUND")
        print(f"   Looking for: {full_path}")
        print(f"   Current dir files: {os.listdir('.')[:10]}")

# Check other important env vars
print("\n" + "-" * 60)
print("Environment Variables:")
print("-" * 60)

env_vars = [
    'GCP_PROJECT_ID',
    'GOOGLE_CLIENT_ID',
    'GOOGLE_CLIENT_SECRET',
    'GOOGLE_REDIRECT_URI',
    'GOOGLE_SHARED_DRIVE_ID',
    'FRONTEND_URL'
]

for var in env_vars:
    value = os.getenv(var, 'Not set')
    if 'SECRET' in var or 'KEY' in var:
        if value != 'Not set':
            print(f"{var}: {'*' * 20} (set)")
        else:
            print(f"{var}: Not set")
    else:
        print(f"{var}: {value}")

# Try to load service account
print("\n" + "-" * 60)
print("Testing Service Account Load:")
print("-" * 60)

if creds_path and os.path.exists(creds_path if os.path.isabs(creds_path) else os.path.join(os.getcwd(), creds_path)):
    try:
        from google.oauth2 import service_account
        import json
        
        full_path = creds_path if os.path.isabs(creds_path) else os.path.join(os.getcwd(), creds_path)
        with open(full_path) as f:
            key_data = json.load(f)
        
        credentials = service_account.Credentials.from_service_account_file(
            full_path,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        print("✅ Service account credentials loaded successfully")
        print(f"   Project: {key_data.get('project_id')}")
        print(f"   Email: {key_data.get('client_email')}")
    except Exception as e:
        print(f"❌ Error loading service account: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⚠️  Cannot test - service account key not found")

# Check Drive upload configuration
print("\n" + "-" * 60)
print("Drive Upload Configuration:")
print("-" * 60)

shared_drive_id = os.getenv('GOOGLE_SHARED_DRIVE_ID', 'Not set')
oauth_client_id = os.getenv('GOOGLE_CLIENT_ID', 'Not set')

if shared_drive_id != 'Not set':
    print(f"✅ GOOGLE_SHARED_DRIVE_ID: {shared_drive_id}")
    print("   → Service account with shared drive is configured")
    if not creds_path or creds_path == 'Not set':
        print("   ⚠️  WARNING: GOOGLE_APPLICATION_CREDENTIALS not set!")
elif oauth_client_id != 'Not set':
    print(f"✅ GOOGLE_CLIENT_ID: Set")
    print("   → OAuth authentication is configured")
    print("   → Users can authenticate and upload to their personal Drive")
else:
    print("❌ Drive upload is NOT configured!")
    print("   → Neither GOOGLE_SHARED_DRIVE_ID nor GOOGLE_CLIENT_ID is set")
    print("   → You need to configure one of the following:")
    print("     1. Set GOOGLE_SHARED_DRIVE_ID (with service account)")
    print("     2. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (for OAuth)")

print("\n" + "=" * 60)

