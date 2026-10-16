"""One-off: check the WTTJ job API (start date, description fields)."""
import json, time, requests
from jobfinder.sources import wttj
s = requests.Session(); s.headers["User-Agent"] = wttj.UA
key = wttj._api_key(s)
data = wttj._search(s, key, wttj.JOBS_INDEX, "query=stage%20transformation&hitsPerPage=15")
first = True
for h in data["hits"]:
    org = (h.get("organization") or {}).get("slug")
    url = f"https://api.welcometothejungle.com/api/v1/organizations/{org}/jobs/{h.get('slug')}"
    t = time.time(); r = s.get(url, timeout=20); dt = time.time() - t
    j = r.json().get("job", {}) if r.ok else {}
    if first and j:
        print("JOB KEYS:", sorted(j.keys())); first = False
        for k, v in j.items():
            if isinstance(v, str) and len(v) > 80:
                print("  long text field:", k, len(v))
    print(r.status_code, f"{dt:.2f}s", h.get("name")[:60], "| start_date =", j.get("start_date"),
          "| dur", j.get("contract_duration_min"), j.get("contract_duration_max"))
