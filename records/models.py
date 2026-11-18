
from django.db import models

from appointments.models import Appointment


class VisitNote(models.Model):
    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name="visit_note"
    )
    summary = models.TextField()
    advice = models.TextField(blank=True)
    follow_up = models.CharField(max_length=255, blank=True)
    medicines = models.JSONField(default=list, blank=True)  # List of medicine names
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Note for {self.appointment}"

