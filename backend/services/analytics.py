from datetime import date, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from database import SessionLoad

def get_loads_in_range(db: Session, athlete_id: int, start: date, end: date) -> List[SessionLoad]:
    return db.query(SessionLoad).filter(
        SessionLoad.athlete_id == athlete_id,
        SessionLoad.date >= start,
        SessionLoad.date <= end
    ).order_by(SessionLoad.date).all()

def calc_acwr(db: Session, athlete_id: int, ref_date: date) -> Dict:
    """Acute:Chronic Workload Ratio — Gabbett (2016)
    Acute  = carga total dos últimos 7 dias
    Chronic= média semanal dos últimos 28 dias
    ACWR   = Acute / (Chronic / 4)
    """
    acute_start   = ref_date - timedelta(days=6)
    chronic_start = ref_date - timedelta(days=27)

    acute_loads   = get_loads_in_range(db, athlete_id, acute_start, ref_date)
    chronic_loads = get_loads_in_range(db, athlete_id, chronic_start, ref_date)

    acute_total   = sum(l.load_ua or 0 for l in acute_loads)
    chronic_total = sum(l.load_ua or 0 for l in chronic_loads)
    chronic_weekly= chronic_total / 4 if chronic_total > 0 else 0

    acwr = round(acute_total / chronic_weekly, 2) if chronic_weekly > 0 else None

    if acwr is None:
        zone = "Sem dados"
        risk = "neutral"
    elif acwr < 0.8:
        zone = "Subtreino"
        risk = "warning"
    elif acwr <= 1.3:
        zone = "Ótima"
        risk = "safe"
    elif acwr <= 1.5:
        zone = "Atenção"
        risk = "warning"
    else:
        zone = "Risco"
        risk = "danger"

    return {
        "acute_load":    round(acute_total, 1),
        "chronic_load":  round(chronic_total, 1),
        "chronic_weekly":round(chronic_weekly, 1),
        "acwr":          acwr,
        "zone":          zone,
        "risk":          risk,
    }

def calc_monotony(db: Session, athlete_id: int, ref_date: date) -> Dict:
    """Foster's Training Monotony & Strain
    Monotony = média diária / desvio padrão (7 dias)
    Strain   = carga semanal × monotonia
    """
    import statistics
    start = ref_date - timedelta(days=6)
    loads = get_loads_in_range(db, athlete_id, start, ref_date)

    daily: Dict[date, float] = {}
    for l in loads:
        daily[l.date] = daily.get(l.date, 0) + (l.load_ua or 0)

    # Fill missing days with 0
    all_vals = []
    for i in range(7):
        d = start + timedelta(days=i)
        all_vals.append(daily.get(d, 0))

    mean   = statistics.mean(all_vals)
    stdev  = statistics.stdev(all_vals) if len(all_vals) > 1 else 0
    monotony = round(mean / stdev, 2) if stdev > 0 else None
    strain   = round(sum(all_vals) * monotony, 1) if monotony else None

    return {
        "daily_loads":     all_vals,
        "mean_daily_load": round(mean, 1),
        "monotony":        monotony,
        "strain":          strain,
    }

def weekly_load_by_type(db: Session, athlete_id: int, ref_date: date) -> List[Dict]:
    """Breakdown of weekly load by session type and origin."""
    start = ref_date - timedelta(days=6)
    loads = get_loads_in_range(db, athlete_id, start, ref_date)

    breakdown: Dict[str, Dict] = {}
    for l in loads:
        key = l.session_type
        if key not in breakdown:
            breakdown[key] = {
                "session_type": l.session_type,
                "origin":       l.session_origin,
                "count":        0,
                "total_volume": 0,
                "total_ua":     0,
                "pse_sum":      0,
            }
        breakdown[key]["count"]        += 1
        breakdown[key]["total_volume"] += l.volume_min or 0
        breakdown[key]["total_ua"]     += l.load_ua or 0
        breakdown[key]["pse_sum"]      += l.pse or 0

    result = []
    total_ua = sum(v["total_ua"] for v in breakdown.values())
    for b in breakdown.values():
        b["avg_pse"] = round(b["pse_sum"] / b["count"], 1) if b["count"] else 0
        b["pct_total"] = round(b["total_ua"] / total_ua * 100, 1) if total_ua else 0
        result.append(b)

    return sorted(result, key=lambda x: x["total_ua"], reverse=True)

def load_trend(db: Session, athlete_id: int, n_weeks: int = 4) -> List[Dict]:
    """Weekly load trend for the last n weeks."""
    today = date.today()
    weeks = []
    for w in range(n_weeks - 1, -1, -1):
        week_end   = today - timedelta(weeks=w)
        week_start = week_end - timedelta(days=6)
        loads = get_loads_in_range(db, athlete_id, week_start, week_end)
        total_ua   = sum(l.load_ua or 0 for l in loads)
        pse_vals   = [l.pse for l in loads if l.pse]
        weeks.append({
            "week":       f"S{n_weeks - w:02d}",
            "start":      str(week_start),
            "end":        str(week_end),
            "total_ua":   round(total_ua, 1),
            "avg_pse":    round(sum(pse_vals)/len(pse_vals), 1) if pse_vals else 0,
            "sessions":   len(loads),
            "acwr_data":  calc_acwr(db, athlete_id, week_end),
        })
    return weeks

def group_availability(db: Session, athlete_ids: List[int], ref_date: date) -> List[Dict]:
    """Quick availability + ACWR overview for the full squad."""
    from database import Athlete, Wellness
    result = []
    for aid in athlete_ids:
        acwr_data = calc_acwr(db, aid, ref_date)
        w = db.query(Wellness).filter(
            Wellness.athlete_id == aid,
            Wellness.date == ref_date
        ).first()
        ath = db.query(Athlete).filter(Athlete.id == aid).first()
        result.append({
            "athlete_id":   aid,
            "name":         ath.name if ath else "—",
            "position":     ath.position if ath else "—",
            "acwr":         acwr_data["acwr"],
            "acwr_zone":    acwr_data["zone"],
            "acwr_risk":    acwr_data["risk"],
            "wellness_score": w.wellness_score if w else None,
            "available":    w.available if w else "Sem dado",
        })
    return result
