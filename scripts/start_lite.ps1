Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

$root = "C:\Projektit\invoice-app"
Set-Location $root

.\.venv\Scripts\Activate.ps1

python -m streamlit run app.py --server.port 8501 --server.fileWatcherType poll
