@echo off
REM One-click setup + launch for Windows. Double-click or run from Command Prompt inside the project folder.
if not exist venv ( python -m venv venv )
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python generate_data.py
python data_cleaning.py
python build_database.py
python run_queries.py > sql_results\all_results.txt
python test_project.py
streamlit run app.py
