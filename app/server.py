"""Application entry point: uvicorn app.server:app"""
from fastapi import FastAPI

from app.api.audit_controller import router as audit_router
from app.api.forms_controller import router as forms_router
from app.security.problem import ProblemDetailException, problem_detail_exception_handler

app = FastAPI(title="Customer Notification Service")
app.add_exception_handler(ProblemDetailException, problem_detail_exception_handler)
app.include_router(forms_router)
app.include_router(audit_router)
