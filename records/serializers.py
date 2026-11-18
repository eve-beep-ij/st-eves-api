from rest_framework import serializers

from .models import VisitNote


class VisitNoteSerializer(serializers.ModelSerializer):
    date = serializers.DateField(source="appointment.date", read_only=True)
    start_time = serializers.TimeField(source="appointment.start_time", read_only=True)
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = VisitNote
        fields = (
            "id",
            "appointment",
            "date",
            "start_time",
            "doctor_name",
            "patient_name",
            "summary",
            "advice",
            "follow_up",
            "medicines",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("appointment", "created_at", "updated_at")

    def get_doctor_name(self, obj):
        user = obj.appointment.doctor.user
        return f"Dr. {user.get_full_name() or user.username}"

    def get_patient_name(self, obj):
        patient = obj.appointment.patient
        return patient.get_full_name() or patient.username

    def validate_medicines(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Medicines must be a list.")
        if len(value) > 20:
            raise serializers.ValidationError("At most 20 medicines per prescription.")

        cleaned = []
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each medicine must be an object.")
            name = str(item.get("name", "")).strip()
            if not name:
                continue  
            cleaned.append(
                {
                    "name": name[:100],
                    "dose": str(item.get("dose", "")).strip()[:50],
                    "frequency": str(item.get("frequency", "")).strip()[:100],
                    "days": str(item.get("days", "")).strip()[:10],
                }
            )
        return cleaned