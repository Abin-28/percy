from app import create_scheduling_link, init_scheduler_db

init_scheduler_db()

sender = "harshavardini@thws.de"
to_recipients = [
    "harshahasini1998@gmail.com",
]  # Required count = 2
slots = [
    "Monday, Nov 16 • 10:00 AM - 10:30 AM",
    "Monday, Nov 16 • 02:30 PM - 03:00 PM",
]

link = create_scheduling_link(sender, to_recipients, slots)
print(link)