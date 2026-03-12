"""
CallCoach CRM - Email Service (Hostinger SMTP)
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL, SMTP_FROM_NAME

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, user_name: str, reset_link: str) -> bool:
    """Send a password reset email via Hostinger SMTP (SSL, port 465)."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("SMTP credentials not configured. Cannot send password reset email.")
        return False

    subject = "Reset Your CallCoach Password"
    from_addr = SMTP_FROM_EMAIL or SMTP_USER

    # HTML email body - SBA branded (black + orange #E88725)
    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#000000;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#000000;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#0A0A0A;border-radius:16px;overflow:hidden;border:1px solid #1a1a1a;">
          <!-- Header -->
          <tr>
            <td style="background-color:#E88725;padding:32px 40px;text-align:center;">
              <h1 style="margin:0;color:#000000;font-size:24px;font-weight:800;letter-spacing:-0.5px;">CallCoach CRM</h1>
              <p style="margin:6px 0 0;color:rgba(0,0,0,0.6);font-size:12px;font-weight:500;letter-spacing:1px;text-transform:uppercase;">by Skin Business Accelerator</p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <h2 style="margin:0 0 16px;color:#ffffff;font-size:20px;font-weight:600;">Password Reset Request</h2>
              <p style="margin:0 0 16px;color:#888888;font-size:15px;line-height:1.6;">
                Hi {user_name},
              </p>
              <p style="margin:0 0 28px;color:#888888;font-size:15px;line-height:1.6;">
                We received a request to reset your password. Click the button below to set a new password. This link expires in 1 hour.
              </p>
              <table cellpadding="0" cellspacing="0" style="margin:0 0 28px;">
                <tr>
                  <td style="background-color:#E88725;border-radius:10px;padding:14px 36px;">
                    <a href="{reset_link}" style="color:#000000;text-decoration:none;font-size:15px;font-weight:700;display:inline-block;">
                      Reset Password
                    </a>
                  </td>
                </tr>
              </table>
              <p style="margin:0 0 8px;color:#555555;font-size:13px;line-height:1.6;">
                If you did not request this, you can safely ignore this email. Your password will not change.
              </p>
              <p style="margin:0;color:#555555;font-size:13px;line-height:1.6;">
                If the button does not work, copy and paste this link into your browser:
              </p>
              <p style="margin:8px 0 0;word-break:break-all;">
                <a href="{reset_link}" style="color:#E88725;font-size:12px;">{reset_link}</a>
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px;border-top:1px solid #1a1a1a;text-align:center;">
              <p style="margin:0;color:#444444;font-size:12px;">
                CallCoach CRM by Skin Business Accelerator
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    # Plain text fallback
    text_body = f"""Hi {user_name},

We received a request to reset your CallCoach password.

Reset your password by visiting this link (expires in 1 hour):
{reset_link}

If you did not request this, you can safely ignore this email.

-- CallCoach CRM by Skin Business Accelerator"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_FROM_NAME} <{from_addr}>"
        msg["To"] = to_email

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(from_addr, [to_email], msg.as_string())

        logger.info(f"Password reset email sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {to_email}: {e}")
        return False
