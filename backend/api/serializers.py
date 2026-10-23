from datetime import datetime, timedelta, timezone

from rest_framework import serializers

from domain.sampling import SUPPORTED_INTERVALS_MI

MAX_LOAD_LB = 150_000


class PlaceSerializer(serializers.Serializer):
    label = serializers.CharField(required=False, allow_blank=True, default="")
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)


class TripSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure = serializers.DateTimeField()
    load_lb = serializers.FloatField(min_value=0, max_value=MAX_LOAD_LB)
    interval_mi = serializers.ChoiceField(choices=SUPPORTED_INTERVALS_MI, default=25)

    def validate_departure(self, value: datetime):
        now = datetime.now(timezone.utc)
        if value < now - timedelta(hours=1):
            raise serializers.ValidationError("Departure cannot be in the past.")
        if value > now + timedelta(days=14):
            raise serializers.ValidationError("Forecasts only cover the next 14 days.")
        return value

    def validate(self, attrs):
        o, d = attrs["origin"], attrs["destination"]
        if (o["lat"], o["lng"]) == (d["lat"], d["lng"]):
            raise serializers.ValidationError({"destination": "Destination must differ from the origin."})
        return attrs
