@echo off
echo === АвтоДилер Backend ===
echo.

if not exist ".env" (
    echo ОШИБКА: Создайте файл .env (скопируйте .env.example)
    pause
    exit /b 1
)

if not exist "venv" (
    echo Создание виртуального окружения...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

echo.
echo Запуск FastAPI на http://localhost:8000
echo Документация: http://localhost:8000/docs
echo.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
