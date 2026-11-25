
import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def connect_calendar():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def find_free_time(service):
    today = datetime.date.today()
    start_of_day = datetime.datetime.combine(
        today, datetime.time(9, 0),
        tzinfo=datetime.timezone.utc
    )
    end_of_day = datetime.datetime.combine(
        today, datetime.time(18, 0),
        tzinfo=datetime.timezone.utc
    )

    events = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat(),
        timeMax=end_of_day.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute().get("items", [])

    print("\nAvailable Time Slots (9 AM to 6 PM)")

    current_time = start_of_day

    for event in events:
        start = event["start"].get("dateTime")
        end = event["end"].get("dateTime")

        if not start or not end:
            continue

        event_start = datetime.datetime.fromisoformat(start)
        event_end = datetime.datetime.fromisoformat(end)

        if event_start > current_time:
            print("Free:", current_time.strftime("%I:%M %p"),
                  "to", event_start.strftime("%I:%M %p"))

        if event_end > current_time:
            current_time = event_end

    if current_time < end_of_day:
        print("Free:", current_time.strftime("%I:%M %p"),
              "to", end_of_day.strftime("%I:%M %p"))
        
def read_upcoming_events(service):
    now = datetime.datetime.now(
        datetime.timezone.utc
    ).isoformat()

    events = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy="startTime"
    ).execute().get("items", [])

    print("\n--- Upcoming Calendar Events ---")

    if not events:
        print("No upcoming events found.")
        return

    for event in events:
        print("Event:", event.get("summary", "No title"))
        print("Start:", event["start"].get(
            "dateTime", event["start"].get("date")
        ))
        print("------------------------")


def suggest_meeting_time(service):
    print("\n--- Smart Meeting Suggestions ---")
    try:
        date = input("Enter date (YYYY-MM-DD): ").strip()
        meeting_date = datetime.date.fromisoformat(date)

        duration = int(input("Meeting duration in minutes: "))

        if duration <= 0 or duration > 540:
            print("Please enter a duration between 1 and 540 minutes.")
            return

    except ValueError:
        print("Invalid date or duration. Please try again.")
        return

    local_tz = datetime.timezone(
        datetime.timedelta(hours=5, minutes=30)
    )

    meeting_date = datetime.date.fromisoformat(date)

    day_start = datetime.datetime.combine(
        meeting_date, datetime.time(9, 0), tzinfo=local_tz
    )

    day_end = datetime.datetime.combine(
        meeting_date, datetime.time(18, 0), tzinfo=local_tz
    )

    events = service.events().list(
        calendarId="primary",
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute().get("items", [])

    busy_slots = []

    for event in events:
        if "dateTime" in event["start"]:
            start = datetime.datetime.fromisoformat(
                event["start"]["dateTime"]
            )
            end = datetime.datetime.fromisoformat(
                event["end"]["dateTime"]
            )
        else:
            start = day_start
            end = day_end

        busy_slots.append((start, end))

    busy_slots.sort(key=lambda x: x[0])

    current = day_start
    suggestions = []

    for start, end in busy_slots:
        if start > current:
            free_minutes = (start - current).total_seconds() / 60

            if free_minutes >= duration:
                meeting_end = current + datetime.timedelta(
                    minutes=duration
                )
                suggestions.append((current, meeting_end))

        if end > current:
            current = end

    if current < day_end:
        free_minutes = (day_end - current).total_seconds() / 60

        if free_minutes >= duration:
            meeting_end = current + datetime.timedelta(
                minutes=duration
            )
            suggestions.append((current, meeting_end))

    print("\nSuggested Meeting Times:")

    if suggestions:
        for start, end in suggestions[:5]:
            print(
                start.strftime("%I:%M %p"),
                "to",
                end.strftime("%I:%M %p")
            )
    else:
        print("No suitable time slot found.")

def schedule_meeting(service):
    print("\n--- Schedule a Meeting ---")

    title = input("Enter meeting title: ")
    date = input("Enter date (YYYY-MM-DD): ").strip()
    start_time = input("Enter start time (HH:MM): ").strip()
    duration = int(input("Enter duration in minutes: "))

    start = datetime.datetime.fromisoformat(
        date + "T" + start_time
    ).replace(tzinfo=datetime.timezone(
        datetime.timedelta(hours=5, minutes=30)
    ))

    end = start + datetime.timedelta(minutes=duration)
    existing_events = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True
    ).execute().get("items", [])

    if existing_events:
        print("\nThis time slot is already booked!")
        print("Please choose another time.")
        return
    

    event = {
    "summary": title,
    "start": {
        "dateTime": start.isoformat(),
        "timeZone": "Asia/Kolkata"
    },
    "end": {
        "dateTime": end.isoformat(),
        "timeZone": "Asia/Kolkata"
    },
    "reminders": {
        "useDefault": False,
        "overrides": [
            {"method": "popup", "minutes": 10},
            {"method": "email", "minutes": 30}
        ]
    }
}

    service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    print("\nMeeting scheduled successfully!")


if __name__ == "__main__":
    service = connect_calendar()

    while True:
        print("\n===== SMART CALENDAR AI =====")
        print("1. View Upcoming Events")
        print("2. Find Free Time")
        print("3. Schedule Meeting")
        print("4. Smart Meeting Suggestions")
        print("5. Exit")
                

        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            read_upcoming_events(service)

        elif choice == "2":
            find_free_time(service)

        elif choice == "3":
            schedule_meeting(service)

        elif choice == "4":
            suggest_meeting_time(service)

        elif choice == "5":
            print("Thank you for using Smart Calendar AI!")
            break

        else:
            print("Invalid choice! Please select 1 to 4.")