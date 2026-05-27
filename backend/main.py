from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
import os, sys

sys.path.insert(0, os.path.dirname(__file__))

from database import create_tables, SessionLocal, User, Athlete
from services.auth import hash_password
from routes.api import router
from datetime import date

app = FastAPI(
    title="Handball Conditioning System",
    description="Sistema de Controle de Condicionamento Físico — Handebol",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")

@app.get("/")
def root():
    return RedirectResponse(url="/app/")

@app.on_event("startup")
def startup():
    create_tables()
    _seed_demo_data()

def _seed_demo_data():
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return  # already seeded

        # Staff user
        staff = User(username="gabriel", hashed_pw=hash_password("admin123"), role="staff")
        db.add(staff); db.flush()

        # Athletes
        athletes_data = [
            ("Gabriel",        "Armador Central",  date(1990,3,15), 87.0, 173.0),
            ("Lucas Ferreira", "Armador Lateral",  date(1998,6,10), 82.0, 181.0),
            ("Thiago Souza",   "Ponta",            date(1999,2,20), 78.0, 177.0),
            ("Rafael Oliveira","Pivô",             date(1997,11,5), 95.0, 185.0),
            ("Bruno Carvalho", "Goleiro",          date(1996,8,14), 88.0, 190.0),
            ("Mateus Lima",    "Armador Central",  date(2001,4,22), 80.0, 179.0),
            ("Pedro Alves",    "Armador Lateral",  date(2000,9,3),  83.0, 183.0),
            ("Felipe Rocha",   "Ponta",            date(2002,1,17), 76.0, 175.0),
            ("André Martins",  "Pivô",             date(1998,7,29), 98.0, 188.0),
            ("Caio Mendes",    "Armador Central",  date(2001,12,8), 81.0, 178.0),
            ("Diego Costa",    "Ponta",            date(1999,5,11), 77.0, 174.0),
            ("Henrique Nunes", "Goleiro",          date(1997,3,25), 90.0, 192.0),
            ("Rodrigo Pires",  "Armador Lateral",  date(2000,10,7), 84.0, 182.0),
            ("Vinícius Teles", "Pivô",             date(1996,1,30), 99.0, 187.0),
            ("Eduardo Freitas","Armador Central",  date(2002,8,15), 79.0, 176.0),
            ("Gustavo Borges", "Ponta",            date(1998,4,18), 75.0, 172.0),
            ("Carlos Pereira", "Armador Lateral",  date(2001,6,23), 85.0, 184.0),
            ("Fernando Dias",  "Goleiro",          date(1997,9,12), 91.0, 191.0),
            ("Leonardo Mota",  "Pivô",             date(1999,2,6),  96.0, 186.0),
            ("Marcos Ribeiro", "Armador Central",  date(2000,11,19),82.0, 180.0),
        ]

        created_athletes = []
        for name, pos, dob, w, h in athletes_data:
            ath = Athlete(name=name, position=pos, date_of_birth=dob,
                          weight_kg=w, height_cm=h,
                          health_history="Sem histórico relevante",
                          injury_history="Sem lesões prévias")
            db.add(ath); db.flush()
            created_athletes.append(ath)

        # Link Gabriel (staff) to first athlete
        staff.athlete_id = created_athletes[0].id

        # Create athlete users (username = first name lowercase)
        for ath in created_athletes[1:]:
            uname = ath.name.split()[0].lower()
            u = User(username=uname, hashed_pw=hash_password("atleta123"),
                     role="athlete", athlete_id=ath.id)
            db.add(u)

        db.commit()

        # Seed session loads (28 days back) for ACWR demo
        from database import SessionLoad
        from datetime import date as dt_date, timedelta
        import random as rnd
        rnd.seed(99)
        today = dt_date.today()
        WEEK_TEMPLATE = [
            (0, "Força",               "Prep. Física",    70, 7),
            (1, "Técnico-Tático",      "Comissão Técnica",90, 7),
            (2, "Velocidade/Sprints",  "Prep. Física",    65, 8),
            (3, "Técnico-Tático",      "Comissão Técnica",90, 7),
            (4, "Resistência Aeróbica","Prep. Física",    60, 6),
            (5, "Jogo/Competição",     "Jogo",            90, 8),
        ]
        for ath in created_athletes:
            for w in range(4):
                week_start = today - timedelta(weeks=3-w)
                for day_off, stype, origin, vol_base, pse_base in WEEK_TEMPLATE:
                    d = week_start + timedelta(days=day_off)
                    if d > today: continue
                    vol = vol_base + rnd.randint(-8, 8)
                    pse = max(1, min(10, pse_base + rnd.randint(-1, 1)))
                    load = SessionLoad(
                        athlete_id=ath.id, date=d,
                        week_number=d.isocalendar()[1],
                        session_type=stype, session_origin=origin,
                        volume_min=vol, pse=pse,
                        rest_perception=rnd.randint(2,5),
                        load_ua=round(pse*vol, 1)
                    )
                    db.add(load)
        db.commit()
        print("✅ Dados de demonstração inseridos")
        print("   Staff login: gabriel / admin123")
        print("   Athlete login: lucas / atleta123  (e demais pelo primeiro nome)")
    except Exception as e:
        db.rollback()
        print(f"⚠️  Seed error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
