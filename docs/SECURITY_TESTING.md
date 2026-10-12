# Security Testing Guide

This document provides procedures for manually verifying security controls in the Sports Injury Risk Detection platform.

## Prerequisites

- Backend server running on `http://localhost:8000`
- Frontend server running on `http://localhost:5173`
- Database with test data
- curl or similar HTTP client (or use browser DevTools)

## Test Scenarios

### 1. Logout + Back Button Protection

**Objective**: Verify that logout invalidates sessions and back button doesn't expose protected data.

**Steps**:
1. Login at `http://localhost:5173/login` with valid credentials
2. Navigate to a protected page (e.g., Dashboard)
3. Click logout
4. Use browser back button to navigate back

**Expected Results**:
- ✅ After logout, you are redirected to login page
- ✅ Browser back may show cached UI (acceptable)
- ✅ Any attempt to fetch protected data returns 401 Unauthorized
- ✅ Dashboard data cannot be loaded after logout

**Verification**:
```bash
# After logout, try to access protected endpoint
curl -H "Authorization: Bearer <previous_token>" http://localhost:8000/api/v1/auth/me
# Expected: 401 Unauthorized
```

---

### 2. Expired Session

**Objective**: Verify that expired sessions are rejected.

**Steps**:
1. Login and capture the JWT token
2. Wait for token to expire (default: 30 minutes) OR modify token expiration in code to 1 minute
3. Try to access a protected endpoint with the expired token

**Expected Results**:
- ✅ Expired token returns 401 Unauthorized
- ✅ Error message: "Session has been revoked or expired"

**Verification**:
```bash
# Wait for expiration, then:
curl -H "Authorization: Bearer <expired_token>" http://localhost:8000/api/v1/auth/me
# Expected: 401 Unauthorized
```

---

### 3. Revoked Session

**Objective**: Verify that server-side session revocation works.

**Steps**:
1. Login and capture the JWT token
2. Call logout endpoint
3. Try to use the same token again

**Expected Results**:
- ✅ Logout returns 200 OK
- ✅ Subsequent requests with same token return 401 Unauthorized
- ✅ Session is marked as revoked in database

**Verification**:
```bash
# Login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  | jq -r '.access_token')

# Logout
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer $TOKEN"

# Try to use token again
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
# Expected: 401 Unauthorized
```

---

### 4. IDOR (Insecure Direct Object Reference)

**Objective**: Verify that users cannot access other users' data.

**Steps**:
1. Create two athlete accounts (Athlete A and Athlete B)
2. Login as Athlete A
3. Try to access Athlete B's profile by ID

**Expected Results**:
- ✅ Athlete A cannot access Athlete B's profile
- ✅ Returns 403 Forbidden or 404 Not Found
- ✅ Athlete A can only access their own profile

**Verification**:
```bash
# Login as Athlete A
TOKEN_A=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"athlete_a@example.com","password":"password123"}' \
  | jq -r '.access_token')

# Try to access Athlete B's profile (ID 2)
curl -H "Authorization: Bearer $TOKEN_A" http://localhost:8000/api/v1/athletes/2
# Expected: 403 Forbidden
```

---

### 5. Role Escalation

**Objective**: Verify that normal users cannot access admin endpoints.

**Steps**:
1. Create a regular athlete account
2. Login as athlete
3. Try to access admin-only endpoints

**Expected Results**:
- ✅ Athlete cannot access admin endpoints
- ✅ Returns 403 Forbidden
- ✅ Admin can access admin endpoints

**Verification**:
```bash
# Login as athlete
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"athlete@example.com","password":"password123"}' \
  | jq -r '.access_token')

# Try to access admin endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/users/
# Expected: 403 Forbidden
```

---

### 6. SQL Injection Protection

**Objective**: Verify that SQL injection attempts are treated as data.

**Steps**:
1. Attempt to register with SQL injection payload in email or name
2. Check if the payload is stored as data
3. Verify that no SQL was executed

**Expected Results**:
- ✅ Malicious input is stored as literal string
- ✅ No SQL commands are executed
- ✅ Database tables remain intact

**Verification**:
```bash
# Attempt SQL injection
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Malicious'\; DROP TABLE users; --",
    "role": "athlete"
  }'

# Verify users table still exists
# Check database: sqlite3 test.db ".tables"
# Expected: users table still exists
```

---

### 7. Password Reset Security

**Objective**: Verify password reset flow security.

**Steps**:
1. Request password reset for an existing email
2. Request password reset for a non-existent email
3. Compare responses
4. Use a reset token to reset password
5. Try to reuse the same token

**Expected Results**:
- ✅ Both existing and non-existent emails return same generic response
- ✅ Reset token works once
- ✅ Reusing token fails
- ✅ Expired token fails
- ✅ All sessions invalidated after reset

**Verification**:
```bash
# Request reset for existing email
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"existing@example.com"}'
# Expected: Generic success message

# Request reset for non-existent email
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"nonexistent@example.com"}'
# Expected: Same generic success message (account enumeration protection)

# Use token once (get token from development console output)
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token":"<token>","new_password":"newpass123","confirm_password":"newpass123"}'
# Expected: Success

# Try to reuse token
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token":"<token>","new_password":"anotherpass123","confirm_password":"anotherpass123"}'
# Expected: 400 Bad Request (token already used)
```

