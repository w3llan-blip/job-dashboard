"""One-off: print a VIE offer by id (Business France is unreachable outside CI)."""
import json, sys
import requests
from jobfinder.sources.vie import _get_api_config, UA, SITE

oid = sys.argv[1]
s = requests.Session(); s.headers["User-Agent"] = UA
ep, key = _get_api_config(s)
print("endpoint", ep)
for url in (f"{ep}/{oid}", f"{ep}/offers/{oid}", f"{ep}/offer/{oid}"):
    try:
        r = s.get(url, headers={"X-API-KEY": key}, timeout=30)
        print(url, r.status_code)
        if r.ok and r.text.strip().startswith("{"):
            print(json.dumps(r.json(), ensure_ascii=False, indent=1)[:12000]); sys.exit()
    except Exception as e:
        print(url, e)
skip = 0
while skip < 6000:
    body = {"limit": 100, "skip": skip, "query": "", "activitySectorId": [], "missionsTypesIds": [],
            "missionsDurations": [], "gerographicZones": [], "countriesIds": [], "studiesLevelId": [],
            "companiesSizes": [], "specializationsIds": [], "entreprisesIds": [0], "missionStartDate": None}
    r = s.post(ep + "/search", json=body, headers={"X-API-KEY": key}, timeout=30); r.raise_for_status()
    batch = r.json().get("result") or []
    if not batch: break
    for o in batch:
        if str(o.get("id")) == oid:
            print(json.dumps(o, ensure_ascii=False, indent=1)[:12000]); sys.exit()
    skip += 100
print("not found")
