# from django.contrib import admin

# Register your models here.

from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("date", "start_time", "doctor", "patient", "status")
    list_filter = ("status", "date", "doctor")
