from django.urls import path

from .views import DoctorDetailView, DoctorListView, MyScheduleDetailView, MyScheduleListCreateView

urlpatterns = [
    path("", DoctorListView.as_view()),
    path("<int:pk>/", DoctorDetailView.as_view()),
    path("schedules/", MyScheduleListCreateView.as_view()),
    path("schedules/<int:pk>/", MyScheduleDetailView.as_view()),
]