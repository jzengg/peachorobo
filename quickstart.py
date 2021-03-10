import os.path
from datetime import timedelta

import parsedatetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
from pytz import timezone

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    else:
        print("help")
    # If there are no (valid) credentials available, let the user log in.
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    service = build("calendar", "v3", credentials=creds)

    # Call the Calendar API
    print("Creating")
    cal = parsedatetime.Calendar()

    datetime_obj, status = cal.parseDT(
        datetimeString="tomorrow at 3pm", tzinfo=timezone("US/Eastern")
    )
    end_time = datetime_obj + timedelta(hours=2)
    body = {
        "summary": "Mystery dinner test",
        "description": "i eat",
        "start": {
            "dateTime": datetime_obj.isoformat(),
        },
        "end": {
            "dateTime": end_time.isoformat(),
        },
        "sendUpdates": True,
        "attendees": [
            {"email": "jzengg@gmail.com"},
        ],
        "reminders": {
            "useDefault": True,
        },
    }
    event = service.events().insert(calendarId="primary", body=body).execute()
    print("Event created: %s" % (event.get("htmlLink")))
    patch = {
        "conferenceDataVersion": 1,
        "calendarId": "primary",
        "eventId": event["id"],
        "conferenceData": {"createRequest": {"requestId": "7qxalsvy0e"}},
    }
    service.events().patch(patch).execute()
    # service.events().delete(calendarId="primary", eventId=event['id'])
    # print('event deleted')


if __name__ == "__main__":
    main()
