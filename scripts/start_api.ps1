Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

$root = "C:\Projektit\invoice-app"
Set-Location $root

.\.venv\Scripts\Activate.ps1

uvicorn server.main:app --host 127.0.0.1 --port 8000
