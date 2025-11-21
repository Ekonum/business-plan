# Ekonum · Pilotage financier

Application web pour construire un budget multi-années, suivre la trésorerie et comparer budget vs réalisé pour une agence d'intégration Odoo.

## Architecture
- **Backend** : FastAPI + SQLModel (SQLite). API REST `backend/main.py` exposant la gestion des offres, contrats, échéanciers, charges fixes, immobilisations et emprunts, ainsi que la projection budgétaire.
- **Calculs** : `backend/services/calculations.py` génère P&L mensuel et cash-flow en combinant revenus (forfaits, récurrents, licences), coûts variables, charges fixes, amortissements et échéanciers de prêts.
- **Frontend** : React + Vite (TypeScript) dans `frontend/`. Écran principal pour configurer les paramètres fiscaux, charger des hypothèses types et visualiser le tableau P&L / cash.

## Lancer localement
```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload

# Frontend
cd ../frontend
npm install
npm run dev -- --host
```

Configurez `VITE_API_URL` (ex: `http://localhost:8000/api`) pour que le frontend atteigne l'API.
