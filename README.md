# Ekonum · Pilotage financier

Application web pour construire un budget multi-années, suivre la trésorerie et comparer budget vs réalisé pour une agence d'intégration Odoo.

## Architecture
- **Backend** : FastAPI + SQLModel (SQLite). API REST `backend/main.py` exposant la gestion des offres, contrats, échéanciers, charges fixes, immobilisations et emprunts, ainsi que la projection budgétaire.
- **Calculs** : `backend/services/calculations.py` génère P&L mensuel et cash-flow en combinant revenus (forfaits, récurrents, licences), coûts variables, charges fixes, amortissements et échéanciers de prêts, puis produit un comparatif budget vs réalisé si des écritures réelles sont présentes.
- **Frontend** : React + Vite (TypeScript) dans `frontend/`. Écran principal pour configurer les paramètres fiscaux, charger des hypothèses types, injecter des réalisés de test et visualiser le tableau P&L / cash ainsi que le comparatif budget vs réalisé.

## Lancer localement
```bash
# Backend (depuis la racine du dépôt)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install --upgrade --force-reinstall -r requirements.txt

# Lancez Uvicorn depuis la racine (ou restez dans backend mais ciblez main:app)
# Option 1
uvicorn backend.main:app --reload  # exécuter depuis la racine du dépôt
# Option 2
# cd backend && uvicorn main:app --reload

# Frontend
cd ../frontend
npm install
npm run dev -- --host
```

Configurez `VITE_API_URL` (ex: `http://localhost:8000/api`) pour que le frontend atteigne l'API.
