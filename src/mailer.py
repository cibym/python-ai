import markdown
import resend

class Mailer:
    def __init__(self, api_key: str):
        resend.api_key = api_key

    def send_digest(self, recipient_email: str, markdown_content: str):
        html_body = markdown.markdown(markdown_content, extensions=['tables'])
        styled_html = f"""
        <html>
        <body style="font-family: sans-serif; line-height: 1.6; max-width: 680px; margin: auto; padding: 20px;">
          <h2>☕ Daily Tech & Market Pulse</h2>
          {html_body}
        </body>
        </html>
        """
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": recipient_email,
            "subject": "☕ Daily Market & Tech Pulse",
            "html": styled_html
        })