---

### 8. Rate Limiting

**Objective**: Verify that authentication endpoints are rate limited.

**Steps**:
1. Make multiple failed login attempts (15+ times)
2. Make multiple password reset requests (10+ times)
3. Observe response codes

**Expected Results**:
- ✅ After threshold, returns 429 Too Many Requests
- ✅ Rate limit resets after time window
- ✅ Normal requests work after waiting

**Verification**:
```bash
# Make 15 failed login attempts
for i in {1..15}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrongpassword"}'
done

# Expected: Last requests return 429 Too Many Requests
```

---

### 9. Password Strength

**Objective**: Verify password strength requirements.

**Steps**:
1. Try to register with short password (< 8 characters)
2. Try to register with valid password (>= 8 characters)

**Expected Results**:
- ✅ Short password rejected with validation error
- ✅ Valid password accepted
- ✅ Same strength requirements for password reset

**Verification**:
```bash
# Try short password
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"short","full_name":"Test","role":"athlete"}'
# Expected: 422 Unprocessable Entity (password too short)

# Try valid password
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test","role":"athlete"}'
# Expected: 201 Created
```

---

### 10. Security Headers

**Objective**: Verify security headers are present.

**Steps**:
1. Make a request to any endpoint
2. Check response headers

**Expected Results**:
- ✅ `X-Content-Type-Options: nosniff`
- ✅ `X-Frame-Options: DENY`
- ✅ `X-XSS-Protection: 1; mode=block`
- ✅ `Referrer-Policy: strict-origin-when-cross-origin`
- ✅ `Permissions-Policy: geolocation=(), microphone=(), camera=()`

**Verification**:
```bash
curl -I http://localhost:8000/
# Check headers in response
```

---

### 11. Public Registration Role Security

**Objective**: Verify that public registration cannot create admin accounts.

**Steps**:
1. Try to register with role="administrator"
2. Try to register with role="coach"
3. Try to register with role="athlete"

**Expected Results**:
- ✅ Administrator registration rejected
- ✅ Coach registration rejected
- ✅ Athlete registration accepted
- ✅ Professional roles require admin creation

**Verification**:
```bash
# Try to register as admin
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"hacker@example.com","password":"password123","full_name":"Hacker","role":"administrator"}'
# Expected: 400 Bad Request (only athlete role allowed)
```

---

### 12. Input Validation

**Objective**: Verify that invalid inputs are rejected.

**Steps**:
1. Try to register with invalid email format
2. Try to create athlete with invalid age (e.g., 150)
3. Try to create athlete with negative height/weight
4. Try to create athlete with oversized text fields

**Expected Results**:
- ✅ Invalid email rejected
- ✅ Invalid age rejected
- ✅ Negative values rejected
- ✅ Oversized fields rejected

**Verification**:
```bash
# Invalid email
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"notanemail","password":"password123","full_name":"Test","role":"athlete"}'
# Expected: 422 Unprocessable Entity

# Invalid age
curl -X POST http://localhost:8000/api/v1/athletes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"athlete_id":"ATH001","age":150,"height":180,"weight":75,"sport_type":"Basketball"}'
# Expected: 422 Unprocessable Entity
```

---

## Automated Security Tests

Run the comprehensive security test suite:

```bash
cd backend
pytest tests/test_security.py -v
```

Expected: 21 passed, 2 skipped (rate limiting tests)

---

## Browser-Based Testing

### Using Browser DevTools

1. **Open DevTools** (F12)
2. **Go to Network tab**
3. **Perform actions** (login, logout, etc.)
4. **Inspect requests**:
   - Check Authorization headers
   - Verify status codes
   - Check response headers

### Common Security Issues to Check

- **Token Storage**: Verify token is stored in localStorage
- **Token Transmission**: Verify token sent in Authorization header
- **Logout Behavior**: Verify token removed after logout
- **Protected Routes**: Verify redirect to login for unauthenticated users
- **Error Messages**: Verify no sensitive data in error messages

---

## Production Security Checklist

Before deploying to production:

- [ ] Change `SECRET_KEY` to a strong random value (minimum 32 characters)
- [ ] Configure `DATABASE_URL` for PostgreSQL (not SQLite)
- [ ] Configure SMTP settings for email delivery
- [ ] Set `ENVIRONMENT=production`
- [ ] Update CORS to production frontend origin
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up database backups
- [ ] Enable security monitoring
- [ ] Review and rotate any committed secrets
- [ ] Run full security test suite
- [ ] Perform penetration testing
- [ ] Set up incident response procedures

---

## Reporting Security Issues

If you discover a security vulnerability:

1. Do not publicly disclose
2. Contact the development team
3. Provide details of the vulnerability
4. Allow time for remediation
5. Follow responsible disclosure

---

**Last Updated**: 2026-09-30  
**Version**: 1.0.0 (Milestone 1)
