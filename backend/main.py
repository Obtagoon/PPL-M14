from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from database import init_db
from routers.employees import router as employees_router
from routers.salary_calculation import router as salary_calculation_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize and seed SQLite database
    init_db()
    yield

app = FastAPI(
    title="PPL-M14 Backend API (Python FastAPI)",
    description="API Pengelolaan Komponen Gaji Karyawan (AC1: Dasar Perhitungan Gaji, AC4: Itemized Tunjangan & Potongan)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Exception Handler to match frontend error contract
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        body = exc.detail
        if "message" not in body and "detail" in body:
            body["message"] = str(body["detail"])
        return JSONResponse(status_code=exc.status_code, content=body)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc.detail)}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_msg = errors[0]["msg"] if errors else "Validasi data gagal"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": f"Data tidak valid: {first_msg}",
            "errors": errors
        }
    )

@app.get("/", tags=["Health Check"])
@app.get("/api", tags=["Health Check"])
@app.get("/api/health", tags=["Health Check"])
def health_check():
    return {
        "status": "ok",
        "message": "PPL-M14 Backend API running with Python FastAPI",
        "version": "1.0.0",
        "features": [
            "AC1: Dasar Perhitungan Gaji",
            "AC4: Itemized Tunjangan & Potongan"
        ]
    }

# Include routers
app.include_router(employees_router)          # US1: Komponen Gaji
app.include_router(salary_calculation_router) # US2: Perhitungan Gaji Berdasarkan Kehadiran

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
