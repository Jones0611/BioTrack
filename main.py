import os
import requests
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

import models
from database import engine, get_db

# Inicialização
load_dotenv()
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BioTrack API - PRO",
    description="Gestão de Treinos, Strava, Clima e Dashboard de Performance.",
    version="3.5.0"
)

# --- CONFIGURAÇÕES ---
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "chave_secreta_pfc_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- SCHEMAS ---
class FeedbackCarga(BaseModel):
    id: int
    carga: str

class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str
    tipo: str # 'atleta', 'professor', 'admin'

class Token(BaseModel):
    access_token: str
    token_type: str

class ExercicioSchema(BaseModel):
    nome: str
    series: int
    repeticoes: int
    carga_planejada: Optional[str] = None

class TreinoCreate(BaseModel):
    atleta_id: int
    data: str # YYYY-MM-DD
    tipo_treino: str
    distancia_meta_km: Optional[float] = None
    tempo_meta_min: Optional[float] = None
    exercicios: List[ExercicioSchema]

class DashStatus(BaseModel):
    treinos_totais: int
    treinos_concluidos: int
    km_acumulados: float
    clima_hoje: Optional[str] = None
    temperatura: Optional[str] = None

# --- UTILITÁRIOS DE SEGURANÇA ---
def verificar_senha(senha_pura, senha_hash):
    return pwd_context.verify(senha_pura, senha_hash)

def gerar_hash_senha(senha):
    return pwd_context.hash(senha)

def criar_token_acesso(data: dict):
    para_codificar = data.copy()
    expira = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    para_codificar.update({"exp": expira})
    return jwt.encode(para_codificar, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Token inválido")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None: raise credentials_exception
    except JWTError: raise credentials_exception
    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if user is None: raise credentials_exception
    return user

# --- FUNÇÃO DE REFRESH DO STRAVA ---
def renovar_token_strava(usuario, db: Session):
    response = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": usuario.strava_refresh_token
    })
    if response.status_code == 200:
        dados = response.json()
        usuario.strava_access_token = dados["access_token"]
        usuario.strava_refresh_token = dados.get("refresh_token", usuario.strava_refresh_token)
        db.commit()
        return dados["access_token"]
    return None

# --- ROTAS ---

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    if not user or not verificar_senha(form_data.password, user.senha):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    return {"access_token": criar_token_acesso(data={"sub": user.email}), "token_type": "bearer"}

@app.post("/usuarios/")
def cadastrar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    if db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first():
        raise HTTPException(status_code=400, detail="E-mail já existe")
    novo = models.Usuario(nome=usuario.nome, email=usuario.email, senha=gerar_hash_senha(usuario.senha), tipo=usuario.tipo)
    db.add(novo); db.commit(); db.refresh(novo)
    return {"id": novo.id}

