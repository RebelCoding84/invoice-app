@echo off
call .venv\Scripts\activate
python -m streamlit run app.py --server.fileWatcherType poll
pause
