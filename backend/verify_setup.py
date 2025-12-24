#!/usr/bin/env python3
"""
Verification script to check GCP credentials setup
Run this to diagnose configuration issues
"""

import os
import sys
import json
from pathlib import Path

def check_env_file():
    """Check if .env file exists and is readable"""
    print("=" * 60)
    print("1. Checking .env file...")
    print("=" * 60)
    
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found!")
        print("   Create a .env file in the backend directory")
        return False
    
    print("✅ .env file exists")
    
    # Try to load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded")
    except ImportError:
        print("⚠️  python-dotenv not installed, loading manually...")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print("✅ Environment variables loaded manually")
    
    return True

def check_service_account_key():
    """Check service account key file"""
    print("\n" + "=" * 60)
    print("2. Checking Service Account Key...")
    print("=" * 60)
    
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set in .env")
        return False
    
    print(f"✅ GOOGLE_APPLICATION_CREDENTIALS = {creds_path}")
    
    # Check if path is relative or absolute
    if not os.path.isabs(creds_path):
        # Make it relative to current directory
        creds_path = os.path.join(os.getcwd(), creds_path)
    
    if not os.path.exists(creds_path):
        print(f"❌ Service account key file not found: {creds_path}")
        print(f"   Current directory: {os.getcwd()}")
        return False
    
    print(f"✅ Service account key file exists: {creds_path}")
    
    # Validate JSON structure
    try:
        with open(creds_path) as f:
            key_data = json.load(f)
        
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [f for f in required_fields if f not in key_data]
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        print(f"✅ Valid JSON structure")
        print(f"   Project ID: {key_data.get('project_id')}")
        print(f"   Service Account: {key_data.get('client_email')}")
        print(f"   Type: {key_data.get('type')}")
        
        return True
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in service account key: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading service account key: {e}")
        return False

def check_gcp_apis():
    """Check if GCP APIs are accessible"""
    print("\n" + "=" * 60)
    print("3. Checking GCP API Access...")
    print("=" * 60)
    
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path or not os.path.exists(creds_path):
        print("⚠️  Skipping API check (no credentials)")
        return False
    
    # Test Speech-to-Text API
    try:
        from google.cloud import speech
        from google.oauth2 import service_account
        
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        client = speech.SpeechClient(credentials=credentials)
        print("✅ Speech-to-Text API: Accessible")
    except Exception as e:
        print(f"❌ Speech-to-Text API: {str(e)}")
    
    # Test Drive API
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        service = build('drive', 'v3', credentials=credentials)
        print("✅ Drive API: Accessible")
    except Exception as e:
        print(f"❌ Drive API: {str(e)}")
        print(f"   Note: Drive API may require additional setup")
    
    return True

def check_oauth_config():
    """Check OAuth configuration"""
    print("\n" + "=" * 60)
    print("4. Checking OAuth Configuration...")
    print("=" * 60)
    
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
    
    if not client_id or client_id == 'your-client-id.apps.googleusercontent.com':
        print("⚠️  GOOGLE_CLIENT_ID not configured (OAuth login will not work)")
        print("   You can still use dummy login (admin/admin123)")
    else:
        print(f"✅ GOOGLE_CLIENT_ID: {client_id[:20]}...")
    
    if not client_secret or client_secret == 'your-client-secret':
        print("⚠️  GOOGLE_CLIENT_SECRET not configured (OAuth login will not work)")
    else:
        print(f"✅ GOOGLE_CLIENT_SECRET: {'*' * 20}...")
    
    if redirect_uri:
        print(f"✅ GOOGLE_REDIRECT_URI: {redirect_uri}")
    else:
        print("⚠️  GOOGLE_REDIRECT_URI not set")
    
    return True

def check_other_config():
    """Check other configuration"""
    print("\n" + "=" * 60)
    print("5. Checking Other Configuration...")
    print("=" * 60)
    
    project_id = os.getenv('GCP_PROJECT_ID')
    if project_id:
        print(f"✅ GCP_PROJECT_ID: {project_id}")
    else:
        print("⚠️  GCP_PROJECT_ID not set")
    
    frontend_url = os.getenv('FRONTEND_URL')
    if frontend_url:
        print(f"✅ FRONTEND_URL: {frontend_url}")
    else:
        print("⚠️  FRONTEND_URL not set (defaults to http://localhost:3000)")
    
    return True

def main():
    """Run all checks"""
    print("\n" + "=" * 60)
    print("GCP Credentials Verification")
    print("=" * 60 + "\n")
    
    results = []
    results.append(check_env_file())
    results.append(check_service_account_key())
    check_gcp_apis()
    check_oauth_config()
    check_other_config()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if all(results[:2]):  # At least env and service account
        print("✅ Basic configuration looks good!")
        print("\nIf you're still getting errors:")
        print("1. Make sure the backend server is restarted after .env changes")
        print("2. Check backend logs for specific error messages")
        print("3. Verify APIs are enabled in GCP Console")
        print("4. Check service account has correct IAM roles")
    else:
        print("❌ Configuration issues found. Please fix the errors above.")
    
    print()

if __name__ == "__main__":
    main()

