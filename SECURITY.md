# Security Documentation

## Overview

This document describes the security architecture, controls, and best practices implemented in the Sports Injury Risk Detection platform for Milestone 1.

## Security Architecture

### Authentication

The system uses JWT (JSON Web Tokens) with server-side session revocation support:

- **JWT Tokens**: Short-lived access tokens (30 minutes default)
- **Session Revocation**: Server-side session tracking in the `sessions` table
- **Token Structure**: Contains `sub` (email), `jti` (session ID), and `exp` (expiration)
- **Password Hashing**: bcrypt with cost factor 12 (via Passlib)

### Session Lifecycle

1. **Login**:
   - User provides credentials
   - Server validates credentials
   - Server creates JWT with unique `jti` (session ID)
   - Server creates session record in `sessions` table
   - Token is returned to client

2. **Authenticated Request**:
   - Client sends JWT in `Authorization: Bearer <token>` header
   - Server validates JWT signature and expiration
   - Server checks if session is not revoked in `sessions` table
   - Request proceeds if valid

3. **Logout**:
   - Client calls `/api/v1/auth/logout`
   - Server marks session as revoked in `sessions` table
   - Client clears local storage
   - Future requests with the same token fail

4. **Session Expiration**:
   - JWT expiration is checked (30 minutes)
   - Session `expires_at` is checked in database
   - Expired sessions are rejected

### Password Recovery

The password reset workflow includes:

1. **Request**:
   - User provides email
   - Server generates cryptographically secure random token (secrets.token_urlsafe(32))
   - Server stores SHA-256 hash of token in `password_resets` table
   - Server sets 1-hour expiration
   - Server sends email with reset link (development: prints to console)

2. **Reset**:
   - User clicks link with token
   - Server validates token hash and expiration
   - Server marks token as used (single-use)
   - Server updates password
   - Server revokes all existing sessions
   - Server sends confirmation email

3. **Security Features**:
   - Generic response prevents account enumeration
   - Tokens are single-use
   - Tokens expire after 1 hour
   - All sessions invalidated after password change
   - Tokens are hashed before storage

## Role-Based Access Control (RBAC)

### Supported Roles

- `athlete` - Can view/update own profile
- `coach` - Can manage athlete profiles
- `physiotherapist` - Can view injury-related information
- `sports_scientist` - Can access analysis data
- `administrator` - Full system access

### Role Assignment Security

- **Public Registration**: Only allows `athlete` role
- **Professional Roles**: Must be created by administrators via admin-only functions
- **Role Enforcement**: Backend dependencies (`require_role()`) enforce role checks
- **Default Deny**: Unauthenticated requests return 401; insufficient permissions return 403

### Object-Level Authorization (IDOR Protection)

The system implements object-level authorization to prevent Insecure Direct Object Reference (IDOR):

- **Athlete Profiles**: Athletes can only access/update their own profile
- **Professional Roles**: Can access athlete profiles based on role permissions
- **Deletion**: Restricted to administrators only
- **Enforcement**: Server-side checks before any CRUD operation

## SQL Injection Prevention

### Implementation

- **ORM Usage**: All database queries use SQLAlchemy ORM
- **Parameterized Queries**: No raw SQL concatenation
- **Validation**: Pydantic schemas validate all inputs
- **Type Safety**: Strong typing prevents injection via type coercion

### Testing

SQL injection payloads are treated as data, not executable SQL:
- Input like `' OR 1=1 --` is stored as literal string
- Table names/column names are never user-controlled
- No `text()` or `execute()` with user input

## Rate Limiting

### Implementation

- **In-Memory Rate Limiter**: Simple in-memory implementation for development
- **Rate Limits**:
  - Registration: 5 requests per 5 minutes
  - Login: 10 requests per minute
  - Forgot Password: 3 requests per 5 minutes
  - Reset Password: 5 requests per 5 minutes
- **Key**: IP address + endpoint path
- **Response**: HTTP 429 Too Many Requests

### Production Consideration

For production deployment, consider:
- Redis-based rate limiting for distributed systems
- Configurable limits per endpoint
- IP-based or user-based limits
- Temporary blocking for repeated violations

## Input Validation

### Backend Validation

All inputs are validated using Pydantic schemas:

- **Email**: Format validation (@ and . present)
- **Password**: Minimum 8 characters
- **Age**: 1-99 years
- **Height/Weight**: Positive values, reasonable limits (max 300)
- **Text Fields**: Length limits (e.g., full_name: 100 chars, injury_history: 5000 chars)
- **Whitespace**: Stripped from string fields

### Mass Assignment Protection

