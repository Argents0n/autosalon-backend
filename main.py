from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, cars, clients, deals, refs, reports, service, test_drives

app = FastAPI(
    title="АвтоДилер API",
    description="REST API для информационной системы автосалона",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cars.router)
app.include_router(clients.router)
app.include_router(deals.router)
app.include_router(refs.router)
app.include_router(reports.router)
app.include_router(service.router)
app.include_router(test_drives.router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "АвтоДилер API v1.0"}
