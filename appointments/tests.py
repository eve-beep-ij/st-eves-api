# from django.test import TestCase

# Create your tests here.

from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from doctors.models import DoctorProfile, Schedule

from .models import Appointment

User = get_user_model()


class AppointmentRulesTests(APITestCase):
    def setUp(self):
        # Runs before EVERY test: builds a fresh doctor, two patients and a schedule.
        self.doctor_user = User.objects.create_user(
            username="drtest", email="dr@test.com", password="pass12345", role="doctor"
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user, specialty="Cardiology"
        )
        self.patient = User.objects.create_user(
            username="patient1", email="p1@test.com", password="pass12345", role="patient"
        )
        self.other_patient = User.objects.create_user(
            username="patient2", email="p2@test.com", password="pass12345", role="patient"
        )

        # One day next week, with the doctor working 09:00-12:00 in 30 minute slots.
        self.day = timezone.localdate() + timedelta(days=7)
        Schedule.objects.create(
            doctor=self.doctor,
            weekday=self.day.weekday(),
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_minutes=30,
        )

    # ---------- helpers ----------

    def make_appointment(self, patient=None, start="09:00", status="pending"):
        start_dt = datetime.combine(self.day, datetime.strptime(start, "%H:%M").time())
        return Appointment.objects.create(
            patient=patient or self.patient,
            doctor=self.doctor,
            date=self.day,
            start_time=start_dt.time(),
            end_time=(start_dt + timedelta(minutes=30)).time(),
            reason="Checkup",
            status=status,
        )

    def book(self, user, start="09:00", day=None):
        self.client.force_authenticate(user=user)
        return self.client.post(
            "/api/appointments/",
            {
                "doctor": self.doctor.id,
                "date": str(day or self.day),
                "start_time": start,
                "reason": "Checkup",
            },
            format="json",
        )

    # ---------- booking ----------

    def test_patient_can_book_a_free_slot(self):
        response = self.book(self.patient)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(Appointment.objects.first().status, "pending")

    def test_cannot_book_a_slot_that_is_taken(self):
        self.make_appointment(patient=self.patient, start="09:00")
        response = self.book(self.other_patient, start="09:00")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_cannot_book_a_date_in_the_past(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        response = self.book(self.patient, day=yesterday)
        self.assertEqual(response.status_code, 400)

    # ---------- cancelling ----------

    def test_patient_cannot_cancel_another_patients_appointment(self):
        appointment = self.make_appointment(patient=self.patient)
        self.client.force_authenticate(user=self.other_patient)
        response = self.client.post(f"/api/appointments/{appointment.id}/cancel/")
        self.assertEqual(response.status_code, 404)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "pending")

    def test_cancelling_frees_the_slot_again(self):
        appointment = self.make_appointment(patient=self.patient, start="09:00")
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(f"/api/appointments/{appointment.id}/cancel/")
        self.assertEqual(response.status_code, 200)

        slots = self.client.get(
            f"/api/appointments/slots/?doctor={self.doctor.id}&date={self.day}"
        )
        self.assertIn("09:00", slots.data["slots"])

    # ---------- doctor status changes ----------

    def test_doctor_can_confirm_a_pending_appointment(self):
        appointment = self.make_appointment()
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.post(
            f"/api/appointments/{appointment.id}/status/",
            {"status": "confirmed"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "confirmed")

    def test_patient_cannot_change_status(self):
        appointment = self.make_appointment()
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            f"/api/appointments/{appointment.id}/status/",
            {"status": "confirmed"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_skip_confirming(self):
        appointment = self.make_appointment(status="pending")
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.post(
            f"/api/appointments/{appointment.id}/status/",
            {"status": "completed"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_complete_before_the_appointment_date(self):
        appointment = self.make_appointment(status="confirmed")
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.post(
            f"/api/appointments/{appointment.id}/status/",
            {"status": "completed"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "confirmed")

    # ---------- rescheduling and privacy ----------

    def test_rescheduling_sends_the_appointment_back_to_pending(self):
        appointment = self.make_appointment(start="09:00", status="confirmed")
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            f"/api/appointments/{appointment.id}/reschedule/",
            {"date": str(self.day), "start_time": "10:00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "pending")
        self.assertEqual(appointment.start_time, time(10, 0))

    def test_patient_only_sees_their_own_appointments(self):
        mine = self.make_appointment(patient=self.patient, start="09:00")
        self.make_appointment(patient=self.other_patient, start="09:30")
        self.client.force_authenticate(user=self.patient)
        response = self.client.get("/api/appointments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([a["id"] for a in response.data], [mine.id])