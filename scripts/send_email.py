import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from app_config import EMAIL, PAS
from report import create_report
import sys
import os
import sql_functions
import pendulum
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


def generate_and_send(user_id, start_date, end_date):
    #user_id = user_id
    package = sql_functions.get_user_package(user_id)
    reciever = package['email']
    bin_array = package['bin_array']
    athlete_id = package['athlete_id']

    subject = 'Weekly Report'
    text = 'email report'
    email_html, src1, src2, src3, src4 = create_report(bin_array=bin_array, user_id=user_id, athlete_id=athlete_id, start_date=start_date, end_date=end_date) # testing with my parameters
    image_li = [image_path + f'{user_id}_hr1.html', image_path + f'{user_id}_hr2.html', image_path + f'{user_id}_mileage.html', image_path + f'{user_id}_time.html']
    send_email(reciever, subject, text, email_html, image_li)

def email_all():
    ##### WEEK INFORMATION #####
    today = pendulum.now()
    beginning = today.start_of('week')
    ending = today.end_of('week')

    week_start = beginning.strftime("%Y-%m-%d")
    week_end = ending.strftime("%Y-%m-%d")

    #sql = 'SELECT user_id FROM users WHERE email IS NOT NULL;'
    sql = 'SELECT user_id FROM users WHERE user_id = 12;' # temp for testing 
    user_id_list = sql_functions.local_sql_to_df(sql)['user_id']

    for user_id in user_id_list:
        generate_and_send(user_id, week_start, week_end)


if __name__ == '__main__':
    email_all()


