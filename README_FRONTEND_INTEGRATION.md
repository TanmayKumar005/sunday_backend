# S.U.N.D.A.Y. Frontend Integration

The repository now includes a `frontend/` React + Vite MVP connected to the existing FastAPI backend.

## Run backend

```powershell
uvicorn app.main:app --reload
```

## Run frontend

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend defaults to `http://127.0.0.1:5173` and the API defaults to `http://127.0.0.1:8000`.

The frontend uses real curriculum, learner, assessment, adaptation, scaffold, result and progress endpoints. It contains no mock learner/progress/question data.

### Small backend integration changes

- Added local-development CORS for Vite (`127.0.0.1:5173` and `localhost:5173`).
- Added optional `unit_id` to `POST /assessments/start` so section practice can create an assessment from the selected real section instead of using unrelated questions.
