# OAuth Setup Guide for PratikoAI

This guide will help you set up Google and LinkedIn OAuth authentication for PratikoAI.

## Prerequisites

- Backend running on `http://localhost:8000`
- Frontend running on `http://localhost:3000`
- Access to Google Cloud Console
- Access to LinkedIn Developer Portal

## 1. Google OAuth Setup

### Create Google OAuth Application

1. **Go to Google Cloud Console**
   - Navigate to [https://console.cloud.google.com](https://console.cloud.google.com)
   - Create a new project or select an existing one

2. **Enable Required APIs**
   - Go to "APIs & Services" → "Library"
   - Search for and enable "Google+ API" (if not already enabled)

3. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Choose "Web application" as the application type
   - Name: "PratikoAI Development" (or your preferred name)

4. **Configure OAuth Consent Screen**
   - Go to "OAuth consent screen"
   - Choose "External" user type
   - Fill in required fields:
     - App name: "PratikoAI"
     - User support email: Your email
     - Developer contact information: Your email
   - Add scopes: `email`, `profile`, `openid`
   - Add test users if in development mode

5. **Set Authorized Redirect URIs**
   - In your OAuth 2.0 client settings, add:
     - **Development**: `http://localhost:3000/auth/callback`
     - **Production**: `https://yourdomain.com/auth/callback`

6. **Copy Credentials**
   - Copy your "Client ID" and "Client Secret"
   - You'll need these for the environment variables

## 2. LinkedIn OAuth Setup

### Create LinkedIn OAuth Application

1. **Go to LinkedIn Developer Portal**
   - Navigate to [https://www.linkedin.com/developers/apps](https://www.linkedin.com/developers/apps)
   - Click "Create app"

2. **Fill in App Information**
   - App name: "PratikoAI"
   - LinkedIn Page: Select or create a company page
   - Privacy policy URL: Your privacy policy URL
   - App logo: Upload your app logo

3. **Configure OAuth Settings**
   - Go to the "Auth" tab
   - Under "OAuth 2.0 settings":
     - Add Authorized redirect URLs:
       - **Development**: `http://localhost:3000/auth/callback`
       - **Production**: `https://yourdomain.com/auth/callback`

4. **Request OAuth Scopes**
   - In the "Products" tab, request access to:
     - "Sign In with LinkedIn"
     - This will give you access to `r_liteprofile` and `r_emailaddress` scopes

5. **Copy Credentials**
   - From the "Auth" tab, copy:
     - Client ID
     - Client Secret

## 3. Multi-Environment OAuth Best Practices

### Why Separate OAuth Apps Per Environment?

**✅ RECOMMENDED:** Create separate OAuth applications for each environment:
- **Development** (`localhost:3000`)
- **Staging** (`https://staging.yourdomain.com`) 
- **Production** (`https://yourdomain.com`)

### Benefits of Separate OAuth Apps:

1. **Security Isolation** - Production credentials never used in development
2. **Different Redirect URIs** - Each environment has its own callback URLs
3. **Analytics Separation** - Track usage per environment separately
4. **Team Access Control** - Limit who has access to production OAuth credentials
5. **Testing Safety** - Development testing won't affect production OAuth quotas/limits

### Creating Multiple OAuth Applications

#### Google OAuth - Multiple Apps

1. **Create 3 separate OAuth clients** in the same Google Cloud project:
   - `PratikoAI Development` 
   - `PratikoAI Staging`
   - `PratikoAI Production`

2. **Configure different redirect URIs** for each:
   - **Development**: `http://localhost:3000/auth/callback`
   - **Staging**: `https://staging.yourdomain.com/auth/callback`
   - **Production**: `https://yourdomain.com/auth/callback`

#### LinkedIn OAuth - Multiple Apps

1. **Create 3 separate LinkedIn apps**:
   - `PratikoAI Development`
   - `PratikoAI Staging` 
   - `PratikoAI Production`

2. **Configure redirect URIs** for each environment

### Environment Configuration

#### Development Environment (`.env.development`):
```bash
# Google OAuth - Development App
GOOGLE_CLIENT_ID="dev-google-client-id-here"
GOOGLE_CLIENT_SECRET="dev-google-client-secret-here"

# LinkedIn OAuth - Development App  
LINKEDIN_CLIENT_ID="dev-linkedin-client-id-here"
LINKEDIN_CLIENT_SECRET="dev-linkedin-client-secret-here"

# Frontend URL for OAuth redirects
FRONTEND_URL="http://localhost:3000"
```

#### Staging Environment (`.env.staging`):
```bash
# Google OAuth - Staging App
GOOGLE_CLIENT_ID="staging-google-client-id-here"
GOOGLE_CLIENT_SECRET="staging-google-client-secret-here"

# LinkedIn OAuth - Staging App
LINKEDIN_CLIENT_ID="staging-linkedin-client-id-here"
LINKEDIN_CLIENT_SECRET="staging-linkedin-client-secret-here"

# Frontend URL for OAuth redirects
FRONTEND_URL="https://staging.yourdomain.com"
```

#### Production Environment (`.env.production`):
```bash
# Google OAuth - Production App
GOOGLE_CLIENT_ID="prod-google-client-id-here"
GOOGLE_CLIENT_SECRET="prod-google-client-secret-here"

# LinkedIn OAuth - Production App
LINKEDIN_CLIENT_ID="prod-linkedin-client-id-here"
LINKEDIN_CLIENT_SECRET="prod-linkedin-client-secret-here"

# Frontend URL for OAuth redirects
FRONTEND_URL="https://yourdomain.com"
```

### Credential Management Best Practices

#### Local Development:
- ✅ **Safe to use development OAuth credentials locally**
- ✅ Store in `.env.development` (already in `.gitignore`)
- ✅ Share development credentials with team members
- ✅ Development credentials only work with `localhost:3000`

#### Credential Security Checklist:
```bash
# ✅ GOOD: Environment-specific credentials
GOOGLE_CLIENT_ID="dev-123456789"      # Development only
GOOGLE_CLIENT_ID="staging-987654321"  # Staging only  
GOOGLE_CLIENT_ID="prod-555666777"     # Production only

# ❌ BAD: Using production credentials in development
GOOGLE_CLIENT_ID="prod-555666777"     # Production credentials in .env.development
```

#### Team Access Management:
- **Development**: All developers can access
- **Staging**: Senior developers and DevOps
- **Production**: Only DevOps and tech leads
- **Use secret management tools** (AWS Secrets Manager, Azure Key Vault, etc.) for production

#### Quick Start for Local Development:
1. Create Google/LinkedIn **development** apps first
2. Use `localhost:3000` redirect URI
3. Add credentials to `.env.development`
4. Test OAuth flow locally
5. Later create staging/production apps when deploying

## 4. Testing OAuth Flow

### Start the Services

1. **Start Backend**:
   ```bash
   cd /Users/micky/PycharmProjects/PratikoAi-BE
   make dev
   ```

2. **Start Frontend**:
   ```bash
   cd /Users/micky/WebstormProjects/PratikoAiWebApp
   npm run dev
   ```

### Test Google OAuth

1. Navigate to `http://localhost:3000/signup` or `http://localhost:3000/signin`
2. Click "Continua con Google"
3. You should be redirected to Google's login page
4. After logging in with Google, you'll be redirected back and automatically logged into PratikoAI

### Test LinkedIn OAuth

1. Navigate to `http://localhost:3000/signup` or `http://localhost:3000/signin`
2. Click "Continua con LinkedIn"
3. You should be redirected to LinkedIn's authorization page
4. After authorizing, you'll be redirected back and automatically logged into PratikoAI

## 5. Troubleshooting

### Common Issues

1. **"OAuth is not configured" Error**
   - Ensure environment variables are set correctly
   - Restart the backend after adding environment variables

2. **Redirect URI Mismatch**
   - Make sure the redirect URI in your OAuth app settings exactly matches:
     - Development: `http://localhost:3000/auth/callback`
     - The protocol (http/https) must match exactly

3. **Popup Blocked**
   - Allow popups for localhost:3000 in your browser
   - The OAuth flow uses popups for better UX

4. **CORS Errors**
   - Ensure `ALLOWED_ORIGINS` in backend `.env` includes your frontend URL
   - Default should already include `http://localhost:3000`

### Verify OAuth is Working

Check the database after OAuth login:
```sql
psql "postgresql://aifinance:devpass@localhost:5432/aifinance"
SELECT id, email, name, provider, provider_id FROM "user" WHERE provider != 'email';
```

You should see OAuth users with their provider information.

## 6. Production Deployment

When deploying to production:

1. **Update OAuth App Settings**:
   - Add production redirect URIs to both Google and LinkedIn apps
   - Update privacy policy and terms of service URLs

2. **Environment Variables**:
   - Set production OAuth credentials
   - Update `FRONTEND_URL` to your production domain

3. **Security Considerations**:
   - Use HTTPS for all production URLs
   - Keep OAuth credentials secure and never commit them to git
   - Regularly rotate OAuth client secrets

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [LinkedIn OAuth Documentation](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication)
- [OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)