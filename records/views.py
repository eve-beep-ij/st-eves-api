# from django.shortcuts import render

# Create your views here.

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment
from appointments.views import visible_appointments
from doctors.views import IsDoctor

from .models import VisitNote
from .serializers import VisitNoteSerializer


class MyRecordsListView(generics.ListAPIView):
    """Visit notes the logged-in person is allowed to see, newest first."""

    serializer_class = VisitNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == "staff":
            return VisitNote.objects.none()
        return (
            VisitNote.objects.filter(
                appointment__in=visible_appointments(self.request.user)
            )
            .select_related("appointment__doctor__user", "appointment__patient")
            .order_by("-appointment__date", "-appointment__start_time")
        )


class AppointmentNoteView(APIView):
    """The doctor reads or writes the note for one of their own appointments."""

    permission_classes = [IsDoctor]

    def get(self, request, appointment_id):
        appointment = get_object_or_404(
            visible_appointments(request.user), pk=appointment_id
        )
        note = VisitNote.objects.filter(appointment=appointment).first()
        if note is None:
            return Response({"summary": "", "advice": "", "follow_up": "", "medicines": []})
        return Response(VisitNoteSerializer(note).data)

    def put(self, request, appointment_id):
        appointment = get_object_or_404(
            visible_appointments(request.user), pk=appointment_id
        )
        if appointment.status != Appointment.Status.COMPLETED:
            return Response(
                {"detail": "You can only write a note for a completed appointment."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        note = VisitNote.objects.filter(appointment=appointment).first()
        serializer = VisitNoteSerializer(note, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(appointment=appointment)
        code = status.HTTP_200_OK if note else status.HTTP_201_CREATED
        return Response(serializer.data, status=code)


    def patch(self, request, appointment_id):
        """Save only the prescription (medicines) on an existing note."""
        appointment = get_object_or_404(
            visible_appointments(request.user), pk=appointment_id
        )
        note = VisitNote.objects.filter(appointment=appointment).first()
        if note is None:
            return Response(
                {"detail": "Save the visit note first, then add the prescription."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = VisitNoteSerializer(
            note,
            data={"medicines": request.data.get("medicines", [])},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)