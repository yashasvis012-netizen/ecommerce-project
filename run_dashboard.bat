@echo off
REM Start the dashboard (after run_all.bat has been run once).
call venv\Scripts\activate
streamlit run app.py
