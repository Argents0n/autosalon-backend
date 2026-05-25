import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

_import_error = None
try:
    from routers import auth, cars, clients, deals, refs, reports, service, test_drives
    _routers_ok = True
except Exception as e:
    _import_error = traceback.format_exc()
    _routers_ok = False

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

if _routers_ok:
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
    if _import_error:
        return JSONResponse({"error": _import_error}, status_code=500)
    return {"status": "ok", "service": "АвтоДилер API v1.0"}
