from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from services.analysis import TripRequest, analyze_trip
from services.heatmap import build_heatmap
from services.routing.alternatives import build_routes

from . import providers
from .errors import error_response
from .serializers import TripSerializer

MIN_QUERY_LENGTH = 3


def _trip_request(data: dict) -> TripRequest:
    return TripRequest(
        origin=(data["origin"]["lat"], data["origin"]["lng"]),
        destination=(data["destination"]["lat"], data["destination"]["lng"]),
        departure=data["departure"],
        load_lb=data["load_lb"],
        interval_mi=int(data["interval_mi"]),
    )


@api_view(["GET"])
@throttle_classes([])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def geocode(request):
    query = request.query_params.get("q", "").strip()
    if len(query) < MIN_QUERY_LENGTH:
        return error_response("validation_error", f"Type at least {MIN_QUERY_LENGTH} characters.", 400, {"q": ["Too short."]})
    return Response({"results": providers.geocoder().search(query)})


@api_view(["POST"])
def analyze(request):
    serializer = TripSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    trip = _trip_request(serializer.validated_data)
    return Response(analyze_trip(trip, providers.routing(), providers.weather()))


@api_view(["POST"])
def heatmap(request):
    serializer = TripSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    trip = _trip_request(serializer.validated_data)
    routes, _ = build_routes(providers.routing(), trip.origin, trip.destination)
    if not routes:
        return error_response("invalid_trip", "No drivable route was found between these locations.", 400)
    payload = build_heatmap([opt.points for _, opt in routes], trip.departure, trip.load_lb, providers.weather())
    return Response(payload)
