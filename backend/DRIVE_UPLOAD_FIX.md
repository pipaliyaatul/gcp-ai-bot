# Fixing Google Drive Upload Error (403 Storage Quota Exceeded)

## Problem
Service Accounts cannot upload files directly to Google Drive because they don't have storage quota. You'll see this error:
```
Service Accounts do not have storage quota. Leverage shared drives or use OAuth delegation instead.
```

## ✅ Solution Implemented: OAuth (User Authentication)

**The application has been updated to use OAuth credentials for Google Drive uploads.**

### How It Works

1. **User Authentication**: Users must log in with Google OAuth before uploading files
2. **Credential Storage**: OAuth credentials (including Drive access) are stored in the user's session
3. **Automatic Upload**: When a user uploads a file, their OAuth credentials are automatically used to upload to their personal Google Drive

### What Was Changed

#### Backend Changes:
- ✅ `drive_service.py`: Updated to accept OAuth credentials for user-based uploads
- ✅ `auth_service.py`: Now requests Drive scope (`https://www.googleapis.com/auth/drive.file`) during OAuth
- ✅ `app.py`: Upload endpoint now accepts and uses OAuth credentials from authenticated users

#### Frontend Changes:
- ✅ `ChatInterface.js`: Automatically sends OAuth credentials with upload requests
- ✅ Credentials are stored in localStorage after Google login

### Requirements

1. **OAuth must be configured** with the following environment variables:
   ```bash
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
   ```

2. **Users must authenticate** with Google before uploading files
   - The OAuth flow will request Drive access permission
   - Files will be uploaded to the user's personal Google Drive

### Testing

1. Start your backend server
2. Log in with Google OAuth (not dummy login)
3. Upload a file - it should now work without the 403 error!

---

## Alternative Solutions (Not Implemented)

### Solution 1: Use Google Workspace Shared Drive (Alternative)

If you have Google Workspace, you can upload files to a Shared Drive using a Service Account.

#### Steps:
1. **Create or identify a Shared Drive** in your Google Workspace
2. **Get the Shared Drive ID**:
   - Open the Shared Drive in Google Drive
   - The URL will look like: `https://drive.google.com/drive/folders/0ABC123xyz...`
   - The ID is the part after `/folders/`
3. **Add the Service Account as a member**:
   - Open the Shared Drive
   - Click "Manage members"
   - Add your service account email (found in `service-account-key.json` as `client_email`)
   - Give it "Content Manager" or "Manager" role
4. **Set environment variable**:
   ```bash
   export GOOGLE_SHARED_DRIVE_ID="0ABC123xyz..."
   ```
   Or add to your `.env` file:
   ```
   GOOGLE_SHARED_DRIVE_ID=0ABC123xyz...
   ```

#### Benefits:
- ✅ No user authentication required
- ✅ Files stored in organization's Shared Drive
- ✅ Works automatically with existing service account

---

### Solution 2: Use OAuth (User Authentication) - ✅ IMPLEMENTED

**This solution has been implemented. See above for details.**

---

### Solution 3: Domain-Wide Delegation (Advanced)

For Google Workspace admins only. Allows service account to impersonate users.

#### Steps:
1. Enable domain-wide delegation in Google Cloud Console
2. Configure in Google Workspace Admin Console
3. Use service account with `sub` parameter to impersonate users

**Note:** This is complex and requires admin access. Not recommended unless you need it.

---

## Quick Fix (Immediate)

For the fastest solution, use **Solution 1 (Shared Drive)**:

1. Create a Shared Drive in Google Workspace
2. Add your service account email as a member
3. Set `GOOGLE_SHARED_DRIVE_ID` environment variable
4. Restart your backend server

The code has already been updated to support this!

---

## Testing

After implementing a solution, test with:
```bash
python check_config.py
```

Then try uploading a file through your application.

