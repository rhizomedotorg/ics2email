import requests
import smtplib
import sqlite3
import yaml

from email.message import EmailMessage
from email.utils import make_msgid, formatdate
from ics import Calendar
from os import path
from re import sub
from slugify import slugify


smtp_url = None
email_addresses = []
smtp_credentials = ()
calendar_url = ''


def get_smtp_session():
    s = smtplib.SMTP_SSL(smtp_url)
    s.login(*smtp_credentials)
    return s


def send_email(to, subj, body, attachment=None, smtp_session=get_smtp_session):
    msg = EmailMessage()
    msg['Subject'] = subj
    msg['From'] = 'WBSG Rhizome <dev@rhizome.org>'
    msg['To'] = to
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain='rhizome.org')
    msg.add_header('List-Unsubscribe', '<mailto:dev@rhizome.org?subject=wbsg-ics2email-unsubscribe>')

    msg.set_content(sub('<[^<]+?>', '', body))
    msg.add_alternative(body, subtype='html')

    if attachment:
        msg.add_attachment(cal_template.format(attachment.serialize()).encode('utf-8'), maintype='text', subtype='calendar',
                           filename=f"{slugify(attachment.name)}.ics")

    with smtp_session() as session:
        session.send_message(msg)


if __name__ == '__main__':
    # load config file
    if not path.exists('config.yaml'):
        raise Exception('config.yaml not found')

    data = yaml.load(open('config.yaml', 'r'), Loader=yaml.FullLoader)

    email_addresses = data.get('recipients')
    smtp_url = data.get('smtp-url')
    smtp_credentials = data.get('smtp-credentials')
    calendar_url = data.get('ics-url')

    cal_template = '''
    BEGIN:VCALENDAR
    VERSION:2.0
    METHOD:PUBLISH
    {}
    END:VCALENDAR'''


    # db connection
    con = sqlite3.connect("calendar-data.db")
    cur = con.cursor()

    # create db table if it doesn't already exist
    cur.execute("CREATE TABLE IF NOT EXISTS ics_events (uid TEXT, created TEXT, last_modified TEXT)")
    con.commit()


    # load known events from database
    known_events = {}
    for row in cur.execute("SELECT uid, created, last_modified FROM ics_events"):
        known_events[row[0]] = {
            'created': row[1],
            'last_modified': row[2]
        }

    c = Calendar(requests.get(calendar_url).text)

    for event in c.events:
        if event.uid not in known_events:
            print(f'New event: {event.name}')

            for address in email_addresses:
                send_email(
                    address,
                    f'New WBSG Event: {event.name}',
                    f'''<h1>New WBSG Event: {event.name}</h1>
                        <time datetime="{event.begin.format()}"><strong>start:</strong> {event.begin.format()}</time><BR>
                        <time datetime="{event.end.format()}"><strong>end:</strong> {event.end.format()}</time><BR>
                        {f'<a href="{event.url}">{event.url}</a><BR><BR>' if event.url else '<BR>'}
                        <p>{event.description}</p>''',
                    event)

            cur.execute("INSERT INTO ics_events VALUES (?, ?, ?)", (event.uid, event.created.format(), event.last_modified.format()))
            con.commit()

        elif known_events[event.uid]['last_modified'] != event.last_modified.format():
            print(f'Event modified: {event.name}')

            for address in email_addresses:
                send_email(
                    address,
                    f'Updated WBSG Event: {event.name}',
                    f'''<h1>Updated WBSG Event: {event.name}</h1>
                        <time datetime="{event.begin.format()}"><strong>start:</strong> {event.begin.format()}</time><BR>
                        <time datetime="{event.end.format()}"><strong>end:</strong> {event.end.format()}</time><BR>
                        {f'<a href="{event.url}">{event.url}</a><BR><BR>' if event.url else '<BR>'}
                        <p>{event.description}</p>''',
                    event)

            # update last_modified record
            cur.execute("UPDATE ics_events SET last_modified = ? WHERE uid = ?", (event.last_modified.format(), event.uid))
            con.commit()