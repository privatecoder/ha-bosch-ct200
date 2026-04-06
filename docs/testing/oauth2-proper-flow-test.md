# Testing OAuth2 with AbstractOAuth2FlowHandler

This document explains how to test the proper OAuth2 implementation using Home Assistant's built-in OAuth2 system.

## What We're Testing

We want to see if we can use Home Assistant's `AbstractOAuth2FlowHandler` with the PointT API, despite the redirect URI mismatch.

### The Challenge

**Current Implementation (Manual):**
- Client ID: `762162C0-FA2D-4540-AE66-6489F189FADC` (from mobile app)
- Redirect URI: `com.bosch.tt.dashtt.pointt://app/login` (mobile app scheme)
- Flow: User copies authorization code manually

**Desired Implementation (Proper OAuth2):**
- Same Client ID (or new one if available)
- Redirect URI: `https://my.home-assistant.io/redirect/oauth` (HA's standard)
- Flow: Automatic redirect back to HA

### Expected Outcome

**Most Likely Result:** ❌ OAuth server rejects request because redirect URI doesn't match

**Why:** The client ID `762162C0-FA2D-4540-AE66-6489F189FADC` is registered with Bosch for the mobile app redirect URI. When we try to use HA's redirect URI, Bosch's OAuth server will reject it with an error like:
- `invalid_request: redirect_uri mismatch`
- `unauthorized_client`

**Possible Success:** ✅ If Bosch registered multiple redirect URIs for this client

## How to Test

### Step 1: Enable Test Config Flow

Edit `custom_components/bosch/__init__.py` and find the line:
```python
from .config_flow import BoschFlowHandler
```

Temporarily change it to:
```python
from .config_flow_oauth2_test import BoschOAuth2FlowHandler as BoschFlowHandler
```

This will use the test OAuth2 flow instead of the manual flow.

### Step 2: Configure Application Credentials

1. Go to **Settings → Devices & Services**
2. Click the **3-dot menu** (top right) → **Application Credentials**
3. Click **Add Application Credential**
4. Fill in:
   - **Integration**: Bosch CT200
   - **Client ID**: `762162C0-FA2D-4540-AE66-6489F189FADC`
   - **Client Secret**: *(Leave empty or use a dummy value - this client doesn't use client secrets)*
5. Click **Create**

### Step 3: Copy Integration to HA

```bash
cp -r custom_components/bosch ~/.homeassistant/custom_components/
```

### Step 4: Restart Home Assistant

Restart HA completely to load the new OAuth2 flow.

### Step 5: Try Adding Integration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **"Bosch"**
3. Click to add
4. You should see the OAuth2 authorization flow start

### Expected Behavior

**Scenario A: Redirect URI Mismatch (Most Likely)**

When HA tries to start the OAuth2 flow, you'll see an error:
- In the browser: `invalid_request` or `redirect_uri mismatch`
- In HA logs: OAuth2 flow fails with error from Bosch server

This means the client doesn't support HA's redirect URI.

**Scenario B: Success (Unlikely)**

The OAuth flow completes automatically:
1. Browser opens to Bosch SingleKey ID login
2. You log in
3. Browser redirects back to HA automatically
4. Integration configured successfully

This would mean Bosch registered multiple redirect URIs for this client.

## Debugging

### Check HA Logs

```bash
tail -f ~/.homeassistant/home-assistant.log | grep bosch
```

Look for:
- OAuth2 flow initialization messages
- Error messages from Bosch OAuth server
- Token exchange attempts

### Check OAuth2 Request

You can inspect the OAuth2 authorization URL being generated. It should look like:

```
https://singlekey-id.com/auth/connect/authorize?
  client_id=762162C0-FA2D-4540-AE66-6489F189FADC
  &redirect_uri=https://my.home-assistant.io/redirect/oauth
  &response_type=code
  &scope=openid+email+profile+offline_access+...
  &code_challenge=...
  &code_challenge_method=S256
```

The key parameter is `redirect_uri` - if this doesn't match what Bosch expects, the request will fail.

## Results Documentation

### Test Environment
- Home Assistant version: 2024+
- Integration version: 0.28.2
- Date tested: 2026-02-17

### Observations

1. **OAuth2 flow started?** Yes - HA redirected to SingleKey ID
2. **Error message:** "Fehlkonfigurierte Anwendung" (Misconfigured Application)
3. **Browser behavior:** Redirected to error page at singlekey-id.com/errors/misconfigured-application
4. **Error URL:** Contains errorId parameter, indicating OAuth server rejection

### Conclusion

**Result: ❌ Keep manual PKCE flow**

The test confirms that Bosch's OAuth server **rejects** Home Assistant's redirect URI (`https://my.home-assistant.io/redirect/oauth`) when used with the mobile app's client ID.

**Why this happened:**
- Client ID `762162C0-FA2D-4540-AE66-6489F189FADC` is registered only for `com.bosch.tt.dashtt.pointt://app/login`
- OAuth servers validate that redirect URIs match registered values
- Using HA's redirect URI with mobile app credentials triggers "misconfigured application" error

**Decision:** Continue with current manual PKCE implementation (user copies authorization code). This approach works perfectly with the reverse-engineered mobile credentials.

## Alternative Solutions

If the redirect URI mismatch fails (expected), we have options:

### Option 1: Keep Current Manual Flow ⭐ (Current)
- Works with extracted mobile credentials
- User copies code manually
- Functional but not ideal UX

### Option 2: Request Official API Access
- Contact Bosch to register official application
- Get Client ID with HA redirect URI
- Use proper OAuth2 flow
- Best solution but requires Bosch cooperation

### Option 3: Hybrid Approach
- Keep manual flow as default
- Document how users can use Option 2 if they have official credentials
- Support both flows in config

## Conclusion

This test helps us understand whether the proper OAuth2 approach is viable with the current extracted credentials. The most likely outcome is that it won't work due to redirect URI mismatch, which validates our current manual implementation approach.

However, if it does work, it would provide a much better user experience and we should migrate to it fully.
