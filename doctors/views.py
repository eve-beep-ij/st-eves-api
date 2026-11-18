from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError

from appointments.models import Appointment

from .models import DoctorProfile, Schedule
from .serializers import DoctorSerializer, ScheduleSerializer


class IsDoctor(permissions.BasePermission):
    """Only logged-in users with the doctor role (and a doctor profile) may pass."""

    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated
            and getattr(user, "role", None) == "doctor"
            and hasattr(user, "doctor_profile")
        )


def booked_on_same_weekday(schedule):
    """Upcoming pending/confirmed appointments that fall on this schedule's weekday."""
    upcoming = Appointment.objects.filter(
        doctor=schedule.doctor,
        date__gte=timezone.localdate(),
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
    )
    return [a for a in upcoming if a.date.weekday() == schedule.weekday]


class DoctorListView(generics.ListAPIView):
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = DoctorProfile.objects.select_related("user").prefetch_related("schedules")
        specialty = self.request.query_params.get("specialty")
        if specialty:
            queryset = queryset.filter(specialty__icontains=specialty)
        return queryset


class DoctorDetailView(generics.RetrieveAPIView):
    queryset = DoctorProfile.objects.select_related("user").prefetch_related("schedules")
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]


class MyScheduleListCreateView(generics.ListCreateAPIView):
    serializer_class = ScheduleSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return Schedule.objects.filter(doctor=self.request.user.doctor_profile)

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user.doctor_profile)


class MyScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ScheduleSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return Schedule.objects.filter(doctor=self.request.user.doctor_profile)

    def perform_destroy(self, instance):
        booked = booked_on_same_weekday(instance)
        if booked:
            raise ValidationError(
                {
                    "detail": (
                        f"You can't remove {instance.get_weekday_display()}: "
                        f"{len(booked)} upcoming appointment(s) are booked that day. "
                        "Cancel them first."
                    )
                }
            )
        instance.delete()

    def perform_update(self, serializer):
        schedule = serializer.instance
        data = serializer.validated_data
        new_weekday = data.get("weekday", schedule.weekday)
        new_start = data.get("start_time", schedule.start_time)
        new_end = data.get("end_time", schedule.end_time)

        booked = booked_on_same_weekday(schedule)
        if new_weekday != schedule.weekday:
            clashing = booked  # the old day would lose all its hours
        else:
            clashing = [
                a for a in booked if a.start_time < new_start or a.end_time > new_end
            ]

        if clashing:
            raise ValidationError(
                {
                    "detail": (
                        f"You can't change {schedule.get_weekday_display()}: "
                        f"{len(clashing)} upcoming appointment(s) would no longer fit. "
                        "Cancel them first."
                    )
                }
            )
        serializer.save()