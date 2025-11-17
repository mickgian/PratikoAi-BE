# Slack Integration Setup for PratikoAI Subagent System

This guide explains how to set up Slack notifications for the PratikoAI multi-agent system.

## Overview

The PratikoAI subagent system uses Slack for real-time notifications including:
- **Architect veto alerts** (immediate, critical priority)
- **Scrum Master progress updates** (every 2 hours)
- **Task completion notifications**
- **Blocker alerts and escalations**
- **Daily standups and sprint summaries**

## Prerequisites

- Slack workspace (create one at https://slack.com if you don't have one)
- Admin access to your Slack workspace
- Access to the PratikoAI backend repository

---

## Step 1: Create Slack Workspace (if needed)

If you don't have a Slack workspace:

1. Go to https://slack.com/get-started
2. Click **"Create a new workspace"**
3. Follow the prompts to set up your workspace
4. Choose a workspace name (e.g., "PratikoAI Team")

---

## Step 2: Create Slack Channels

**IMPORTANT:** Slack channels do NOT auto-create when webhooks post to them. You MUST manually create these channels first.

Create dedicated channels for different notification types:

1. **Open Slack** and click the "+" next to "Channels"

2. **Create #architect-alerts channel:**
   - Click "Create a channel"
   - Name: `architect-alerts` (must match exactly, including the #)
   - Description: `Critical architecture veto notifications from PratikoAI Architect`
   - Make it **Public** (or Private if you prefer)
   - Click "Create"

3. **Create #scrum-updates channel:**
   - Click "Create a channel"
   - Name: `scrum-updates` (must match exactly, including the #)
   - Description: `2-hour progress updates from PratikoAI Scrum Master`
   - Make it **Public** (or Private if you prefer)
   - Click "Create"

**Note:** The channel names in `.env` (SLACK_CHANNEL_ARCHITECT and SLACK_CHANNEL_SCRUM) must match the channels you created in Slack.

---

## Step 3: Create Incoming Webhooks (Two Required)

**IMPORTANT:** Modern Slack app webhooks are locked to the channel selected during creation and cannot override it programmatically. You **must create two separate webhooks** - one for each channel.

### For Slack (Free/Pro/Enterprise Grid):

1. **Go to your Slack App page:**
   - Visit: https://api.slack.com/apps
   - Click **"Create New App"** (or select your existing PratikoAI app)

2. **If creating a new app:**
   - Select **"From scratch"**
   - App Name: `PratikoAI Notifications`
   - Workspace: Select your workspace
   - Click **"Create App"**

3. **Enable Incoming Webhooks:**
   - In the left sidebar, click **"Incoming Webhooks"**
   - Toggle **"Activate Incoming Webhooks"** to **ON**

4. **Create Webhook #1 for #architect-alerts:**
   - Scroll down and click **"Add New Webhook to Workspace"**
   - Select the **#architect-alerts** channel
   - Click **"Allow"**
   - Copy the webhook URL (you'll see something like `https://hooks.slack.com/services/T00000000/B11111111/XXXXXXXXXXXXXXXXXXXX`)
   - **Save this URL** - this is your `SLACK_WEBHOOK_URL_ARCHITECT`

5. **Create Webhook #2 for #scrum-updates:**
   - Click **"Add New Webhook to Workspace"** again
   - Select the **#scrum-updates** channel
   - Click **"Allow"**
   - Copy the webhook URL (you'll see something like `https://hooks.slack.com/services/T00000000/B22222222/YYYYYYYYYYYYYYYYYYYY`)
   - **Save this URL** - this is your `SLACK_WEBHOOK_URL_SCRUM`

**Why two webhooks?** Modern Slack app webhooks ignore the `"channel"` parameter in API requests. Each webhook is permanently bound to the channel you selected during creation. To send to different channels, you need separate webhooks.

---

## Step 4: Configure Environment Variables

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file:**
   ```bash
   nano .env  # or use your preferred editor
   ```

3. **Add/Update Slack configuration:**
   ```bash
   # Slack Integration (for Subagent Notifications)
   # You need TWO separate webhooks - one for each channel
   SLACK_WEBHOOK_URL_ARCHITECT=https://hooks.slack.com/services/T00000000/B11111111/XXXXXXXXXXXXXXXXXXXX
   SLACK_WEBHOOK_URL_SCRUM=https://hooks.slack.com/services/T00000000/B22222222/YYYYYYYYYYYYYYYYYYYY
   SLACK_ENABLED=true
   ```

4. **Replace the webhook URLs** with the actual URLs you copied in Step 3:
   - `SLACK_WEBHOOK_URL_ARCHITECT` = URL for #architect-alerts channel
   - `SLACK_WEBHOOK_URL_SCRUM` = URL for #scrum-updates channel

5. **Save the file** (Ctrl+X, then Y, then Enter in nano)

---

## Step 5: Test the Integration

Test that Slack notifications are working:

1. **Run the test script:**
   ```bash
   python scripts/test_slack_notifications.py
   ```

2. **Check Slack:**
   - Go to your **#scrum-updates** channel
   - You should see test notifications appear

3. **Expected test messages:**
   - ✅ Architect veto alert (critical, red)
   - ✅ Scrum progress update (informational, green)
   - ✅ Task completion notification
   - ✅ Blocker alert (warning, orange)

4. **If messages don't appear:**
   - Verify `SLACK_WEBHOOK_URL` is correct in `.env`
   - Verify `SLACK_ENABLED=true` in `.env`
   - Check the test script output for errors
   - Verify the webhook is still active at https://api.slack.com/apps

---

## Step 6: Verify Configuration

1. **Check configuration is loaded:**
   ```bash
   python -c "from app.core.config import config; print(f'Slack enabled: {config.SLACK_ENABLED}'); print(f'Webhook: {config.SLACK_WEBHOOK_URL[:50]}...')"
   ```

2. **Expected output:**
   ```
   Slack enabled: True
   Webhook: https://hooks.slack.com/services/T00000000/B0...
   ```

---

## Step 7: Production Deployment

When deploying to QA/Preprod/Production:

1. **Create separate Slack channels for each environment:**
   - `#architect-alerts-qa`
   - `#architect-alerts-preprod`
   - `#architect-alerts-prod`
   - `#scrum-updates-qa`
   - `#scrum-updates-preprod`
   - `#scrum-updates-prod`

2. **Create separate webhooks** for each environment

3. **Configure environment-specific .env files:**
   - `.env.qa` - QA webhook
   - `.env.preprod` - Preprod webhook
   - `.env.production` - Production webhook

---

## Notification Examples

### Architect Veto Alert
```
🛑 ARCHITECT VETO EXERCISED

Task: DEV-BE-XX: Switch to Qdrant
Proposed By: Backend Expert
Veto Time: 2025-11-17 14:30 CET

Veto Reason: Violates ADR-003 (pgvector over Pinecone)
Violated Principle: ADR-003 - Vector database choice
Risk Introduced: $2,400/year cost increase, GDPR compliance risk

Alternative Approach: Optimize existing pgvector indexes (HNSW upgrade)

- PratikoAI Architect
```

### Scrum Progress Update
```
📊 PROGRESS UPDATE - 14:00 CET

Active Sprint: Sprint 1
Progress: 5/12 tasks (42%)

🔄 IN PROGRESS:
• DEV-BE-67: Migrate FAQ Embeddings (Backend Expert) - 8 hours, 60% complete
• DEV-BE-Test: Increase test coverage (Test Generation) - 16 hours, 40% complete

✅ COMPLETED TODAY:
• DEV-BE-71: Disable emoji in responses

⏳ NEXT UP:
• DEV-BE-76: Fix cache key

⚠️ BLOCKERS: None

Velocity: 2.5 points/day (target: 2.0)
Sprint status: ✅ ON TRACK

- PratikoAI Scrum Master
```

---

## Troubleshooting

### Issue: Notifications not appearing in Slack

**Solution 1: Verify channels exist**
- Go to your Slack workspace
- Verify `#architect-alerts` channel exists
- Verify `#scrum-updates` channel exists
- Channel names must match EXACTLY (including the # symbol)
- If channels don't exist, create them (see Step 2 above)

**Solution 2: Verify webhooks are active**
```bash
# Test architect webhook
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test from Architect webhook"}' \
  YOUR_ARCHITECT_WEBHOOK_URL

# Test scrum webhook
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test from Scrum webhook"}' \
  YOUR_SCRUM_WEBHOOK_URL
```
- Check #architect-alerts channel - you should see the first test message
- Check #scrum-updates channel - you should see the second test message
- If messages go to wrong channels, recreate the webhooks

**Solution 3: Check .env file**
- Ensure `SLACK_ENABLED=true`
- Ensure `SLACK_WEBHOOK_URL_ARCHITECT` has no trailing spaces
- Ensure `SLACK_WEBHOOK_URL_SCRUM` has no trailing spaces
- Ensure both webhook URLs start with `https://hooks.slack.com/services/`
- Restart the application after changing .env

**Solution 4: Check application logs**
```bash
docker-compose logs app | grep -i slack
```
- Look for error messages related to Slack
- Common error: "channel_not_found" means the channel doesn't exist in Slack

### Issue: Wrong channel receiving notifications

**Common Cause:** Modern Slack app webhooks are locked to the channel selected during webhook creation.

**Solution:**
1. Verify both `#architect-alerts` and `#scrum-updates` channels exist in Slack
2. Delete the existing webhooks from https://api.slack.com/apps → Your App → Incoming Webhooks
3. Create two new webhooks:
   - Webhook 1: Select **#architect-alerts** channel → Copy URL to `SLACK_WEBHOOK_URL_ARCHITECT`
   - Webhook 2: Select **#scrum-updates** channel → Copy URL to `SLACK_WEBHOOK_URL_SCRUM`
4. Update your `.env` file with both webhook URLs
5. Restart the application

**Note:** You cannot change which channel a webhook posts to after creation. The channel is permanently bound to the webhook.

### Issue: Webhook expired or revoked

**Solution:**
1. Go to https://api.slack.com/apps
2. Select your **PratikoAI Notifications** app
3. Click **"Incoming Webhooks"**
4. Click **"Add New Webhook to Workspace"**
5. Select the channel and allow
6. Copy new webhook URL to `.env`
7. Restart application

---

## Security Considerations

### Webhook URL is Sensitive
- **Never commit** `.env` files to git (already in `.gitignore`)
- **Rotate webhooks** if accidentally exposed
- **Use different webhooks** for dev/qa/prod

### Webhook Permissions
- Webhooks can only POST messages, cannot read messages
- Webhooks are tied to specific channels
- Revoke webhooks if no longer needed

---

## Advanced Configuration

### Understanding the Two-Webhook Architecture

**Why is this necessary?**

Modern Slack app webhooks (created via api.slack.com/apps) have a critical limitation:
- The `"channel"` parameter in JSON payloads is **completely ignored**
- Each webhook is **permanently locked** to the channel selected during creation
- There is NO way to override this programmatically

**Previous approach (doesn't work):**
```python
# This doesn't work with modern webhooks!
payload = {"channel": "#architect-alerts", "text": "Message"}
```

**Current approach (works):**
- Architect notifications → Use `SLACK_WEBHOOK_URL_ARCHITECT` (locked to #architect-alerts)
- Scrum notifications → Use `SLACK_WEBHOOK_URL_SCRUM` (locked to #scrum-updates)

**Alternative:** Use legacy Incoming Webhooks app (allows channel override) or Slack Web API with bot tokens (most flexible but requires more setup).

### Slack App Customization

Customize the app appearance:

1. Go to https://api.slack.com/apps
2. Select **PratikoAI Notifications** app
3. Click **"Basic Information"**
4. Under **"Display Information"**:
   - Add app icon (use PratikoAI logo)
   - Set short description
   - Choose background color

---

## Support

For issues:
- Check Slack API documentation: https://api.slack.com/messaging/webhooks
- Review `app/services/slack_notification_service.py` code
- Run test script with debugging: `python scripts/test_slack_notifications.py`

---

**Last Updated:** 2025-11-17
**Maintained By:** PratikoAI Development Team
