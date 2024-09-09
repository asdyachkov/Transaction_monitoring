from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse, JSONResponse

from .services import AnalyticsService

router = APIRouter()
templates = Jinja2Templates(directory="analytics/templates")

service = AnalyticsService()

@router.get("/analytics", response_class=HTMLResponse)
async def get_analytics_page(request: Request):
    return templates.TemplateResponse("analytics.html", {"request": request})

@router.get("/analytics/data", response_class=JSONResponse)
async def get_analytics_data():
    analytics_data = service.get_analytics_data()
    return analytics_data
