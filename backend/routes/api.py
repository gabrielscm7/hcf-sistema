from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

from database import get_db, User, Athlete, SessionLoad, Wellness, StrengthLog, RunningLog, TestResult, InjuryRecord
from services.auth import (hash_password, verify_password, create_access_token,
                            get_current_user, require_staff, require_athlete_or_staff)
from services.analytics import calc_acwr, calc_monotony, weekly_load_by_type, load_trend, group_availability

router = APIRouter()

# ─── Schemas ──────────────────────────────────────────────────────────────────
class TokenOut(BaseModel):
    access_token: str
    token_type:   str
    role:         str
    athlete_id:   Optional[int] = None
    name:         str

class AthleteCreate(BaseModel):
    name:            str
    position:        str
    date_of_birth:   Optional[date] = None
    weight_kg:       Optional[float] = None
    height_cm:       Optional[float] = None
    dominant_side:   Optional[str] = None
    experience_years:Optional[int] = None
    shirt_number:    Optional[int] = None
    contact:         Optional[str] = None
    health_history:  Optional[str] = None
    injury_history:  Optional[str] = None

class AthleteOut(AthleteCreate):
    id:         int
    photo_url:  Optional[str] = None
    active:     bool
    class Config: from_attributes = True

class LoadCreate(BaseModel):
    date:           date
    session_type:   str
    session_origin: str = "Prep. Física"
    volume_min:     int
    pse:            int
    rest_perception:Optional[int] = None
    notes:          Optional[str] = None

class LoadOut(LoadCreate):
    id:         int
    athlete_id: int
    load_ua:    float
    week_number:Optional[int] = None
    class Config: from_attributes = True

class WellnessCreate(BaseModel):
    date:           date
    sleep_hours:    Optional[float] = None
    sleep_quality:  Optional[int] = None
    muscle_fatigue: Optional[int] = None
    muscle_soreness:Optional[int] = None
    pain_level:     Optional[int] = None
    hydration:      Optional[int] = None
    psych_stress:   Optional[int] = None
    mood:           Optional[int] = None
    notes:          Optional[str] = None

class WellnessOut(WellnessCreate):
    id:             int
    athlete_id:     int
    wellness_score: Optional[float] = None
    available:      Optional[str] = None
    class Config: from_attributes = True

class StrengthCreate(BaseModel):
    date:            date
    exercise:        str
    set_number:      int
    reps:            int
    load_kg:         float
    execution_speed: Optional[int] = None
    pse_session:     Optional[int] = None
    notes:           Optional[str] = None

class RunningCreate(BaseModel):
    date:             date
    session_type:     str
    total_distance_m: Optional[int] = None
    hi_distance_m:    Optional[int] = None
    n_sprints:        Optional[int] = None
    max_speed_kmh:    Optional[float] = None
    avg_speed_kmh:    Optional[float] = None
    duration_min:     Optional[int] = None
    hr_max:           Optional[int] = None
    hr_avg:           Optional[int] = None
    pse:              Optional[int] = None
    notes:            Optional[str] = None

class TestCreate(BaseModel):
    date:           date
    test_name:      str
    capacity:       str
    value:          float
    unit:           str
    classification: Optional[str] = None
    notes:          Optional[str] = None

class UserCreate(BaseModel):
    username:   str
    password:   str
    role:       str = "athlete"
    athlete_id: Optional[int] = None

# ─── Auth ─────────────────────────────────────────────────────────────────────
@router.post("/auth/token", response_model=TokenOut, tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_pw):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    token = create_access_token({"sub": user.username, "role": user.role})
    athlete = db.query(Athlete).filter(Athlete.id == user.athlete_id).first() if user.athlete_id else None
    name = athlete.name if athlete else user.username
    return TokenOut(access_token=token, token_type="bearer",
                    role=user.role, athlete_id=user.athlete_id, name=name)

