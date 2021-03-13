from datetime import datetime, timedelta
from time import sleep

import parsedatetime
from gcsa.conference import ConferenceSolutionCreateRequest, SolutionType
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar, SendUpdatesMode

from pytz import timezone

from config import peachorobo_config


class CalendarService:
    def __init__(self):
        self.calendar = GoogleCalendar(
            "primary", credentials_path="credentials.json", token_path="token.pickle"
        )

    def create_event(self, start_dt: datetime) -> Event:
        end_dt = start_dt + timedelta(hours=2)
        attendees = peachorobo_config.calendar_emails
        event = Event(
            "Mystery Dinner",
            start=start_dt,
            end=end_dt,
            attendees=attendees,
            conference_solution=ConferenceSolutionCreateRequest(
                solution_type=SolutionType.HANGOUTS_MEET,
            ),
        )
        event_response = self.calendar.add_event(
            event, send_updates=SendUpdatesMode.ALL
        )
        hangout_link = None
        retries = 5
        while hangout_link is None and retries > 0:
            try:
                hangout_link = event_response.conference_solution.entry_points[0].uri
            except Exception as e:
                event = self.get_event(event.id)
                retries -= 1
                sleep(5)
        return event_response

    def get_event(self, event_id: str) -> Event:
        event_response = self.calendar.get_event(event_id)
        return event_response

    def delete_event(self, event_id: str) -> None:
        try:
            event = self.calendar.get_event(event_id)
            self.calendar.delete_event(event)
        except Exception:
            pass


def main():
    calendar_service = CalendarService()
    cal_parser = parsedatetime.Calendar()
    start_dt, _ = cal_parser.parseDT(
        datetimeString="tomorrow at 3pm", tzinfo=timezone("US/Eastern")
    )
    event = calendar_service.create_event(start_dt)
    event


if __name__ == "__main__":
    main()
