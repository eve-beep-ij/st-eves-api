from rest_framework import serializers

from .models import DoctorProfile, Schedule


class ScheduleSerializer(serializers.ModelSerializer):
    weekday_name = serializers.CharField(source="get_weekday_display", read_only=True)

    def validate(self, data):
        start = data.get("start_time", getattr(self.instance, "start_time", None))
        end = data.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError("End time must be after start time.")

        request = self.context.get("request")
        if request and self.instance is None:
            doctor = request.user.doctor_profile
            if Schedule.objects.filter(doctor=doctor, weekday=data["weekday"]).exists():
                raise serializers.ValidationError(
                    "You already have hours for that day. Edit or delete it instead."
                )
        return data

    def validate_slot_minutes(self, value):
        if value < 10:
            raise serializers.ValidationError("Slots must be at least 10 minutes.")
        return value    

    class Meta:
        model = Schedule
        fields = ("id", "weekday", "weekday_name", "start_time", "end_time", "slot_minutes")
       

class DoctorSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    schedules = ScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = DoctorProfile
        fields = (
            "id", "first_name", "last_name", "specialty",
            "bio", "years_experience", "photo", "schedules",
        )