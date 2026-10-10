import json, re, sys, datetime, requests
from bs4 import BeautifulSoup

URL = "https://av.brest.by/prigorod.html"
DAYS = {"пн":"1","вт":"2","ср":"3","чт":"4","пт":"5","сб":"6","вс":"7"}

def days(txt):
    t = txt.translate(str.maketrans("Cc", "Сс")).lower()
    if "ежедневно" in t:
        d = "*"
    else:
        ds = {DAYS[w[:2]] for w in re.findall(r"[а-я]+", t)
              if w[:2] in DAYS and not w.startswith("праздн")}
        d = "".join(sorted(ds)) or "*"
    return d, ("и в праздники" if "праздн" in t else "")

def tm(s):
    m = re.search(r"(\d{1,2})\s*[-:.]\s*(\d{2})", s or "")
    return f"{int(m[1])}:{m[2]}" if m else ""

def cell(td):
    return [p.strip() for p in td.get_text("\n").split("\n") if p.strip()]

r = requests.get(URL, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()
soup = BeautifulSoup(r.content, "lxml")
m = re.search(r"Последнее обновление:?\s*(\d{2}\.\d{2}\.\d{4})", soup.get_text(" "))
updated = m[1] if m else ""

out, inn = [], []
for tr in soup.find_all("tr"):
    tds = tr.find_all("td", recursive=False)
    if len(tds) < 8:
        continue
    c = [cell(td) for td in tds[:8]]
    name = " ".join(" ".join(c[0]).split())
    name = re.sub(r"^Брест\s*[-–—]\s*", "", name)
    if not name or name.startswith("Маршрут"):
        continue
    d, hol = days(" ".join(c[2]))
    dep = tm(c[3][0]) if c[3] else ""
    arr = tm(c[5][0]) if c[5] else ""
    if dep and arr:
        notes = ", ".join(x for x in (" ".join(c[5][1:]), hol) if x)
        out.append([name, " ".join(c[1]), d, dep, arr, notes])
    rd = tm(c[6][0]) if c[6] else ""
    ra = tm(c[7][0]) if c[7] else ""
    if rd and ra:
        rdays, notes = d, [hol] if hol else []
        for e in c[6][1:]:
            if re.match(r"(из|от)\s", e.lower()):
                notes.append(e)
            elif days(e)[0] != "*":
                rdays = days(e)[0]
        inn.append([name, rdays, rd, ra, ", ".join(notes)])

print(f"updated={updated} out={len(out)} in={len(inn)}")
if len(out) < 200 or len(inn) < 200:
    sys.exit("Слишком мало рейсов: возможно, изменилась разметка сайта")

with open("schedule.json", "w", encoding="utf-8") as f:
    json.dump({"updated": updated, "fetched": datetime.date.today().isoformat(),
               "out": out, "in": inn}, f, ensure_ascii=False, separators=(",", ":"))
