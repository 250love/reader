import smtplib
from email.mime.text import MIMEText

from flask import current_app


def send_email_verification_code(to_email: str, code: str) -> bool:
    host = current_app.config["SMTP_HOST"]
    port = current_app.config["SMTP_PORT"]
    username = current_app.config["SMTP_USERNAME"]
    password = current_app.config["SMTP_PASSWORD"]
    from_email = current_app.config["SMTP_FROM_EMAIL"]
    use_tls = current_app.config["SMTP_USE_TLS"]

    if not all([host, port, username, password, from_email]):
        return False

    content = (
        "Your verification code is: "
        f"{code}\n\n"
        "This code will expire in "
        f"{current_app.config['EMAIL_CODE_EXPIRE_MINUTES']} minutes."
    )

    message = MIMEText(content, "plain", "utf-8")
    message["Subject"] = "Paper Reader verification code"
    message["From"] = from_email
    message["To"] = to_email

    with smtplib.SMTP(host, port, timeout=15) as server:
        if use_tls:
            server.starttls()
        server.login(username, password)
        server.sendmail(from_email, [to_email], message.as_string())

    return True

