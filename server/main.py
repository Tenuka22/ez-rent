from fastapi import FastAPI

from server.api import cache, predictions, properties

app = FastAPI(
    title="Ez-Rent Price Predictor",
    description="API for scraping rental data and predicting prices.",
    version="1.0.0",
)


app.include_router(predictions.router, tags=["Predictions"])
app.include_router(properties.router, tags=["Properties"])
app.include_router(cache.router, tags=["Scrapes"])
