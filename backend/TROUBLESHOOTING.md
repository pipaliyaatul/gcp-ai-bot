# Troubleshooting Guide

## Common Issues and Solutions

### Issue: 400 Bad Request / 500 Internal Server Error

#### 1. Check if .env file is being loaded

The app needs to load the `.env` file. Make sure:

- `.env` file exists in the `backend/` directory
- You've restarted the server after creating/modifying `.env`
- The file format is correct (no spaces around `=`)

**Test:**
```bash
cd backend
source venv/bin/activate
python check_config.py
```

#### 2. Verify Service Account Key Path

The `GOOGLE_APPLICATION_CREDENTIALS` should point to the JSON key file.

**In .env file:**
```bash
# If key is in backend directory:
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# Or use absolute path:
GOOGLE_APPLICATION_CREDENTIALS=/full/path/to/service-account-key.json
```

**Verify:**
```bash
cd backend
ls -la service-account-key.json
# Should show the file exists
```

#### 3. Check Environment Variables

Run the diagnostic script:
```bash
cd backend
source venv/bin/activate
python check_config.py
```

This will show:
- Which environment variables are set
- If the service account key file is found
- If credentials can be loaded

#### 4. Common .env File Issues

**Wrong format:**
```bash
# ❌ Wrong - spaces around =
GOOGLE_APPLICATION_CREDENTIALS = ./service-account-key.json

# ✅ Correct - no spaces
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
```

**Missing quotes (if path has spaces):**
```bash
# If path has spaces, use quotes
GOOGLE_APPLICATION_CREDENTIALS="./path with spaces/key.json"
```

**Relative vs Absolute paths:**
```bash
# Relative to backend directory (recommended)
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# Absolute path (also works)
GOOGLE_APPLICATION_CREDENTIALS=/Users/yourname/path/to/key.json
```

### Issue: "Google Drive service not initialized"

**Causes:**
1. `GOOGLE_APPLICATION_CREDENTIALS` not set in `.env`
2. Service account key file not found
3. Invalid JSON in key file
4. Missing IAM permissions

**Solutions:**

1. **Check .env file:**
   ```bash
   cd backend
   cat .env | grep GOOGLE_APPLICATION_CREDENTIALS
   ```

2. **Verify file exists:**
   ```bash
   cd backend
   ls -la service-account-key.json
   ```

3. **Test credentials:**
   ```bash
   cd backend
   source venv/bin/activate
   python check_config.py
   ```

4. **Check IAM roles in GCP Console:**
   - Go to IAM & Admin > Service Accounts
   - Verify service account has `Cloud Speech Client` role
   - For Drive: Service account needs Drive API access

### Issue: "OAuth credentials not configured" (400 error)

This is expected if you haven't set up OAuth. You can:

1. **Use dummy login** (admin/admin123) - no OAuth needed
2. **Set up OAuth** - see GCP_SETUP.md

### Issue: File upload fails with 500 error

**Check backend logs** for specific error:

```bash
# Look for error messages in terminal where backend is running
# Common errors:
# - "File is empty" - file validation failed
# - "Could not extract content" - file processing failed
# - "Drive service not initialized" - credentials issue
```

**Solutions:**

1. **For text files (PDF, DOCX, TXT):**
   - Should work even without GCP credentials
   - Files will be saved locally if Drive not configured

2. **For audio files (WAV, M4A, MP3):**
   - Requires Speech-to-Text API
   - Needs valid `GOOGLE_APPLICATION_CREDENTIALS`
   - Check API is enabled in GCP Console

### Quick Diagnostic Steps

1. **Check .env file exists:**
   ```bash
   cd backend
   ls -la .env
   ```

2. **Check service account key:**
   ```bash
   cd backend
   ls -la service-account-key.json
   ```

3. **Run diagnostic script:**
   ```bash
   cd backend
   source venv/bin/activate
   python check_config.py
   ```

4. **Check backend logs:**
   - Look at terminal where `python app.py` is running
   - Look for WARNING or ERROR messages
   - Check what services initialized successfully

5. **Test API endpoints:**
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Should return: {"status":"healthy"}
   ```

### Still Having Issues?

1. **Restart the backend server** after changing `.env`
2. **Check file permissions:**
   ```bash
   chmod 600 service-account-key.json  # Secure the key file
   chmod 644 .env  # Make .env readable
   ```
3. **Verify virtual environment is activated:**
   ```bash
   # Should see (venv) in prompt
   which python  # Should point to venv/bin/python
   ```
4. **Check Python can import modules:**
   ```bash
   source venv/bin/activate
   python -c "from google.cloud import speech; print('OK')"
   ```

### Getting Help

When asking for help, provide:
1. Output of `python check_config.py`
2. Backend error logs
3. Contents of `.env` (remove secrets!)
4. What operation you were trying (upload file, login, etc.)

