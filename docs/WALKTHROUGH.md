# Walkthrough script (about 8 minutes)

Setup: the hosted app open in one tab, the repo in a second, the README in a third. Open the hosted
URL once beforehand so the free instance is awake. For a trip with real weather variety, check the
heatmap first and pick a corridor that shows orange or red at some hour (South Florida is a good
candidate; Cheyenne, WY to Salt Lake City, UT is a good wind and snow candidate). Words in
[brackets] are things to do, not to say.

---

## 0:00 Intro (30 s)

"Hi, I'm [name]. This is my submission for the weather-aware truck routing assessment. A driver
gives the app an origin, a destination, a departure time and a load weight. The app builds three
routes, looks up the forecast at the place and time the truck will actually be there, scores each
route for risk, and recommends one. It also has a weather heatmap with a slider that covers the
next 48 hours. It's a React front end and a Django back end, served as one app. I'll show it
first, then walk through the logic and how it's built."

## 0:30 Demo (2 min 30 s)

[Open the app. Type the origin; wait for suggestions.]
"I'll start typing the origin. Suggestions appear after three characters, and the search is
debounced so it doesn't fire on every keystroke."

[Pick origin and destination.]

[Set the departure and load.]
"Departure time and load weight come next. The sampling interval defaults to 25 miles, and I can
switch it to 10 or 50. A shorter interval catches smaller storm cells but needs more weather
lookups."

[Submit. Point at the progress stages.]
"While it runs you can see the stages: finding routes, fetching the forecast, then scoring. Long
trips take a few seconds because they call free public routing and weather services."

[Results appear.]
"Here are the three routes. The banner says which one is recommended and why, with numbers: for
example, 'Fewest Severe miles, 0 against 10'. Each card shows duration, distance, arrival time, a
risk bar, the miles at Severe and High, and the average risk."

[Click between the route cards.]
"On the map the routes are coloured by risk segment by segment. Clicking a route selects it.
Clicking a checkpoint shows the ETA there and the wind, rain and snow the app used."

[Click 'Show checkpoints'.]
"The checkpoint table lists each stop with its ETA and risk level, so every colour on the map can
be traced to a number."

[Scroll to the heatmap and drag the slider.]
"This is the heatmap. The slider goes from now to 48 hours out. Dragging it is smooth because the
data for all 49 hours is loaded once. Moving the slider only changes how the map is painted, and
doesn't make a network request." [Press play.]

[Change the load to 45,000 lb and run again.]
"Now I'll raise the load to 45,000 pounds and run it again. Heavy loads make high wind more
dangerous, so the same winds can push a route up a level."

## 3:00 Risk and recommendation logic (2 min)

[Open backend/domain/rules.py.]
"All the thresholds are in this one file. Wind, rain and snow each have bands from Low up to No
Travel. A band includes its lower value and excludes its upper value, except at the top of the
Severe rain and snow bands, where the edge is included. A checkpoint's level is the worst of
its three weather levels. The load rules can only raise that level, never lower it: above 40,000
pounds, wind of 35 or more is Severe; above 30,000 pounds, wind of 45 or more is No Travel; and
55 mph is No Travel for anyone."

[Open backend/tests/test_rules.py.]
"Every boundary has a test: 24.9 against 25 mph, and exactly 30,000 pounds against 30,001."

[Open backend/domain/ranking.py.]
"Ranking compares routes in this order: fewest Severe miles, then fewest High miles, then lowest
average risk, then shortest time. Values are rounded so a tiny difference falls through to the
next rule. A route containing No Travel conditions is ranked last."

"Where the brief left room for interpretation, I made a choice and wrote it in the README. For
example, each checkpoint owns the miles up to the next one, and miles with no forecast are shown
as unscored and never assumed to be Low."

## 5:00 Architecture (1 min 30 s)

[Show the folder tree.]
"The domain folder is plain Python with no framework imports: geometry, sampling, rules, scoring
and ranking. The services folder wraps OSRM for routing, Photon for place search and Open-Meteo for
weather, each behind a small interface. Tests use fake providers, so they never touch the network."

"For timing: a checkpoint's ETA is the departure time plus the elapsed time along the route's legs.
I use the forecast hour nearest to that ETA."

"For three routes, I take OSRM's alternatives first. If there are fewer than three, I add routes
through via-points off to the side. I drop any that double back or that mostly overlap another
route."

"The heatmap is one grid along the corridor, scored with the same function as the routes. The slider
only rewrites a paint expression on the map."

"In production, Django serves the built React app and the API together, so it's a single service."

## 6:30 Quality and limits (1 min)

"The back end has 112 tests and the front end has 14. CI runs both, plus lint and the build."

"The limits, honestly: the public OSRM server only has a car profile, so I apply a truck speed
factor of 0.9. The ETAs are an estimate, not truck-exact. The free APIs are fair-use and can
rate-limit, so I batch and cache requests and show a plain message if one is busy. Weather is
sampled at points, so a small storm cell can colour a whole stretch. And two routes that run a few
miles apart can score differently because of that sampling."

"With more time, I'd add a truck-aware routing engine, hazard scoring that accounts for the time
of day, and saved trips."

## 7:30 Close (30 s)

"That's the project. The repository and the hosted app are linked below. The README has the
setup steps, the risk-rule interpretations and the full list of limitations. Thanks for watching."
