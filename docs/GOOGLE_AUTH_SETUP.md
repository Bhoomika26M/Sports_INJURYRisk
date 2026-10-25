# Google OAuth 2.0 / OpenID Connect Setup Guide

This guide provides step-by-step instructions for configuring Google Authentication in the Sports Injury Risk Detection platform.

---

## 1. Google Cloud Console Configuration

### Step 1: Create or Select a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Log in with your Google account.
3. Click the project dropdown at the top of the page and select **New Project**.
4. Name your project (e.g., `Sports Injury Risk Detection`) and click **Create**.

### Step 2: Configure the OAuth Consent Screen
1. In the left navigation sidebar, navigate to **APIs & Services** > **OAuth consent screen**.
2. Under **User Type**, select **External** (unless you are using a Google Workspace organization and only internal members will access the app). Click **Create**.
3. Fill in the **App Information**:
   - **App name**: `Sports Injury Risk Detection`
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
4. Click **Save and Continue**.
5. On the **Scopes** page:
   - Click **Add or Remove Scopes**.
   - Check `.../auth/userinfo.email` and `.../auth/userinfo.profile` (or `openid`).
   - Click **Update** and then **Save and Continue**.
6. On the **Test Users** page (while in "Testing" publishing status):
   - Click **Add Users**.
   - Enter your personal Google email address (and any tester accounts).
   - Click **Save and Continue**.
7. Review your summary and click **Back to Dashboard**.

### Step 3: Create OAuth 2.0 Client ID Credentials
1. In the left navigation sidebar, navigate to **APIs & Services** > **Credentials**.
2. Click **+ Create Credentials** at the top and select **OAuth client ID**.
3. Under **Application type**, choose **Web application**.
4. Set the **Name** to: `Sports Injury Risk Web Client`.
5. Under **Authorized JavaScript origins**, click **+ Add URI** and add:
   - `http://localhost:5173`
   - `http://127.0.0.1:5173`
   - *(Add your production domain here when deploying, e.g., `https://yourdomain.com`)*
6. Leave **Authorized redirect URIs** blank (the project uses the modern OpenID Connect GIS One Tap / Popup credential flow which validates ID tokens directly on the backend).
7. Click **Create**.
8. A modal will appear displaying your **Client ID** (formatted like `1234567890-abcdefg.apps.googleusercontent.com`). Copy this Client ID.

---

## 2. Environment Configuration

### Frontend Setup
In `frontend/.env` (or create it from `frontend/.env.example`):
```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
```

> **Note:** If `VITE_GOOGLE_CLIENT_ID` is not yet configured, the application UI provides an in-app prompt where you can paste your client ID temporarily or view simulated OAuth testing.

### Backend Setup
In `backend/.env` (or create it from `backend/.env.example`):
```env
GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
```

When `GOOGLE_CLIENT_ID` is configured on the backend, the backend verifies that all incoming Google ID tokens were issued specifically for your application (audience verification).

---

## 3. Architecture & Security Model

```
[ Frontend: React + @react-oauth/google ]
               |
        1. User clicks "Sign in with Google"
        2. Google OAuth Popup prompts user
        3. Returns signed Google ID Token (JWT)
               |
               v
[ Backend: FastAPI POST /api/v1/auth/google ]
               |
        4. google.oauth2.id_token.verify_oauth2_token(token, requests.Request(), audience=GOOGLE_CLIENT_ID)
           - Cryptographically verifies Google's RSA signature using Google's public certs.
           - Verifies token is not expired (exp).
           - Enforces email_verified == True.
               |
        5. User Resolution & Security Safeguards:
           - Existing user with matching google_id -> Login permitted.
           - Existing user with matching email and no google_id -> Link google_id securely (local password preserved).
           - Existing user with conflicting google_id -> HTTP 409 Conflict (anti-takeover guard).
           - New user -> Auto-registered with selected role ('athlete', 'coach', etc.).
           - Admin role protection: Admin role requires matching ADMIN_REGISTRATION_CODE.
               |
        6. Issue standard application JWT Access Token
               |
               v
[ Client authenticated in application session ]
```

---

## 4. Manual Testing Checklist

Use this checklist to verify your Google Authentication integration:

- [ ] **1. Missing Configuration Fallback:**
  - Launch frontend with `VITE_GOOGLE_CLIENT_ID` left empty.
  - Visit `http://localhost:5173/login`.
  - Verify that the "Sign in with Google" button indicates that setup is pending and clicking it displays the configuration modal.

- [ ] **2. Live Sign-In with Real Google Account:**
  - Set `VITE_GOOGLE_CLIENT_ID` in `frontend/.env` and `GOOGLE_CLIENT_ID` in `backend/.env`.
  - Restart frontend (`npm run dev`).
  - Click the Google Sign-in button.
  - Authenticate with your Google account.
  - Verify redirect to the appropriate dashboard based on your assigned role.

- [ ] **3. New User Auto-Registration:**
  - Sign in with a new Google email that does not exist in the database.
  - Verify a new record is created in PostgreSQL with `auth_provider: 'google'` and `google_id` populated.

- [ ] **4. Account Linking (No Password Overwrite):**
  - Register a standard user using email/password (e.g., `user@example.com`).
  - Log out.
  - Sign in with Google using the same email (`user@example.com`).
  - Verify login succeeds and `google_id` is linked to the existing user.
  - Log out and log back in using the original email and password to ensure credentials remain intact.

- [ ] **5. Role-Based Access Control:**
  - On the Register page, choose a role (e.g., Coach) and sign up with Google.
  - Verify that the user profile reflects the Coach role upon login.
  - Verify that attempting to register as Administrator without the admin code safely falls back to Athlete.

- [ ] **6. Standard Email/Password Unaffected:**
  - Register and login with standard email/password accounts to ensure no regressions in local auth.
