# Walkthrough script (about 8 minutes)

Record with the hosted app open, a second tab on the repo, and the README open.
Pick a trip with some weather variety, for example Cheyenne, WY to Salt Lake City, UT.

## 0:00 What it is (30 s)
- A truck driver enters origin, destination, departure and load weight.
- The app builds three routes, checks the forecast where the truck will be at the time it is there,
  scores risk, and recommends one.

## 0:30 Demo (2.5 min)
1. Type the origin and destination; point out the autocomplete (3 characters, debounced).
2. Set departure and load. Keep 25 miles as the sampling interval; mention 10 and 50.
3. Submit. Call out the progress stages.
4. Results: the recommended banner and why ("Lowest average risk (0.00 vs 0.19)").
   Each card: duration, distance, arrival, the flat risk bar, Severe and High miles, average risk.
5. Map: three labelled routes, segments coloured by risk, click a route to select it,
   click a checkpoint to see ETA and wind, rain and snow.
6. "Show checkpoints": the table with ETA and risk per checkpoint.
7. Heatmap: drag the slider through 48 hours, then press play. Point out that it is smooth because
   the data is loaded once.
8. Change the load to 45,000 lb and run again to show the wind load rules changing the result.

## 3:00 Risk and recommendation logic (2 min)
- Open `backend/domain/rules.py`: bands, boundaries, load rules; worst-of-three per checkpoint.
- Open `backend/tests/test_rules.py`: boundary tests (24.9 / 25, exactly 30,000 lb vs 30,001).
- `ranking.py`: fewest Severe miles, fewest High miles, lowest average risk, shortest time;
  rounding so near-ties fall through; a No Travel route is ranked last.
- Interpretation decisions are listed in the README.

## 5:00 Architecture (1.5 min)
- `domain/` is pure Python with no framework imports; `services/` wraps OSRM, Photon and Open-Meteo
  behind small interfaces so tests use fakes and never hit the network.
- Weather lookup: the checkpoint's ETA is the departure time plus elapsed time along the route's
  steps; the nearest forecast hour is used. Unscored miles are shown, never assumed Low.
- Three routes: OSRM alternatives, then via-point routes; routes that double back or overlap
  are dropped.
- Heatmap: one grid along the corridor, scored with the same function; the slider only rewrites a
  map paint expression.

## 6:30 Quality and limits (1 min)
- Tests: backend `pytest`, frontend `npm test`; CI runs both plus lint and build.
- Limits: OSRM public demo is a car profile with a truck speed factor; free APIs are fair-use and
  rate limited, so requests are cached, batched and rate-limit aware.
- What I would do next: a truck-aware routing engine, hazard-weighted route scoring by time of day,
  and saved trips.

## 7:30 Close (30 s)
- Repo and hosted URL.
