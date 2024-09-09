from fastapi import APIRouter, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from .services import LoadGeneratorService


router = APIRouter()
templates = Jinja2Templates(directory="load_generator/templates")
service = LoadGeneratorService()


@router.get("/")
async def read_root(request: Request):
    if not service.test_status.get_status():
        return templates.TemplateResponse("index.html", {"request": request})
    return templates.TemplateResponse("index.html", {"request": request, "message": "Тест уже идет!", "test_running": True})


@router.post("/start-test")
async def start_test(
    request: Request,
    background_tasks: BackgroundTasks,
    users: int = Form(...),
    transactions_per_second: int = Form(...)
):
    if not service.test_status.get_status():  # Проверяем, запущен ли тест
        service.test_status.set_status(True)  # Устанавливаем статус теста в True
        background_tasks.add_task(service.generate_load, users, transactions_per_second)
        return templates.TemplateResponse("index.html", {"request": request, "message": "Тест начался!", "test_running": True})
    return templates.TemplateResponse("index.html", {"request": request, "message": "Тест уже идет!", "test_running": True})


@router.post("/stop-test")
async def stop_test(
    request: Request,
    background_tasks: BackgroundTasks
):
    if service.test_status.get_status():
        background_tasks.add_task(service.stop)
        return templates.TemplateResponse("index.html", {"request": request, "message": "Тест остановлен.", "test_running": False})
    return templates.TemplateResponse("index.html", {"request": request, "message": "Тест не запущен.", "test_running": False})