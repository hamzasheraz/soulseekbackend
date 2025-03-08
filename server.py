from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",'https://soulseek.vercel.app'],  # Adjust if different
    allow_methods=["*"],
    allow_headers=["*"],
)

LOG_FILE_PATH = "conversation_log.txt"

@app.get("/api/get-conversation")
async def get_conversation():
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as file:
            return {"conversation": file.read()}
    return {"conversation": ""}
