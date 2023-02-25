import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from app_config import EMAIL, PAS
from report import create_report
import sys
import os
########## Setting working directory ##########
image_path = os.getcwd() + '/strava-year-in-review/scripts/static/images/'

def send_email(receiver, subject, text_ver, html_ver, image_list):
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

    # Image stuff
    i = 1
    for image in image_list:
        fp = open(image, 'rb')
        msgImage = MIMEImage(fp.read())
        fp.close()
        # Define the image's ID as referenced above
        msgImage.add_header('Content-ID', f'<image{i}>')
        msg.attach(msgImage)
        i += 1


    try:
        server.sendmail(EMAIL, send_to, msg.as_string()) # from, to, message
    except Exception as ex:
        print('Unable to send message:', ex)

    server.quit()


def main():
    reciever = sys.argv[1]
    user_id = 12
    subject = 'Weekly Report'
    text = 'email report'
    bin_array = [0, 150, 160, 205]
    email_html, src1, src2, src3, src4 = create_report(bin_array=bin_array, user_id=user_id, athlete_id=24403919, start_date='2023-02-20', end_date='2023-02-25') # testing with my parameters
    image_li = [image_path + f'{user_id}_hr1.png', image_path + f'{user_id}_hr2.png', image_path + f'{user_id}_mileage.png', image_path + f'{user_id}_time.png']
    send_email(reciever, subject, text, email_html, image_li)


if __name__ == '__main__':
    main()