Separate schemas for different operations:
- `UserCreate` - Registration
- `UserUpdate` - User updates (no role field)
- `AdminUserUpdate` - Admin-only updates (includes role)
- `AthleteCreate` - Profile creation
- `AthleteUpdate` - Profile updates

Sensitive fields (role, is_active) are excluded from user-controlled update schemas.

## Security Headers

The API includes the following security headers:

- `X-Content-Type-Options: nosniff` - Prevent MIME type sniffing
- `X-Frame-Options: DENY` - Prevent clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Referrer-Policy: strict-origin-when-cross-origin` - Control referrer information
- `Permissions-Policy: geolocation=(), microphone=(), camera=()` - Restrict browser features

## CORS Configuration

### Development

- Allowed origins: `http://localhost:5173`, `http://localhost:3000`
- Credentials: Enabled
- Methods: All
- Headers: All

### Production

In production, configure:
- Specific frontend origin (not `*`)
- Explicit allowed methods
- Explicit allowed headers
- Credentials only if needed

## Secret Management

### Environment Variables

All secrets are configured via environment variables:

```bash
# Backend
DATABASE_URL=postgresql://user:password@localhost:5432/sports_injury_risk
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@sportsinjuryrisk.com

# Environment
ENVIRONMENT=development
```

### Security Practices

- `.env` files are in `.gitignore`
- `.env.example` contains placeholders only
- Never commit real secrets
- Rotate secrets if compromised
- Use strong random secrets (minimum 32 characters)

## Error Handling

### Secure Error Responses

- **Generic Messages**: "Unable to complete the request" for internal errors
- **No Stack Traces**: Stack traces logged server-side, not exposed to clients
- **No Database Details**: Connection strings, SQL queries not exposed
- **No Passwords**: Password hashes never returned
- **Logging**: Detailed errors logged with appropriate context

### Audit Logging

Security events are logged:

- Successful login
- Failed login
- Logout
- Password reset requested
- Password reset completed
- Password changed
- Authorization failures
- User registration
- Role changes

**Never logged**:
- Passwords
- Raw reset tokens
- JWT secrets
- Sensitive personal data

## Known Limitations

### Development Environment

- **In-Memory Rate Limiting**: Lost on server restart; use Redis in production
- **Development Email**: Reset links printed to console; requires SMTP in production
- **SQLite**: Using SQLite for development; PostgreSQL recommended for production
- **Default Secret**: Development secret key should be changed for production

### Future Enhancements

- **Refresh Tokens**: Implement refresh token rotation
- **Multi-Factor Authentication**: Add 2FA support
- **Session Timeout**: Implement idle timeout
- **IP Whitelisting**: Admin access from specific IPs
- **Advanced Rate Limiting**: Redis-based distributed rate limiting
- **Security Monitoring**: Real-time security event monitoring
- **Automated Token Rotation**: Periodic secret rotation

## Security Testing

### Automated Tests

Comprehensive security tests cover:

- ✅ Role assignment security (public registration cannot create admin)
- ✅ Account enumeration protection (forgot password generic response)
- ✅ Password strength validation (minimum 8 characters)
- ✅ IDOR protection (athletes cannot access other athletes)
- ✅ Session revocation (logout invalidates sessions)
- ✅ SQL injection prevention (malicious input treated as data)
- ✅ Authorization (unauthenticated = 401, unauthorized = 403)
- ✅ Password reset security (single-use tokens, expiration)
- ✅ Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
- ✅ CORS restrictions

### Manual Testing

See `docs/SECURITY_TESTING.md` for manual security verification procedures.

## Dependencies

### Security-Related Dependencies

- `python-jose[cryptography]` - JWT implementation
- `passlib[bcrypt]` - Password hashing
- `bcrypt==4.0.1` - Bcrypt implementation (pinned for compatibility)
- `pydantic` - Input validation
- `fastapi` - API framework with built-in security features

### Regular Updates

Keep dependencies updated for security patches:
```bash
pip install --upgrade -r requirements.txt
```

## Compliance Notes

### Data Protection

- **Passwords**: Hashed with bcrypt, never stored in plaintext
- **Personal Data**: Minimized collection, stored securely
- **Audit Logs**: No sensitive data in logs
- **Email**: Not logged in plaintext

### Accessibility

- **Error Messages**: Generic to prevent information leakage
- **Account Enumeration**: Prevented via generic responses
- **Rate Limiting**: Prevents brute force attacks

## Contact

For security concerns or to report vulnerabilities, contact the development team.

---

**Last Updated**: 2026-09-30  
**Version**: 1.0.0 (Milestone 1)
