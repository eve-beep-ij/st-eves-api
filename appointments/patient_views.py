from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User

from .models import Appointment
from .views import visible_appointments


class IsDoctorOnly(permissions.BasePermission):
    """Only logged-in doctors. Staff and patients are not allowed."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "doctor"


def full_name(user):
    return user.get_full_name() or user.username


class MyPatientsListView(APIView):
    """The patients this doctor has (non-cancelled) appointments with."""

    permission_classes = [IsDoctorOnly]

    def get(self, request):
        appointments = (
            visible_appointments(request.user)
            .exclude(status=Appointment.Status.CANCELLED)
            .order_by("-date", "-start_time")
        )

        patients = {}
        for a in appointments:
            p = a.patient
            if p.id not in patients:
                patients[p.id] = {
                    "id": p.id,
                    "name": full_name(p),
                    "email": p.email,
                    "phone": p.phone,
                    "visits": 0,
                    "latest_date": a.date,
                }
            patients[p.id]["visits"] += 1

        return Response(list(patients.values()))


class MyPatientDetailView(APIView):
    """One patient of this doctor, with their appointments with this doctor."""

    permission_classes = [IsDoctorOnly]

    def get(self, request, patient_id):
        appointments = visible_appointments(request.user).filter(
            patient_id=patient_id
        ).order_by("-date", "-start_time")

        # If this doctor has no appointments with that person, pretend not found
        if not appointments.exists():
            raise Http404

        patient = get_object_or_404(User, pk=patient_id)

        return Response(
            {
                "id": patient.id,
                "name": full_name(patient),
                "email": patient.email,
                "phone": patient.phone,
                "appointments": [
                    {
                        "id": a.id,
                        "date": a.date,
                        "start_time": str(a.start_time)[:5],
                        "status": a.status,
                        "reason": a.reason,
                    }
                    for a in appointments
                ],
            }
        )