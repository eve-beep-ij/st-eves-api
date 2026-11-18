from django.urls import path

from .views import AppointmentNoteView, MyRecordsListView

urlpatterns = [
    path("", MyRecordsListView.as_view()),
    path("appointment/<int:appointment_id>/", AppointmentNoteView.as_view()),
]