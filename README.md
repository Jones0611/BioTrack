# 🏃‍♂️ BioTrack API - PRO 🚴‍♂️🏊‍♂️

O **BioTrack** é uma API robusta de gestão de performance esportiva, focada em triatletas e atletas de endurance (Ironman). O sistema integra dados do **Strava**, previsões meteorológicas em tempo real e uma estrutura de permissões para Professores e Atletas.

## 🚀 Funcionalidades Principais

* **🛡️ Segurança de Nível Profissional**: Autenticação via JWT (JSON Web Tokens) com diferenciação de escopo (Admin, Professor e Atleta).
* **📊 Dashboard de Performance**: Rota centralizada com estatísticas de treinos totais, conclusão de metas e quilometragem acumulada.
* **🧡 Integração Strava v3**: 
    * Sincronização automática de atividades.
    * **Auto-Refresh Token**: Renovação automática do acesso sem intervenção do usuário.
    * Validação de metas (Verificação se o atleta cumpriu pelo menos 95% da distância prescrita).
* **☁️ Inteligência Climática**: Integração com OpenWeatherMap para monitoramento das condições de treino em Mogi das Cruzes.
* **🏋️‍♂️ Gestão de Prescrições**: 
    * Professores prescrevem treinos de musculação e corrida.
    * Atletas registram feedbacks de carga e performance.
    * Trava de segurança: Feedbacks permitidos apenas para treinos dos últimos 7 dias.

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.9+
* **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **Banco de Dados:** PostgreSQL / SQLite (via SQLAlchemy)
* **Segurança:** Passlib (Bcrypt) & Jose-JWT
* **Integrações:** Strava API & OpenWeatherMap API

## 📋 Pré-requisitos

Antes de começar, você precisará das seguintes chaves no seu arquivo `.env`:

```env
STRAVA_CLIENT_ID=seu_id
STRAVA_CLIENT_SECRET=seu_secret
OPENWEATHER_API_KEY=sua_chave_weather
SECRET_KEY=sua_chave_secreta_jwt
