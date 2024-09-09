import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from load_generator.routes import router as load_generator_router
from analytics.routes import router as analytics_router

app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app.include_router(load_generator_router)
app.include_router(analytics_router)

app.mount("/static", StaticFiles(directory="load_generator/static"), name="static")

