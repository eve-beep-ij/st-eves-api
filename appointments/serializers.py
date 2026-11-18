from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Appointment
from .utils import get_free_slots


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        role = getattr(getattr(request, "user", None), "role", None)
        if role not in ("patient", "doctor"):
            data.pop("video_room", None)
        return data

    class Meta:
        model = Appointment
        fields = (
            "id", "doctor", "doctor_name", "patient_name", "date",
            "start_time", "end_time", "reason", "status", "created_at", "video_room",
        )
        read_only_fields = ("end_time", "status", "created_at", "video_room")

    def get_doctor_name(self, obj):
        user = obj.doctor.user
        return f"Dr. {user.get_full_name() or user.username}"

    def get_patient_name(self, obj):
        return obj.patient.get_full_name() or obj.patient.username

    def validate(self, data):
        if data["date"] < timezone.localdate():
            raise serializers.ValidationError("You cannot book a date in the past.")
        if data["start_time"] not in get_free_slots(data["doctor"], data["date"]):
            raise serializers.ValidationError("That time slot is not available.")
        return data

    def create(self, validated_data):
        doctor = validated_data["doctor"]
        schedule = doctor.schedules.get(weekday=validated_data["date"].weekday())
        start = datetime.combine(validated_data["date"], validated_data["start_time"])
        validated_data["end_time"] = (
            start + timedelta(minutes=schedule.slot_minutes)
        ).time()
        validated_data["patient"] = self.context["request"].user
        return super().create(validated_data)