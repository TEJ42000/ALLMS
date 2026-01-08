"""
Email Service for GDPR Notifications

Supports multiple email providers:
- SendGrid (recommended for production)
- AWS SES (alternative for AWS deployments)
- Console (development/testing)
"""

import logging
import os
from datetime import datetime
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class EmailProvider(str, Enum):
    """Supported email providers."""
    CONSOLE = "console"
    SENDGRID = "sendgrid"
    SES = "ses"


class EmailService:
    """Email service for sending GDPR-related emails."""
    
    def __init__(self):
        """Initialize email service based on environment configuration."""
        self.provider = EmailProvider(os.getenv('EMAIL_SERVICE_PROVIDER', 'console'))
        
        if self.provider == EmailProvider.SENDGRID:
            self._init_sendgrid()
        elif self.provider == EmailProvider.SES:
            self._init_ses()
        else:
            logger.info("Using console email provider (development mode)")
    
    def _init_sendgrid(self):
        """Initialize SendGrid client."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
            if not self.sendgrid_api_key:
                raise ValueError("SENDGRID_API_KEY not set in environment")
            
            self.sendgrid_client = SendGridAPIClient(self.sendgrid_api_key)
            self.sendgrid_mail = Mail
            logger.info("SendGrid email service initialized")
            
        except ImportError:
            logger.error("SendGrid library not installed. Install with: pip install sendgrid")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize SendGrid: {e}")
            raise
    
    def _init_ses(self):
        """Initialize AWS SES client."""
        try:
            import boto3
            
            self.ses_region = os.getenv('AWS_SES_REGION', 'us-east-1')
            self.ses_client = boto3.client('ses', region_name=self.ses_region)
            logger.info(f"AWS SES email service initialized (region: {self.ses_region})")
            
        except ImportError:
            logger.error("Boto3 library not installed. Install with: pip install boto3")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize AWS SES: {e}")
            raise
    
    async def send_deletion_confirmation_email(
        self,
        to_email: str,
        user_id: str,
        token: str,
        expiry: datetime
    ) -> bool:
        """Send account deletion confirmation email.
        
        Args:
            to_email: Recipient email address
            user_id: User ID
            token: Deletion confirmation token
            expiry: Token expiry datetime
            
        Returns:
            True if email sent successfully, False otherwise
        """
        subject = "Confirm Account Deletion - ALLMS"
        
        expiry_str = expiry.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #e74c3c; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .token-box {{ background: white; border: 2px solid #e74c3c; padding: 15px; margin: 20px 0; font-family: monospace; font-size: 14px; word-break: break-all; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #777; font-size: 12px; margin-top: 20px; }}
                .button {{ display: inline-block; background: #e74c3c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ Account Deletion Request</h1>
                </div>
                <div class="content">
                    <p>Dear User,</p>
                    
                    <p>You have requested to delete your ALLMS account. This action is <strong>permanent and cannot be undone</strong>.</p>
                    
                    <div class="warning">
                        <strong>⚠️ Warning:</strong> Deleting your account will:
                        <ul>
                            <li>Remove all your quiz results and progress</li>
                            <li>Delete all AI tutor conversations</li>
                            <li>Remove all uploaded study materials</li>
                            <li>Erase all personal data after 30 days</li>
                        </ul>
                    </div>
                    
                    <p><strong>To confirm account deletion, use the following token:</strong></p>
                    
                    <div class="token-box">
                        {token}
                    </div>
                    
                    <p><strong>Token expires:</strong> {expiry_str}</p>
                    
                    <p>To complete the deletion:</p>
                    <ol>
                        <li>Go to your <a href="https://allms.example.com/privacy-dashboard">Privacy Dashboard</a></li>
                        <li>Click "Delete My Account"</li>
                        <li>Enter the token above</li>
                        <li>Confirm deletion</li>
                    </ol>
                    
                    <p><strong>If you did not request this deletion:</strong></p>
                    <ul>
                        <li>Ignore this email - your account will remain active</li>
                        <li>Change your password immediately</li>
                        <li>Contact support if you suspect unauthorized access</li>
                    </ul>
                    
                    <p>For security reasons, this token can only be used once and will expire in 30 minutes.</p>
                    
                    <p>Best regards,<br>ALLMS Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>ALLMS - AI-Powered Learning Management System</p>
                    <p><a href="https://allms.example.com/privacy-policy">Privacy Policy</a> | <a href="https://allms.example.com/terms-of-service">Terms of Service</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_body = f"""
        Account Deletion Request - ALLMS
        
        Dear User,
        
        You have requested to delete your ALLMS account. This action is permanent and cannot be undone.
        
        WARNING: Deleting your account will:
        - Remove all your quiz results and progress
        - Delete all AI tutor conversations
        - Remove all uploaded study materials
        - Erase all personal data after 30 days
        
        To confirm account deletion, use the following token:
        
        {token}
        
        Token expires: {expiry_str}
        
        To complete the deletion:
        1. Go to your Privacy Dashboard: https://allms.example.com/privacy-dashboard
        2. Click "Delete My Account"
        3. Enter the token above
        4. Confirm deletion
        
        If you did not request this deletion:
        - Ignore this email - your account will remain active
        - Change your password immediately
        - Contact support if you suspect unauthorized access
        
        For security reasons, this token can only be used once and will expire in 30 minutes.
        
        Best regards,
        ALLMS Team
        
        ---
        This is an automated message. Please do not reply to this email.
        ALLMS - AI-Powered Learning Management System
        Privacy Policy: https://allms.example.com/privacy-policy
        Terms of Service: https://allms.example.com/terms-of-service
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        from_email: Optional[str] = None
    ) -> bool:
        """Send email using configured provider.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            from_email: Sender email (optional, uses default)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not from_email:
            from_email = os.getenv('EMAIL_FROM_ADDRESS', 'noreply@allms.example.com')
        
        try:
            if self.provider == EmailProvider.SENDGRID:
                return await self._send_sendgrid(to_email, from_email, subject, html_body, text_body)
            elif self.provider == EmailProvider.SES:
                return await self._send_ses(to_email, from_email, subject, html_body, text_body)
            else:
                return await self._send_console(to_email, from_email, subject, html_body, text_body)
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
            return False
    
    async def _send_sendgrid(
        self,
        to_email: str,
        from_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """Send email via SendGrid."""
        try:
            message = self.sendgrid_mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_body,
                plain_text_content=text_body
            )
            
            response = self.sendgrid_client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully via SendGrid to {to_email}")
                return True
            else:
                logger.error(f"SendGrid returned status {response.status_code}: {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"SendGrid error: {e}", exc_info=True)
            return False
    
    async def _send_ses(
        self,
        to_email: str,
        from_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """Send email via AWS SES."""
        try:
            response = self.ses_client.send_email(
                Source=from_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                    }
                }
            )
            
            logger.info(f"Email sent successfully via SES to {to_email} (MessageId: {response['MessageId']})")
            return True
            
        except Exception as e:
            logger.error(f"AWS SES error: {e}", exc_info=True)
            return False
    
    async def _send_console(
        self,
        to_email: str,
        from_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """Log email to console (development mode)."""
        logger.info("=" * 80)
        logger.info("[EMAIL - CONSOLE MODE]")
        logger.info(f"From: {from_email}")
        logger.info(f"To: {to_email}")
        logger.info(f"Subject: {subject}")
        logger.info("-" * 80)
        logger.info("Plain Text Body:")
        logger.info(text_body)
        logger.info("=" * 80)
        return True


# Global email service instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

