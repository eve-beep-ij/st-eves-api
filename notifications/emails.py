import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _name(user):
    return user.get_full_name() or user.username


def _when(day, start):
    return f"{day:%A %d %B %Y} at {start:%H:%M}"


def _send(subject, body, recipient):
    """Send one email. A missing address or a mail problem never breaks the app."""
    if not recipient:
        return
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient])
    except Exception:
        logger.exception("Could not send email to %s", recipient)


def notify_booked(appointment):
    patient = appointment.patient
    doctor_user = appointment.doctor.user
    when = _when(appointment.date, appointment.start_time)
    _send(
        "St Eves: appointment request received",
        f"Hello {_name(patient)},\n\n"
        f"We received your appointment request with Dr. {_name(doctor_user)} "
        f"on {when}. It is waiting for the doctor to confirm.\n\n"
        "St Eves",
        patient.email,
    )
    _send(
        "St Eves: new appointment request",
        f"Hello Dr. {_name(doctor_user)},\n\n"
        f"{_name(patient)} requested an appointment on {when}. "
        "Please confirm or cancel it from your dashboard.\n\n"
        "St Eves",
        doctor_user.email,
    )


def notify_status_changed(appointment):
    patient = appointment.patient
    doctor_user = appointment.doctor.user
    when = _when(appointment.date, appointment.start_time)
    if appointment.status == "confirmed":
        _send(
            "St Eves: appointment confirmed",
            f"Hello {_name(patient)},\n\n"
            f"Dr. {_name(doctor_user)} confirmed your appointment on {when}.\n\n"
            "St Eves",
            patient.email,
        )
    elif appointment.status == "completed":
        _send(
            "St Eves: visit completed",
            f"Hello {_name(patient)},\n\n"
            f"Your visit with Dr. {_name(doctor_user)} on {when} is complete. "
            "Any notes from your doctor will appear under My history.\n\n"
            "St Eves",
            patient.email,
        )


def notify_cancelled(appointment, cancelled_by):
    patient = appointment.patient
    doctor_user = appointment.doctor.user
    when = _when(appointment.date, appointment.start_time)
    if cancelled_by == patient:
        _send(
            "St Eves: appointment cancelled",
            f"Hello Dr. {_name(doctor_user)},\n\n"
            f"{_name(patient)} cancelled the appointment on {when}.\n\n"
            "St Eves",
            doctor_user.email,
        )
    else:
        _send(
            "St Eves: appointment cancelled",
            f"Hello {_name(patient)},\n\n"
            f"Dr. {_name(doctor_user)} cancelled your appointment on {when}. "
            "Please book another time.\n\n"
            "St Eves",
            patient.email,
        )


def notify_rescheduled(appointment, old_date, old_start):
    patient = appointment.patient
    doctor_user = appointment.doctor.user
    old_when = _when(old_date, old_start)
    new_when = _when(appointment.date, appointment.start_time)
    _send(
        "St Eves: appointment rescheduled",
        f"Hello Dr. {_name(doctor_user)},\n\n"
        f"{_name(patient)} moved an appointment from {old_when} to {new_when}. "
        "Please confirm the new time from your dashboard.\n\n"
        "St Eves",
        doctor_user.email,
    )
    _send(
        "St Eves: appointment rescheduled",
        f"Hello {_name(patient)},\n\n"
        f"Your appointment with Dr. {_name(doctor_user)} moved from {old_when} "
        f"to {new_when}. It is waiting for the doctor to confirm.\n\n"
        "St Eves",
        patient.email,
    )



def notify_reminder(appointment):
    patient = appointment.patient
    doctor_user = appointment.doctor.user
    when = _when(appointment.date, appointment.start_time)
    _send(
        "St Eves: appointment reminder",
        f"Hello {_name(patient)},\n\n"
        f"This is a reminder of your appointment with Dr. {_name(doctor_user)} "
        f"on {when}.\n\n"
        "If you can no longer attend, please cancel or reschedule from "
        "My Appointments.\n\n"
        "St Eves",
        patient.email,
    )