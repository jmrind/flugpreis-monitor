"""
Erzeugt einen self-contained HTML-Report (dashboard.html): Statistik,
Preisverlauf pro Strecke, Gästezahl, Buchungsstatus und Ticketing-Deadline.
Einfach im Browser öffnen.

  python dashboard.py
"""

from __future__ import annotations
import json
import html
import datetime as dt

import config
import storage


def _ticket_state(meta: dict, deadline: dt.date, days_left: int) -> tuple[str, str]:
    if not meta["booked"]:
        return "monitor", "nur beobachtet"
    if meta["ticketed"]:
        return "ticketed", "Tickets ausgestellt"
    if days_left < 0:
        return "overdue", f"überfällig seit {abs(days_left)} T"
    if days_left <= config.REMINDER_WINDOW_DAYS:
        return "soon", f"Ticketing in {days_left} T"
    return "scheduled", f"Ticketing bis {deadline.strftime('%d.%m.')}"


def build(out_path: str = "dashboard.html") -> str:
    today = dt.date.today()
    metas = {m["watch_key"]: m for m in storage.list_watches()}
    cards, booked_n, lows_n = [], 0, 0
    next_deadline: tuple[dt.date, str] | None = None

    for r in storage.all_watch_keys():
        key = r["watch_key"]
        m = metas.get(key, {})
        st = storage.stats(key, config.HISTORY_DAYS_FOR_STATS)
        if not st:
            continue
        hist = storage.history(key, config.HISTORY_DAYS_FOR_STATS)

        depart = dt.date.fromisoformat(r["depart_date"])
        deadline = depart - dt.timedelta(days=config.TICKETING_LEAD_DAYS)
        days_left = (deadline - today).days
        booked = bool(m.get("booked"))
        ticketed = bool(m.get("ticketed"))
        state, state_label = _ticket_state(
            {"booked": booked, "ticketed": ticketed}, deadline, days_left)

        if booked:
            booked_n += 1
            if not ticketed and depart >= today:
                if next_deadline is None or deadline < next_deadline[0]:
                    next_deadline = (deadline, f"{r['company']} · {r['origin']}→{r['destination']}")
        if st["all_time_low"]:
            lows_n += 1

        route = f"{r['origin']} → {r['destination']}"
        ret = ""
        if r["return_date"]:
            ro = m.get("return_origin") or r["destination"]
            ret = f"  ·  zurück {ro}→{r['origin']} {r['return_date']}"
        cards.append({
            "id": key, "company": r["company"] or "",
            "kind": m.get("kind", "roundtrip"),
            "route": html.escape(route),
            "sub": html.escape(f"hin {r['depart_date']}{ret}"),
            "trip": html.escape((r["label"] or "").split(" · ")[0]),
            "pax": int(m.get("adults") or 1),
            "state": state, "state_label": html.escape(state_label),
            "current": st["current"], "avg": st["avg"],
            "min": st["min"], "max": st["max"], "n": st["count"],
            "vs_avg": st["vs_avg"],
            "labels": [ts[5:16].replace("T", " ") for ts, _ in hist],
            "values": [p for _, p in hist],
        })

    summary = {
        "watched": len(cards), "booked": booked_n, "lows": lows_n,
        "next_deadline": (
            f"{next_deadline[0].strftime('%d.%m.%Y')}"
            if next_deadline else "—"),
        "next_deadline_sub": (
            html.escape(next_deadline[1]) if next_deadline else "keine gebuchte Reise"),
    }

    doc = (_TEMPLATE
           .replace("__CARDS__", json.dumps(cards))
           .replace("__SUMMARY__", json.dumps(summary))
           .replace("__CUR__", config.CURRENCY)
           .replace("__GEN__", today.strftime("%d.%m.%Y")))
    with open(out_path, "w") as f:
        f.write(doc)
    print(f"Dashboard geschrieben: {out_path} ({len(cards)} Strecken)")
    return out_path


