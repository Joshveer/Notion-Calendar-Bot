import os
import time
import pickle
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from notion_client import Client
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

load_dotenv()

notion = Client(auth=os.getenv("NOTION_TOKEN"))
DATABASE_ID = os.getenv("DATABASE_ID")

SCOPES = ['https://www.googleapis.com/auth/calendar']
creds = None
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

calendar = build('calendar', 'v3', credentials=creds)
NY = ZoneInfo("America/New_York")

def round_to_nearest_5(dt):
    minute = dt.minute
    rounded_minute = round(minute / 5) * 5
    if rounded_minute == 60:
        dt = dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        dt = dt.replace(minute=rounded_minute, second=0, microsecond=0)
    return dt.replace(second=0, microsecond=0)

def create_calendar_event(title):
    now = datetime.now(NY)
    end = round_to_nearest_5(now + timedelta(minutes=30))
    event = {
        'summary': title,
        'start': {'dateTime': now.isoformat(), 'timeZone': 'America/New_York'},
        'end': {'dateTime': end.isoformat(), 'timeZone': 'America/New_York'},
        'colorId': '6'
    }
    created = calendar.events().insert(calendarId='primary', body=event).execute()
    print(f"[+] Scheduled: {title} from {now.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')} EST")
    return created['id']

def update_calendar_event(event_id, title):
    now = datetime.now(NY)
    event = calendar.events().get(calendarId='primary', eventId=event_id).execute()
    start_str = event['start']['dateTime']
    start_dt = datetime.fromisoformat(start_str).astimezone(NY)
    duration = int((now - start_dt).total_seconds() // 60)

    if duration < 5:
        calendar.events().delete(calendarId='primary', eventId=event_id).execute()
        print(f"[!] Discarded: {title} — Too short ({duration} min)")
        return

    event['end'] = {'dateTime': now.isoformat(), 'timeZone': 'America/New_York'}
    updated = calendar.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    print(f"[x] Ended: {title} at {now.strftime('%I:%M %p')} EST — Duration: {duration} min")
    return updated

def poll_notion():
    while True:
        results = notion.databases.query(database_id=DATABASE_ID)["results"]
        for page in results:
            props = page["properties"]
            title = props["Task name"]["title"][0]["plain_text"]
            status = props["Status"]["status"]["name"]
            event_id_prop = props.get("Calendar Event ID", {}).get("rich_text", [])
            event_id = event_id_prop[0]["plain_text"] if event_id_prop else None

            if status == "In progress" and not event_id:
                eid = create_calendar_event(title)
                notion.pages.update(
                    page_id=page["id"],
                    properties={
                        "Calendar Event ID": {
                            "rich_text": [{"text": {"content": eid}}]
                        }
                    }
                )

            elif status in ["Pause", "Done"] and event_id:
                update_calendar_event(event_id, title)
                notion.pages.update(
                    page_id=page["id"],
                    properties={"Calendar Event ID": {"rich_text": []}}
                )
        time.sleep(10)

if __name__ == "__main__":
    print("Running...")
    poll_notion()