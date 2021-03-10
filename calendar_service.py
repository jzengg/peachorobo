from datetime import timedelta

import parsedatetime
from gcsa.conference import ConferenceSolutionCreateRequest, SolutionType
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar, SendUpdatesMode

from pytz import timezone


class CalendarService:
    def __init__(self):
        self.calendar = GoogleCalendar(
            "primary", credentials_path="credentials.json", token_path="token.pickle"
        )

    def create_event(self, start_dt):
        end_dt = start_dt + timedelta(hours=2)
        attendees = ["jzengg@gmail.com"]
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
        return event_response

    def get_event(self, event_id):
        event_response = self.calendar.get_event(event_id)
        return event_response

    def delete_event(self, event_id):
        event = self.calendar.get_event(event_id)
        self.calendar.delete_event(event)


def main():
    calendar_service = CalendarService()
    cal_parser = parsedatetime.Calendar()
    start_dt, _ = cal_parser.parseDT(
        datetimeString="tomorrow at 3pm", tzinfo=timezone("US/Eastern")
    )
    calendar_service.create_event(start_dt)


if __name__ == "__main__":
    main()
