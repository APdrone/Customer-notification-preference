"""Application entry point: uvicorn app.server:app"""
from fastapi import FastAPI

from app.api.forms_controller import router as forms_router

app = FastAPI(title="Customer Notification Service")
app.include_router(forms_router)
