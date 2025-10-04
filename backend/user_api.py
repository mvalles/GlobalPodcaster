from fastapi import HTTPException
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import firebase_admin
from firebase_admin import credentials, firestore
import json
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto por el dominio de tu frontend en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

firebase_key_json = os.environ.get('FIREBASE_KEY_JSON')
if firebase_key_json:
    import json
    firebase_key_dict = json.loads(firebase_key_json)
    cred = credentials.Certificate(firebase_key_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
else:
    FIREBASE_KEY_PATH = os.environ.get('FIREBASE_KEY_PATH')
    if not FIREBASE_KEY_PATH:
        FIREBASE_KEY_PATH = 'devcontainer/serviceAccountKey.json'
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)
db = firestore.client()

"""User/profile management and simple Firestore-backed API"""

@app.post("/user/create")
async def create_user(request: Request):
    data = await request.json()
    uid = data.get("uid")
    email = data.get("email")
    full_name = data.get("full_name", "")
    if not uid or not email:
        return JSONResponse(content={"status": "error", "error": "uid and email required"}, status_code=400)
    user_ref = db.collection("users").document(uid)
    user_ref.set({
        #"uid": uid,
        "email": email,
        "full_name": full_name,
        "onboarding_completed": False,
        # Optional profile defaults for consistent schema
        "preferred_languages": [],
        "voice_sample_url": None,
        "voice_prompt_seen": False,
        "notification_preferences": {"email_alerts": True},
        #"feeds": [],
    }, merge=True)
    return JSONResponse(content={"status": "success", "uid": uid})


@app.get("/user/me")
async def get_user(request: Request):
    data = await request.json() if request.method == "POST" else {}
    uid = data.get("uid") or request.query_params.get("uid")
    if not uid:
        return JSONResponse(content={"status": "error", "error": "uid required"}, status_code=400)
    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return JSONResponse(content={"status": "error", "error": "User not found"}, status_code=404)
    return JSONResponse(content={"status": "success", "user": user_doc.to_dict()})

# Nuevo endpoint para actualizar usuario
@app.put("/user/me")
async def update_user(request: Request):
    data = await request.json()
    uid = data.get("uid")
    if not uid:
        return JSONResponse(content={"status": "error", "error": "uid required"}, status_code=400)
    user_ref = db.collection("users").document(uid)
    update_fields = {}
    # Solo actualiza los campos que llegan en el body
    # Extendido para mantener el perfil completo consistente con el frontend
    for field in [
        "email",
        "full_name",
        "onboarding_completed",
        "preferred_languages",
        "voice_sample_url",
        "voice_prompt_seen",
        "notification_preferences",
    ]:
        if field in data:
            update_fields[field] = data[field]
    if not update_fields:
        return JSONResponse(content={"status": "error", "error": "No fields to update"}, status_code=400)
    user_ref.set(update_fields, merge=True)
    user_doc = user_ref.get()
    return JSONResponse(content={"status": "success", "user": user_doc.to_dict()})


# File uploads are handled via Firebase Storage from the frontend.