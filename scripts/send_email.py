import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from os.path import basename
from app_config import EMAIL, PAS
from report import email_html
import sys

def send_email(receiver, subject, text_ver, html_ver):
    send_to = receiver

    smtp = "smtp.gmail.com"
    port = 587
    server = smtplib.SMTP(smtp, port)  # Send the message via local SMTP server. server = smtplib.SMTP('localhost')
    server.starttls()
    server.login(EMAIL, PAS) # login


    msg = MIMEMultipart('alternative')  # create message to be emailed
    msg['From'] = EMAIL
    msg['To'] = send_to
    msg['Subject'] = subject

    text = text_ver
    html = html_ver
    
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    
    msg.attach(part1)
    msg.attach(part2)

    try:
        server.sendmail(EMAIL, send_to, msg.as_string()) # from, to, message
    except Exception as ex:
        print('Unable to send message:', ex)

    server.quit()


if __name__ == '__main__':
    reciever = sys.argv[1]
    subject = 'Weekly Report'
    text = 'email report'
    send_email(reciever, subject, text, email_html)