@router.post("/auth/register", tags=["Auth"])
def register(data: UserCreate, db: Session = Depends(get_db), _=Depends(require_staff)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Usuário já existe")
    user = User(username=data.username, hashed_pw=hash_password(data.password),
                role=data.role, athlete_id=data.athlete_id)
    db.add(user); db.commit(); db.refresh(user)
    return {"id": user.id, "username": user.username, "role": user.role}

# ─── Athletes ─────────────────────────────────────────────────────────────────
@router.get("/athletes", response_model=List[AthleteOut], tags=["Atletas"])
def list_athletes(db: Session = Depends(get_db), _=Depends(require_staff)):
    return db.query(Athlete).filter(Athlete.active == True).all()

@router.post("/athletes", response_model=AthleteOut, tags=["Atletas"])
def create_athlete(data: AthleteCreate, db: Session = Depends(get_db), _=Depends(require_staff)):
    ath = Athlete(**data.model_dump())
    db.add(ath); db.commit(); db.refresh(ath)
    return ath

@router.get("/athletes/{athlete_id}", response_model=AthleteOut, tags=["Atletas"])
def get_athlete(athlete_id: int, db: Session = Depends(get_db), cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    ath = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not ath: raise HTTPException(404, "Atleta não encontrado")
    return ath

@router.put("/athletes/{athlete_id}", response_model=AthleteOut, tags=["Atletas"])
def update_athlete(athlete_id: int, data: AthleteCreate, db: Session = Depends(get_db), _=Depends(require_staff)):
    ath = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not ath: raise HTTPException(404, "Atleta não encontrado")
    for k, v in data.model_dump().items():
        setattr(ath, k, v)
    db.commit(); db.refresh(ath)
    return ath

# ─── Session Loads ────────────────────────────────────────────────────────────
def _calc_load(pse: int, volume: int) -> float:
    return round(pse * volume, 1)

def _week_number(d: date) -> int:
    return d.isocalendar()[1]

@router.post("/athletes/{athlete_id}/loads", response_model=LoadOut, tags=["Carga"])
def create_load(athlete_id: int, data: LoadCreate, db: Session = Depends(get_db),
                cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    load = SessionLoad(
        athlete_id     = athlete_id,
        load_ua        = _calc_load(data.pse, data.volume_min),
        week_number    = _week_number(data.date),
        **data.model_dump()
    )
    db.add(load); db.commit(); db.refresh(load)
    return load

@router.get("/athletes/{athlete_id}/loads", response_model=List[LoadOut], tags=["Carga"])
def get_loads(athlete_id: int, limit: int = 60, db: Session = Depends(get_db),
              cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    return db.query(SessionLoad).filter(SessionLoad.athlete_id == athlete_id)\
             .order_by(SessionLoad.date.desc()).limit(limit).all()

@router.delete("/athletes/{athlete_id}/loads/{load_id}", tags=["Carga"])
def delete_load(athlete_id: int, load_id: int, db: Session = Depends(get_db), _=Depends(require_staff)):
    load = db.query(SessionLoad).filter(SessionLoad.id == load_id, SessionLoad.athlete_id == athlete_id).first()
    if not load: raise HTTPException(404)
    db.delete(load); db.commit()
    return {"ok": True}

# ─── Wellness ─────────────────────────────────────────────────────────────────
def _wellness_score(data: WellnessCreate) -> float:
    vals = [v for v in [data.muscle_fatigue, data.muscle_soreness,
                         data.pain_level, data.psych_stress] if v is not None]
    if not vals: return None
    return round(10 - sum(vals) / len(vals), 1)

def _availability(score: float) -> str:
    if score is None: return "Sem dado"
    if score >= 7: return "Sim"
    if score >= 5: return "Monitorar"
    return "Não"

@router.post("/athletes/{athlete_id}/wellness", response_model=WellnessOut, tags=["Wellness"])
def create_wellness(athlete_id: int, data: WellnessCreate, db: Session = Depends(get_db),
                    cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    # Prevent duplicate for same day
    existing = db.query(Wellness).filter(Wellness.athlete_id == athlete_id,
                                          Wellness.date == data.date).first()
    score = _wellness_score(data)
    avail = _availability(score)
    if existing:
        for k, v in data.model_dump().items(): setattr(existing, k, v)
        existing.wellness_score = score; existing.available = avail
        db.commit(); db.refresh(existing); return existing
    w = Wellness(athlete_id=athlete_id, wellness_score=score, available=avail, **data.model_dump())
    db.add(w); db.commit(); db.refresh(w)
    return w

@router.get("/athletes/{athlete_id}/wellness", response_model=List[WellnessOut], tags=["Wellness"])
def get_wellness(athlete_id: int, limit: int = 30, db: Session = Depends(get_db),
                 cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    return db.query(Wellness).filter(Wellness.athlete_id == athlete_id)\
             .order_by(Wellness.date.desc()).limit(limit).all()

# ─── Strength Logs ────────────────────────────────────────────────────────────
@router.post("/athletes/{athlete_id}/strength", tags=["Carga Externa"])
def create_strength(athlete_id: int, data: StrengthCreate, db: Session = Depends(get_db),
                    cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    vol = round(data.reps * data.load_kg, 1)
    rm  = round(data.load_kg * (1 + data.reps / 30), 1) if data.reps <= 10 else None
    s = StrengthLog(athlete_id=athlete_id, volume_kg=vol, one_rm_epley=rm, **data.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return s

@router.get("/athletes/{athlete_id}/strength", tags=["Carga Externa"])
def get_strength(athlete_id: int, limit: int = 100, db: Session = Depends(get_db),
                 cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    return db.query(StrengthLog).filter(StrengthLog.athlete_id == athlete_id)\
             .order_by(StrengthLog.date.desc()).limit(limit).all()

# ─── Running Logs ─────────────────────────────────────────────────────────────
@router.post("/athletes/{athlete_id}/running", tags=["Carga Externa"])
def create_running(athlete_id: int, data: RunningCreate, db: Session = Depends(get_db),
                   cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    r = RunningLog(athlete_id=athlete_id, **data.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return r

@router.get("/athletes/{athlete_id}/running", tags=["Carga Externa"])
def get_running(athlete_id: int, limit: int = 60, db: Session = Depends(get_db),
                cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    return db.query(RunningLog).filter(RunningLog.athlete_id == athlete_id)\
             .order_by(RunningLog.date.desc()).limit(limit).all()

# ─── Test Results ─────────────────────────────────────────────────────────────
@router.post("/athletes/{athlete_id}/tests", tags=["Testes"])
def create_test(athlete_id: int, data: TestCreate, db: Session = Depends(get_db), _=Depends(require_staff)):
    t = TestResult(athlete_id=athlete_id, **data.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return t

@router.get("/athletes/{athlete_id}/tests", tags=["Testes"])
def get_tests(athlete_id: int, db: Session = Depends(get_db), cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    return db.query(TestResult).filter(TestResult.athlete_id == athlete_id)\
             .order_by(TestResult.date.desc()).all()

# ─── Analytics ────────────────────────────────────────────────────────────────
@router.get("/athletes/{athlete_id}/analytics/acwr", tags=["Analytics"])
def get_acwr(athlete_id: int, ref_date: Optional[date] = None,
             db: Session = Depends(get_db), cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    return calc_acwr(db, athlete_id, ref_date or date.today())

@router.get("/athletes/{athlete_id}/analytics/monotony", tags=["Analytics"])
def get_monotony(athlete_id: int, ref_date: Optional[date] = None,
                 db: Session = Depends(get_db), _=Depends(require_staff)):
    return calc_monotony(db, athlete_id, ref_date or date.today())

@router.get("/athletes/{athlete_id}/analytics/load-breakdown", tags=["Analytics"])
def get_load_breakdown(athlete_id: int, ref_date: Optional[date] = None,
                       db: Session = Depends(get_db), cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    return weekly_load_by_type(db, athlete_id, ref_date or date.today())

@router.get("/athletes/{athlete_id}/analytics/trend", tags=["Analytics"])
def get_trend(athlete_id: int, weeks: int = 4,
              db: Session = Depends(get_db), cu=Depends(require_athlete_or_staff)):
    if cu.role == "athlete" and cu.athlete_id != athlete_id:
        raise HTTPException(403, "Acesso negado")
    return load_trend(db, athlete_id, weeks)

@router.get("/group/analytics/availability", tags=["Analytics Grupo"])
def get_group_availability(ref_date: Optional[date] = None,
                            db: Session = Depends(get_db), _=Depends(require_staff)):
    athletes = db.query(Athlete).filter(Athlete.active == True).all()
    ids = [a.id for a in athletes]
    return group_availability(db, ids, ref_date or date.today())

@router.get("/group/analytics/load-summary", tags=["Analytics Grupo"])
def get_group_load_summary(ref_date: Optional[date] = None,
                            db: Session = Depends(get_db), _=Depends(require_staff)):
    from datetime import timedelta
    today = ref_date or date.today()
    athletes = db.query(Athlete).filter(Athlete.active == True).all()
    result = []
    for ath in athletes:
        acwr_data = calc_acwr(db, ath.id, today)
        trend_data = load_trend(db, ath.id, 4)
        last_week = trend_data[-1] if trend_data else {}
        result.append({
            "athlete_id":   ath.id,
            "name":         ath.name,
            "position":     ath.position,
            "total_ua":     last_week.get("total_ua", 0),
            "avg_pse":      last_week.get("avg_pse", 0),
            "sessions":     last_week.get("sessions", 0),
            "acwr":         acwr_data["acwr"],
            "acwr_zone":    acwr_data["zone"],
            "acwr_risk":    acwr_data["risk"],
        })
    return result
