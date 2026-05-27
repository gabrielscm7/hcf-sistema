from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Text, Boolean, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

DATABASE_URL = "sqlite:///./handball.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─── Enums ────────────────────────────────────────────────────────────────────
class PositionEnum(str, enum.Enum):
    armador_central  = "Armador Central"
    armador_lateral  = "Armador Lateral"
    ponta            = "Ponta"
    pivo             = "Pivô"
    goleiro          = "Goleiro"

class SessionTypeEnum(str, enum.Enum):
    forca            = "Força"
    potencia         = "Potência"
    resistencia_aer  = "Resistência Aeróbica"
    resistencia_ana  = "Resistência Anaeróbica"
    velocidade       = "Velocidade/Sprints"
    agilidade        = "Agilidade/COD"
    tecnico_tatico   = "Técnico-Tático"
    jogo             = "Jogo/Competição"
    recuperacao      = "Recuperação Ativa"
    folga            = "Folga"

class SessionOriginEnum(str, enum.Enum):
    prep_fisica      = "Prep. Física"
    comissao         = "Comissão Técnica"
    jogo             = "Jogo"
    outro            = "Outro"

# ─── Models ───────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String, unique=True, index=True, nullable=False)
    hashed_pw     = Column(String, nullable=False)
    role          = Column(String, default="athlete")  # "staff" | "athlete"
    athlete_id    = Column(Integer, ForeignKey("athletes.id"), nullable=True)
    athlete       = relationship("Athlete", back_populates="user")

class Athlete(Base):
    __tablename__ = "athletes"
    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String, nullable=False)
    position        = Column(String, nullable=False)
    date_of_birth   = Column(Date, nullable=True)
    weight_kg       = Column(Float, nullable=True)
    height_cm       = Column(Float, nullable=True)
    dominant_side   = Column(String, nullable=True)
    experience_years= Column(Integer, nullable=True)
    shirt_number    = Column(Integer, nullable=True)
    contact         = Column(String, nullable=True)
    health_history  = Column(Text, nullable=True)
    injury_history  = Column(Text, nullable=True)
    photo_url       = Column(String, nullable=True)
    active          = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    user            = relationship("User", back_populates="athlete", uselist=False)
    loads           = relationship("SessionLoad", back_populates="athlete")
    wellness        = relationship("Wellness", back_populates="athlete")
    test_results    = relationship("TestResult", back_populates="athlete")
    strength_logs   = relationship("StrengthLog", back_populates="athlete")
    running_logs    = relationship("RunningLog", back_populates="athlete")
    injuries        = relationship("InjuryRecord", back_populates="athlete")

class SessionLoad(Base):
    __tablename__ = "session_loads"
    id              = Column(Integer, primary_key=True, index=True)
    athlete_id      = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    date            = Column(Date, nullable=False)
    week_number     = Column(Integer, nullable=True)
    session_type    = Column(String, nullable=False)
    session_origin  = Column(String, nullable=False, default="Prep. Física")
    volume_min      = Column(Integer, nullable=False)  # duration in minutes
    pse             = Column(Integer, nullable=False)   # 1–10
    rest_perception = Column(Integer, nullable=True)    # 1–5
    load_ua         = Column(Float)                     # calculated: pse × volume
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    athlete         = relationship("Athlete", back_populates="loads")

class Wellness(Base):
    __tablename__ = "wellness"
    id              = Column(Integer, primary_key=True, index=True)
    athlete_id      = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    date            = Column(Date, nullable=False)
    sleep_hours     = Column(Float, nullable=True)
    sleep_quality   = Column(Integer, nullable=True)   # 1–5
    muscle_fatigue  = Column(Integer, nullable=True)   # 1–10
    muscle_soreness = Column(Integer, nullable=True)   # 1–10
    pain_level      = Column(Integer, nullable=True)   # 1–10
    hydration       = Column(Integer, nullable=True)   # 1–5
    psych_stress    = Column(Integer, nullable=True)   # 1–10
    mood            = Column(Integer, nullable=True)   # 1–5
    wellness_score  = Column(Float, nullable=True)     # auto-calculated
    available       = Column(String, nullable=True)    # Sim / Monitorar / Não
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    athlete         = relationship("Athlete", back_populates="wellness")

class StrengthLog(Base):
    __tablename__ = "strength_logs"
    id              = Column(Integer, primary_key=True, index=True)
    athlete_id      = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    date            = Column(Date, nullable=False)
    exercise        = Column(String, nullable=False)
    set_number      = Column(Integer, nullable=False)
    reps            = Column(Integer, nullable=False)
    load_kg         = Column(Float, nullable=False)
    execution_speed = Column(Integer, nullable=True)   # 1=slow 3=explosive
    volume_kg       = Column(Float, nullable=True)     # sets×reps×kg
    one_rm_epley    = Column(Float, nullable=True)
    pse_session     = Column(Integer, nullable=True)
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    athlete         = relationship("Athlete", back_populates="strength_logs")

class RunningLog(Base):
    __tablename__ = "running_logs"
    id              = Column(Integer, primary_key=True, index=True)
    athlete_id      = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    date            = Column(Date, nullable=False)
    session_type    = Column(String, nullable=False)
    total_distance_m= Column(Integer, nullable=True)
    hi_distance_m   = Column(Integer, nullable=True)   # >85% HRmax
    n_sprints       = Column(Integer, nullable=True)
    max_speed_kmh   = Column(Float, nullable=True)
    avg_speed_kmh   = Column(Float, nullable=True)
    duration_min    = Column(Integer, nullable=True)
    hr_max          = Column(Integer, nullable=True)
    hr_avg          = Column(Integer, nullable=True)
    pse             = Column(Integer, nullable=True)
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    athlete         = relationship("Athlete", back_populates="running_logs")

class TestResult(Base):
    __tablename__ = "test_results"
    id              = Column(Integer, primary_key=True, index=True)
    athlete_id      = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    date            = Column(Date, nullable=False)
    test_name       = Column(String, nullable=False)
    capacity        = Column(String, nullable=False)
    value           = Column(Float, nullable=False)
    unit            = Column(String, nullable=False)
    classification  = Column(String, nullable=True)
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    athlete         = relationship("Athlete", back_populates="test_results")

class InjuryRecord(Base):
    __tablename__ = "injury_records"
    id              = Column(Integer, primary_key=True, index=True)
    athlete_id      = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    date_onset      = Column(Date, nullable=False)
    date_return     = Column(Date, nullable=True)
    injury_type     = Column(String, nullable=False)
    body_location   = Column(String, nullable=False)
    mechanism       = Column(String, nullable=True)
    severity        = Column(String, nullable=True)   # Leve / Moderada / Grave
    days_out        = Column(Integer, nullable=True)
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    athlete         = relationship("Athlete", back_populates="injuries")

def create_tables():
    Base.metadata.create_all(bind=engine)
