from datetime import datetime, timedelta

from django.utils import timezone

from .models import Appointment


def generate_slots(doctor, day):
    """All times the doctor works on this date, cut into slots."""
    schedule = doctor.schedules.filter(weekday=day.weekday()).first()
    if not schedule:
        return []
    step = timedelta(minutes=schedule.slot_minutes)
    current = datetime.combine(day, schedule.start_time)
    end = datetime.combine(day, schedule.end_time)
    slots = []
    while current + step <= end:
        slots.append(current.time())
        current += step
    return slots


def get_free_slots(doctor, day):
    """Slots that are not booked and not already in the past."""
    now = timezone.localtime()
    if day < now.date():
        return []
    booked = set(
        Appointment.objects.filter(doctor=doctor, date=day)
        .exclude(status=Appointment.Status.CANCELLED)
        .values_list("start_time", flat=True)
    )
    free = []
    for slot in generate_slots(doctor, day):
        if slot in booked:
            continue
        if day == now.date() and slot <= now.time():
            continue
        free.append(slot)
    return free