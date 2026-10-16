"""One-off: show which fields of a WTTJ search hit hold the start date."""
import json, requests
from jobfinder.sources import wttj
s = requests.Session(); s.headers["User-Agent"] = wttj.UA
key = wttj._api_key(s)
data = wttj._search(s, key, wttj.JOBS_INDEX, "query=stage%20strategie&hitsPerPage=5")
for h in data["hits"][:3]:
    print("=== ", h.get("name"))
    print("KEYS:", sorted(h.keys()))
    for k, v in h.items():
        if any(w in k.lower() for w in ("start", "date", "begin", "duration", "_at")):
            print("  ", k, "=", json.dumps(v, ensure_ascii=False)[:200])
# the public job page / API for the first hit
h = data["hits"][0]
org = (h.get("organization") or {}).get("slug")
for url in (f"https://api.welcometothejungle.com/api/v1/organizations/{org}/jobs/{h.get('slug')}",):
    try:
        r = s.get(url, timeout=20)
        print("API", r.status_code)
        j = r.json().get("job", {})
        for k, v in j.items():
            if any(w in k.lower() for w in ("start", "date", "duration", "_at")):
                print("  ", k, "=", json.dumps(v, ensure_ascii=False)[:200])
    except Exception as e:
        print("API error", e)
