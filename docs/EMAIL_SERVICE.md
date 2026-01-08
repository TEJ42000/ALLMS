# Email Service Documentation

This document describes the email service implementation for GDPR-related notifications.

## Overview

The email service supports multiple providers and is used for sending critical GDPR notifications such as account deletion confirmations.

## Supported Providers

### 1. Console (Development)

**Use for:** Development and testing

**Configuration:**
```bash
EMAIL_SERVICE_PROVIDER=console
```

**Behavior:**
- Logs email content to console
- No actual email sent
- Useful for development and debugging

**Pros:**
- ✅ No setup required
- ✅ No cost
- ✅ Immediate feedback in logs

**Cons:**
- ❌ No actual emails sent
- ❌ Cannot test email delivery
- ❌ Not suitable for production

---

### 2. SendGrid (Recommended for Production)

**Use for:** Production deployments

**Setup:**

1. **Create SendGrid Account**
   - Sign up at https://sendgrid.com
   - Verify your domain
   - Create an API key

2. **Install Dependencies**
   ```bash
   pip install sendgrid
   ```

3. **Configure Environment**
   ```bash
   EMAIL_SERVICE_PROVIDER=sendgrid
   SENDGRID_API_KEY=SG.your-api-key-here
   EMAIL_FROM_ADDRESS=noreply@yourdomain.com
   ```

4. **Store API Key Securely**
   ```bash
   # Google Secret Manager
   echo -n "SG.your-api-key" | gcloud secrets create sendgrid-api-key --data-file=-
   
   # Reference in Cloud Run
   --set-env-vars SENDGRID_API_KEY=projects/YOUR_PROJECT/secrets/sendgrid-api-key/versions/latest
   ```

**Pros:**
- ✅ Reliable delivery
- ✅ Good deliverability rates
- ✅ Email analytics
- ✅ Template support
- ✅ Easy setup

**Cons:**
- ❌ Costs money (free tier available)
- ❌ Requires domain verification

**Pricing:**
- Free tier: 100 emails/day
- Essentials: $19.95/month for 50,000 emails
- See https://sendgrid.com/pricing

---

### 3. AWS SES (Alternative for AWS Deployments)

**Use for:** AWS-based deployments or high-volume sending

**Setup:**

1. **Configure AWS SES**
   ```bash
   # Verify domain
   aws ses verify-domain-identity --domain yourdomain.com
   
   # Move out of sandbox (required for production)
   # Submit request in AWS Console
   ```

2. **Install Dependencies**
   ```bash
   pip install boto3
   ```

3. **Configure Environment**
   ```bash
   EMAIL_SERVICE_PROVIDER=ses
   AWS_SES_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   EMAIL_FROM_ADDRESS=noreply@yourdomain.com
   ```

4. **IAM Permissions**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ses:SendEmail",
           "ses:SendRawEmail"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

**Pros:**
- ✅ Very low cost
- ✅ High volume support
- ✅ Integrates with AWS ecosystem
- ✅ Good deliverability

**Cons:**
- ❌ Requires AWS account
- ❌ Sandbox mode by default
- ❌ More complex setup

**Pricing:**
- $0.10 per 1,000 emails
- Free tier: 62,000 emails/month (if sent from EC2)

---

## Email Types

### Account Deletion Confirmation

**Trigger:** User requests account deletion via `/api/gdpr/delete/request`

**Content:**
- Subject: "Confirm Account Deletion - ALLMS"
- Deletion token (30-minute expiry)
- Warning about data loss
- Instructions to complete deletion
- Security notice

**Template:** HTML + Plain text fallback

**Example:**
```python
from app.services.email_service import get_email_service

email_service = get_email_service()
success = await email_service.send_deletion_confirmation_email(
    to_email="user@example.com",
    user_id="user-123",
    token="abc123...",
    expiry=datetime.utcnow() + timedelta(minutes=30)
)
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMAIL_SERVICE_PROVIDER` | No | `console` | Email provider: `console`, `sendgrid`, `ses` |
| `EMAIL_FROM_ADDRESS` | No | `noreply@allms.example.com` | Sender email address |
| `SENDGRID_API_KEY` | If using SendGrid | - | SendGrid API key |
| `AWS_SES_REGION` | If using SES | `us-east-1` | AWS SES region |
| `AWS_ACCESS_KEY_ID` | If using SES | - | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | If using SES | - | AWS secret key |

