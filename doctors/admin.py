# from django.contrib import admin

# Register your models here.

from django.contrib import admin

from .models import DoctorProfile, Schedule


class ScheduleInline(admin.TabularInline):
    model = Schedule
    extra = 1


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialty", "years_experience")
    inlines = [ScheduleInline]