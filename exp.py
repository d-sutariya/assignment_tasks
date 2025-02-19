import smtplib
from config import Config  # Ensure Config has correct SMTP_SERVER, SMTP_PORT, GMAIL_USER, GMAIL_PASSWORD

try:
    # Instead of smtp.gmail.com, use the IPv4 address directly:
    with smtplib.SMTP("74.125.130.109", Config.SMTP_PORT) as server:
        # ...
        server.set_debuglevel(1)
        server.starttls()
        server.login(Config.GMAIL_USER, Config.GMAIL_PASSWORD)
        print("Connection successful!")
except Exception as e:
    print("Error during SMTP connection:", e)
