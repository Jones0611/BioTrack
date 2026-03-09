from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha = Column(String, nullable=False)
    tipo = Column(String)  # 'atleta', 'professor' ou 'admin'
    
    strava_access_token = Column(String, nullable=True)
    strava_refresh_token = Column(String, nullable=True)
    treinos = relationship("Treino", back_populates="atleta")

class Treino(Base):
    __tablename__ = "treinos"
    id = Column(Integer, primary_key=True, index=True)
    data = Column(String, nullable=False) # Formato YYYY-MM-DD
    tipo_treino = Column(String) 
    concluido = Column(Boolean, default=False)
    
    # Metas para Corrida/Ironman
    distancia_meta_km = Column(Float, nullable=True)
    tempo_meta_min = Column(Float, nullable=True)
    feedback_geral = Column(String, nullable=True)
    
    atleta_id = Column(Integer, ForeignKey("usuarios.id"))
    atleta = relationship("Usuario", back_populates="treinos")
    exercicios = relationship("Exercicio", back_populates="treino")

class Exercicio(Base):
    __tablename__ = "exercicios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    series = Column(Integer)
    repeticoes = Column(Integer)
    carga_planejada = Column(String, nullable=True)
    carga_realizada = Column(String, nullable=True) # Onde o João edita
    
    treino_id = Column(Integer, ForeignKey("treinos.id"))
    treino = relationship("Treino", back_populates="exercicios")