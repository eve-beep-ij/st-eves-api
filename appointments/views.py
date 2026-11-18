from datetime import date as date_type
from datetime import datetime, timedelta
from datetime import time as time_type

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from doctors.models import DoctorProfile
from notifications.emails import (
    notify_booked,
    notify_cancelled,
    notify_rescheduled,
    notify_status_changed,
)

from .models import Appointment
from .serializers import AppointmentSerializer
from .utils import get_free_slots


def visible_appointments(user):
    queryset = Appointment.objects.select_related("doctor__user", "patient")
    if user.role == "patient":
        return queryset.filter(patient=user)
    if user.role == "doctor":
        return queryset.filter(doctor__user=user)
    return queryset  # staff see everything


class IsPatient(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "patient"


class IsDoctorOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            "doctor",
            "staff",
        )


class AppointmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AppointmentSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPatient()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return visible_appointments(self.request.user)

    def perform_create(self, serializer):
        appointment = serializer.save()
        notify_booked(appointment)


class AppointmentCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        appointment = get_object_or_404(visible_appointments(request.user), pk=pk)
        if appointment.status in (
            Appointment.Status.CANCELLED,
            Appointment.Status.COMPLETED,
        ):
            return Response(
                {"detail": f"This appointment is already {appointment.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()
        notify_cancelled(appointment, request.user)
        return Response(AppointmentSerializer(appointment).data)


class AppointmentStatusView(APIView):
    permission_classes = [IsDoctorOrStaff]

    # Allowed moves: pending -> confirmed -> completed
    ALLOWED = {
        Appointment.Status.PENDING: [Appointment.Status.CONFIRMED],
        Appointment.Status.CONFIRMED: [Appointment.Status.COMPLETED],
    }

    def post(self, request, pk):
        appointment = get_object_or_404(visible_appointments(request.user), pk=pk)
        new_status = request.data.get("status")
        if request.user.role == "staff" and new_status == Appointment.Status.COMPLETED:
            return Response(
                {"detail": "Only the doctor can mark a visit as completed."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if new_status not in self.ALLOWED.get(appointment.status, []):
            return Response(
                {
                    "detail": f"Cannot change a {appointment.status} appointment to {new_status}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            new_status == Appointment.Status.COMPLETED
            and appointment.date > timezone.localdate()
        ):
            return Response(
                {"detail": "You cannot complete an appointment before its date."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = new_status
        appointment.save()
        notify_status_changed(appointment)
        return Response(AppointmentSerializer(appointment).data)


class FreeSlotsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        doctor_id = request.query_params.get("doctor")
        day_text = request.query_params.get("date")
        if not doctor_id or not day_text:
            return Response(
                {"detail": "Both doctor and date are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            day = date_type.fromisoformat(day_text)
        except ValueError:
            return Response(
                {"detail": "Date must look like 2026-11-16."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        doctor = get_object_or_404(DoctorProfile, pk=doctor_id)
        slots = [slot.strftime("%H:%M") for slot in get_free_slots(doctor, day)]
        return Response({"doctor": doctor.id, "date": day_text, "slots": slots})


class AppointmentRescheduleView(APIView):
    permission_classes = [IsPatient]

    def post(self, request, pk):
        # Only this patient's own appointments can be found here
        appointment = get_object_or_404(visible_appointments(request.user), pk=pk)

        if appointment.status not in (
            Appointment.Status.PENDING,
            Appointment.Status.CONFIRMED,
        ):
            return Response(
                {"detail": f"A {appointment.status} appointment cannot be rescheduled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.localdate()
        if appointment.date < today:
            return Response(
                {"detail": "Past appointments cannot be rescheduled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_date = date_type.fromisoformat(str(request.data.get("date", "")))
            new_time = time_type.fromisoformat(str(request.data.get("start_time", "")))
        except ValueError:
            return Response(
                {"detail": "Please send a date like 2026-11-16 and a time like 09:30."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_date < today:
            return Response(
                {"detail": "You cannot move an appointment to a date in the past."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_time not in get_free_slots(appointment.doctor, new_date):
            return Response(
                {"detail": "That time slot is not available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        schedule = appointment.doctor.schedules.get(weekday=new_date.weekday())
        end = datetime.combine(new_date, new_time) + timedelta(
            minutes=schedule.slot_minutes
        )

        old_date = appointment.date
        old_start = appointment.start_time

        appointment.date = new_date
        appointment.start_time = new_time
        appointment.end_time = end.time()
        appointment.status = Appointment.Status.PENDING
        appointment.reminder_sent = False
        appointment.save()
        notify_rescheduled(appointment, old_date, old_start)
        return Response(AppointmentSerializer(appointment).data)
        