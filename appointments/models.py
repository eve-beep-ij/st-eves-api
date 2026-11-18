import secrets

from django.conf import settings
from django.db import models

from doctors.models import DoctorProfile


def make_room_code():
    return f"stEves-{secrets.token_hex(16)}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE, related_name="appointments"
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    video_room = models.CharField(max_length=64, blank=True, default="", editable=False)
    reminder_sent = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.video_room:
            self.video_room = make_room_code()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.patient} with {self.doctor} on {self.date} at {self.start_time}"