### Example Configurations

**Development:**
```bash
EMAIL_SERVICE_PROVIDER=console
```

**Production with SendGrid:**
```bash
EMAIL_SERVICE_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.xxx
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
```

**Production with AWS SES:**
```bash
EMAIL_SERVICE_PROVIDER=ses
AWS_SES_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=xxx
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
```

---

## Testing

### Test Email Sending

```python
import asyncio
from datetime import datetime, timedelta
from app.services.email_service import get_email_service

async def test_email():
    email_service = get_email_service()
    
    success = await email_service.send_deletion_confirmation_email(
        to_email="test@example.com",
        user_id="test-user-123",
        token="test-token-abc123",
        expiry=datetime.utcnow() + timedelta(minutes=30)
    )
    
    print(f"Email sent: {success}")

asyncio.run(test_email())
```

### Test with Console Provider

```bash
# Set environment
export EMAIL_SERVICE_PROVIDER=console

# Run test
python3 test_email.py

# Check logs for email content
```

### Test with SendGrid

```bash
# Set environment
export EMAIL_SERVICE_PROVIDER=sendgrid
export SENDGRID_API_KEY=SG.your-key
export EMAIL_FROM_ADDRESS=noreply@yourdomain.com

# Run test
python3 test_email.py

# Check inbox for email
```

---

## Troubleshooting

### Email Not Sending

**Check:**
1. `EMAIL_SERVICE_PROVIDER` is set correctly
2. API keys are valid and not expired
3. Sender email is verified (SendGrid/SES)
4. Recipient email is valid
5. Check application logs for errors

**Common Issues:**

**SendGrid:**
- API key not set or invalid
- Sender email not verified
- Domain not verified
- API key permissions insufficient

**AWS SES:**
- Account in sandbox mode (can only send to verified emails)
- IAM permissions insufficient
- Region mismatch
- Sender email not verified

### Email Goes to Spam

**Solutions:**
1. Verify your domain with SPF/DKIM records
2. Use a professional sender address
3. Avoid spam trigger words
4. Include unsubscribe link (for marketing emails)
5. Maintain good sender reputation

### Rate Limiting

**SendGrid:**
- Free tier: 100 emails/day
- Paid plans: Higher limits

**AWS SES:**
- Sandbox: 200 emails/day, 1 email/second
- Production: 50,000 emails/day (can request increase)

---

## Security Best Practices

1. **Never commit API keys**
   - Use environment variables
   - Store in Secret Manager
   - Rotate regularly

2. **Validate email addresses**
   - Use Pydantic EmailStr
   - Check for disposable emails
   - Verify domain exists

3. **Rate limit email sending**
   - Prevent abuse
   - Avoid hitting provider limits
   - Monitor sending patterns

4. **Use HTTPS for links**
   - All links in emails should use HTTPS
   - Verify SSL certificates

5. **Include security notices**
   - Warn about phishing
   - Provide contact information
   - Include privacy policy link

---

## Monitoring

### Metrics to Track

1. **Email Delivery Rate**
   - Sent vs. delivered
   - Bounce rate
   - Spam complaints

2. **Email Open Rate**
   - Track opens (if enabled)
   - Click-through rate

3. **Provider Errors**
   - API errors
   - Rate limit hits
   - Authentication failures

### Logging

All email operations are logged:

```python
logger.info(f"Email sent successfully via SendGrid to {to_email}")
logger.error(f"Failed to send email to {to_email}: {error}")
```

Check logs:
```bash
# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.message=~'Email'" --limit 50
```

---

## Migration Guide

### From Console to SendGrid

1. Create SendGrid account and API key
2. Update environment variables
3. Test with a few emails
4. Monitor delivery rates
5. Gradually increase volume

### From SendGrid to AWS SES

1. Set up AWS SES and verify domain
2. Request production access (move out of sandbox)
3. Update environment variables
4. Test thoroughly
5. Switch over

---

## Related Documentation

- [GDPR Implementation Guide](GDPR_IMPLEMENTATION.md)
- [Environment Variables](ENVIRONMENT_VARIABLES.md)
- [Deployment Guide](GDPR_DEPLOYMENT.md)
- [Token Service](../app/services/token_service.py)

---

## Support

For email service issues:
- **Technical:** dev@allms.example.com
- **SendGrid Support:** https://support.sendgrid.com
- **AWS SES Support:** https://aws.amazon.com/ses/support

