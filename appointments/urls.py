from django.urls import path

from .patient_views import MyPatientDetailView, MyPatientsListView
from .views import (
    AppointmentCancelView,
    AppointmentListCreateView,
    AppointmentRescheduleView,
    AppointmentStatusView,
    FreeSlotsView,
)

urlpatterns = [
    path("", AppointmentListCreateView.as_view()),
    path("slots/", FreeSlotsView.as_view()),
    path("my-patients/", MyPatientsListView.as_view()),
    path("my-patients/<int:patient_id>/", MyPatientDetailView.as_view()),
    path("<int:pk>/cancel/", AppointmentCancelView.as_view()),
    path("<int:pk>/status/", AppointmentStatusView.as_view()),
    path("<int:pk>/reschedule/", AppointmentRescheduleView.as_view()),
]