@app.get("/dashboard", response_model=DashStatus)
def get_dashboard(current_user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    # Estatísticas de Treino
    treinos = db.query(models.Treino).filter(models.Treino.atleta_id == current_user.id).all()
    total = len(treinos)
    concluidos = len([t for t in treinos if t.concluido])
    km_total = db.query(func.sum(models.Treino.distancia_meta_km)).filter(
        models.Treino.atleta_id == current_user.id, 
        models.Treino.concluido == True
    ).scalar() or 0.0

    # Busca de Clima (Mogi das Cruzes como padrão)
    clima_desc, temp_atual = "Indisponível", "--"
    if OPENWEATHER_API_KEY:
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q=Mogi das Cruzes&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
            r = requests.get(url, timeout=5).json()
            clima_desc = r['weather'][0]['description'].capitalize()
            temp_atual = f"{r['main']['temp']}°C"
        except: pass

    return {
        "treinos_totais": total,
        "treinos_concluidos": concluidos,
        "km_acumulados": round(km_total, 2),
        "clima_hoje": clima_desc,
        "temperatura": temp_atual
    }

@app.post("/treinos/")
def criar_treino(treino_in: TreinoCreate, current_user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.tipo not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Apenas professores/admins")
    
    data_treino = datetime.strptime(treino_in.data, "%Y-%m-%d")
    if data_treino < datetime.now() - timedelta(days=365):
        raise HTTPException(status_code=400, detail="Data de treino muito antiga.")

    novo_treino = models.Treino(
        atleta_id=treino_in.atleta_id, data=treino_in.data, tipo_treino=treino_in.tipo_treino,
        distancia_meta_km=treino_in.distancia_meta_km, tempo_meta_min=treino_in.tempo_meta_min
    )
    db.add(novo_treino); db.commit(); db.refresh(novo_treino)
    
    for ex in treino_in.exercicios:
        db.add(models.Exercicio(nome=ex.nome, series=ex.series, repeticoes=ex.repeticoes, 
                                carga_planejada=ex.carga_planejada, treino_id=novo_treino.id))
    db.commit()
    return {"id": novo_treino.id}

@app.patch("/treinos/{treino_id}/feedback-atleta")
def atualizar_performance_musculacao(
    treino_id: int, cargas_reais: List[FeedbackCarga], 
    current_user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)
):
    treino = db.query(models.Treino).filter(models.Treino.id == treino_id, models.Treino.atleta_id == current_user.id).first()
    if not treino: raise HTTPException(status_code=404, detail="Treino não encontrado")

    data_treino = datetime.strptime(treino.data, "%Y-%m-%d")
    if data_treino < datetime.now() - timedelta(days=7):
         raise HTTPException(status_code=400, detail="Prazo para feedback expirado (7 dias).")

    for item in cargas_reais:
        ex = db.query(models.Exercicio).filter(models.Exercicio.id == item.id, models.Exercicio.treino_id == treino_id).first()
        if ex: ex.carga_realizada = item.carga
    
    treino.concluido = True
    db.commit()
    return {"status": "Progresso salvo!"}

@app.get("/strava/analisar/{treino_id}")
def comparar_strava_pfc(treino_id: int, current_user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    treino = db.query(models.Treino).filter(models.Treino.id == treino_id).first()
    if not treino: raise HTTPException(status_code=404)
    
    token = current_user.strava_access_token
    if not token: raise HTTPException(status_code=400, detail="Conecte ao Strava")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get("https://www.strava.com/api/v3/athlete/activities", headers=headers)

    if response.status_code == 401:
        token = renovar_token_strava(current_user, db)
        if not token: raise HTTPException(status_code=401, detail="Reconecte ao Strava.")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("https://www.strava.com/api/v3/athlete/activities", headers=headers)

    atividades = response.json()
    for ativ in atividades:
        if ativ['start_date_local'][:10] == treino.data:
            dist_real = ativ['distance'] / 1000
            meta = treino.distancia_meta_km or 0
            foi_concluido = dist_real >= (meta * 0.95) if meta > 0 else True
            treino.concluido = foi_concluido
            db.commit()
            return {"status": "Concluído" if foi_concluido else "Incompleto", "realizado": dist_real}
            
    return {"status": "Pendente", "mensagem": "Atividade não encontrada no Strava."}

@app.get("/strava/conectar/{atleta_id}")
def gerar_link_strava(atleta_id: int):
    scope = "read,activity:read_all"
    redirect_uri = "http://localhost:8000/strava/callback"
    return {"url": f"https://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}&response_type=code&redirect_uri={redirect_uri}&scope={scope}&state={atleta_id}"}

@app.get("/strava/callback")
def strava_callback(code: str, state: str, db: Session = Depends(get_db)):
    response = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": STRAVA_CLIENT_ID, "client_secret": STRAVA_CLIENT_SECRET, 
        "code": code, "grant_type": "authorization_code"
    }).json()
    
    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(state)).first()
    if usuario and "access_token" in response:
        usuario.strava_access_token = response["access_token"]
        usuario.strava_refresh_token = response["refresh_token"]
        db.commit()
        return {"status": "Sincronizado!"}
    return {"erro": "Falha na sincronização"}