_TEMPLATE = r"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Flugpreis-Monitor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
:root{
  --paper:#F4F2EC; --card:#FFFFFF; --ink:#22323C; --muted:#6C7680;
  --line:#E6E1D6; --accent:#2B4C7E; --brass:#A98B4B;
  --good:#2F7A57; --warn:#B4623A; --alert:#9B2D3A;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:Inter,system-ui,sans-serif;font-size:14px;line-height:1.5;
  -webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.wrap{max-width:1120px;margin:0 auto;padding:0 24px 64px}
header{padding:40px 0 22px;border-bottom:1px solid var(--line)}
.eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;
  color:var(--brass);font-weight:600}
h1{font-family:Fraunces,serif;font-weight:500;font-size:30px;letter-spacing:-.01em;
  margin:6px 0 2px}
.gen{color:var(--muted);font-size:12.5px}
/* summary */
.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:14px;
  overflow:hidden;margin:26px 0 8px}
.tile{background:var(--card);padding:18px 20px}
.tile .k{font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.tile .v{font-family:Fraunces,serif;font-size:26px;font-weight:500;margin-top:6px}
.tile .s{font-size:12px;color:var(--muted);margin-top:2px}
/* filter */
.bar{display:flex;align-items:center;justify-content:space-between;
  margin:26px 0 14px;flex-wrap:wrap;gap:12px}
.seg{display:inline-flex;background:var(--card);border:1px solid var(--line);
  border-radius:999px;padding:3px}
.seg button{border:0;background:transparent;color:var(--muted);cursor:pointer;
  font:inherit;padding:7px 16px;border-radius:999px}
.seg button.on{background:var(--ink);color:#fff}
.count{color:var(--muted);font-size:13px}
/* grid + card */
.grid{display:grid;gap:18px;grid-template-columns:repeat(auto-fill,minmax(330px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;
  padding:20px;box-shadow:0 1px 2px rgba(34,50,60,.04),0 8px 24px rgba(34,50,60,.04);
  opacity:0;transform:translateY(6px);animation:rise .5s ease forwards}
@keyframes rise{to{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){.card{animation:none;opacity:1;transform:none}}
.c-top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.trip{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--brass);
  font-weight:600}
.route{font-family:Fraunces,serif;font-size:20px;font-weight:500;margin:3px 0 1px}
.sub{color:var(--muted);font-size:12.5px}
.chip{font-size:11.5px;font-weight:500;padding:5px 10px;border-radius:999px;
  white-space:nowrap;border:1px solid transparent}
.chip.scheduled{background:#EEF2F7;color:var(--accent);border-color:#DEE6EF}
.chip.soon{background:#F7EDE6;color:var(--warn);border-color:#ECD9CB}
.chip.overdue{background:#F6E7E9;color:var(--alert);border-color:#EACDD1}
.chip.ticketed{background:#E9F1EC;color:var(--good);border-color:#D4E6DB}
.chip.monitor{background:#F1EFE9;color:var(--muted);border-color:var(--line)}
.price{display:flex;align-items:baseline;gap:10px;margin:16px 0 2px}
.price .now{font-family:Fraunces,serif;font-size:30px;font-weight:500;letter-spacing:-.01em}
.price .unit{color:var(--muted);font-size:12.5px}
.delta{font-size:13px;font-weight:500}
.delta.dn{color:var(--good)} .delta.up{color:var(--warn)}
.meta{display:flex;gap:16px;color:var(--muted);font-size:12.5px;margin:6px 0 12px;
  flex-wrap:wrap}
.meta b{color:var(--ink);font-weight:600}
.pax{color:var(--ink)}
canvas{max-height:120px}
footer{margin-top:34px;color:var(--muted);font-size:12px;text-align:center}
</style></head>
<body><div class="wrap">
<header>
  <div class="eyebrow">Fernreisen · Preisüberwachung</div>
  <h1>Flugpreis-Monitor</h1>
  <div class="gen">Stand __GEN__ · Preise pro Gast in __CUR__</div>
</header>

<div class="summary" id="summary"></div>

<div class="bar">
  <div class="seg" id="seg"></div>
  <div class="count" id="count"></div>
</div>

<div class="grid" id="grid"></div>
<footer>Ticketing-Deadline = Abflug − 25 Tage (~3,5 Wochen). Historie ist vollständig gespeichert.</footer>
</div>
<script>
const CARDS=__CARDS__, S=__SUMMARY__;
document.getElementById('summary').innerHTML=`
 <div class="tile"><div class="k">Beobachtet</div><div class="v">${S.watched}</div><div class="s">Verbindungen</div></div>
 <div class="tile"><div class="k">Gebucht</div><div class="v">${S.booked}</div><div class="s">mit Ticketing-Frist</div></div>
 <div class="tile"><div class="k">Tiefstwerte jetzt</div><div class="v">${S.lows}</div><div class="s">aktuell am günstigsten</div></div>
 <div class="tile"><div class="k">Nächste Deadline</div><div class="v">${S.next_deadline}</div><div class="s">${S.next_deadline_sub}</div></div>`;

const companies=[...new Set(CARDS.map(c=>c.company))];
const seg=document.getElementById('seg');
['alle',...companies].forEach((c,i)=>{
  const b=document.createElement('button');b.textContent=c;
  if(i===0)b.classList.add('on');b.onclick=()=>{document.querySelectorAll('.seg button').forEach(x=>x.classList.remove('on'));b.classList.add('on');render(c==='alle'?'':c);};
  seg.appendChild(b);
});

function render(f){
  const grid=document.getElementById('grid');grid.innerHTML='';
  const items=CARDS.filter(c=>!f||c.company===f);
  document.getElementById('count').textContent=`${items.length} von ${CARDS.length}`;
  items.forEach((c,idx)=>{
    const dn=c.vs_avg<=0;
    const el=document.createElement('div');el.className='card';
    el.style.animationDelay=(Math.min(idx,12)*22)+'ms';
    el.innerHTML=`
     <div class="c-top">
       <div><div class="trip">${c.company} · ${c.trip}</div>
        <div class="route">${c.route}</div><div class="sub">${c.sub}</div></div>
       <span class="chip ${c.state}">${c.state_label}</span>
     </div>
     <div class="price"><span class="now">${c.current} €</span>
       <span class="unit">/ Gast</span>
       <span class="delta ${dn?'dn':'up'}">${dn?'▼':'▲'} ${dn?'':'+'}${c.vs_avg} € ggü. Schnitt</span></div>
     <div class="meta"><span>Schnitt <b>${c.avg} €</b></span>
       <span>Spanne <b>${c.min}–${c.max} €</b></span>
       <span class="pax">Gäste <b>${c.pax}</b></span>
       <span>${c.n} Messungen</span></div>
     <canvas id="cv_${c.id}"></canvas>`;
    grid.appendChild(el);
    new Chart(document.getElementById('cv_'+c.id),{type:'line',
      data:{labels:c.labels,datasets:[{data:c.values,borderColor:'#2B4C7E',
        backgroundColor:'rgba(43,76,126,.08)',fill:true,tension:.3,
        pointRadius:0,borderWidth:2}]},
      options:{plugins:{legend:{display:false},
        tooltip:{callbacks:{label:x=>x.parsed.y+' €'}}},
        scales:{x:{ticks:{color:'#9AA0A6',maxTicksLimit:5,font:{size:10}},
          grid:{display:false}},
        y:{ticks:{color:'#9AA0A6',maxTicksLimit:4,font:{size:10}},
          grid:{color:'#EFEBE1'}}}}});
  });
}
render('');
</script></body></html>"""


if __name__ == "__main__":
    build()
