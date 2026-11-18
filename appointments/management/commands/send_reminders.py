from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import Appointment
from notifications.emails import notify_reminder


class Command(BaseCommand):
    help = "Email patients a reminder before a confirmed appointment."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="How many days ahead to remind (default 1 = tomorrow)",
        )

    def handle(self, *args, **options):
        target_day = timezone.localdate() + timedelta(days=options["days"])

        appointments = Appointment.objects.filter(
            date=target_day,
            status=Appointment.Status.CONFIRMED,
            reminder_sent=False,
        ).select_related("patient", "doctor__user")

        sent = 0
        for appointment in appointments:
            if not appointment.patient.email:
                continue
            notify_reminder(appointment)
            appointment.reminder_sent = True
            appointment.save(update_fields=["reminder_sent"])
            sent += 1

        self.stdout.write(f"Reminders sent: {sent}")