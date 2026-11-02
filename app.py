import streamlit as st
import subprocess
import streamlit.components.v1 as components
import os
import sys

st.set_page_config(page_title="League Data", layout="wide")
st.title("League Data Generator")

# Lock all file operations to the exact folder where app.py is saved
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

league_id = st.text_input("Enter League ID:")
col1, col2 = st.columns(2)
run_script1 = col1.button("Get Top 20 Scores")
run_script2 = col2.button("Run Trade Analyzer")

if run_script1:
    if league_id:
        with st.spinner('Running API Script...'):
            script_path = os.path.join(BASE_DIR, 'sleeper_api_script.py')
            html_path = os.path.join(BASE_DIR, 'top_20_scores.html')
            
            # sys.executable ensures it uses the exact same Python environment
            result = subprocess.run([sys.executable, script_path, league_id], cwd=BASE_DIR, capture_output=True, text=True)
            
            if os.path.exists(html_path):
                with open(html_path, "r", encoding='utf-8') as f:
                    components.html(f.read(), height=900, scrolling=True)
            else:
                st.error(f"Failed to generate. Python Error: {result.stderr}")
    else:
        st.warning("Please enter a League ID first.")

if run_script2:
    if league_id:
        with st.spinner('Running Trade Analyzer...'):
            script_path = os.path.join(BASE_DIR, 'sleeper_nfl_trade_analyzer.py')
            html_path = os.path.join(BASE_DIR, 'all_time_trade_counts.html')
            
            result = subprocess.run([sys.executable, script_path, league_id], cwd=BASE_DIR, capture_output=True, text=True)
            
            if os.path.exists(html_path):
                with open(html_path, "r", encoding='utf-8') as f:
                    components.html(f.read(), height=900, scrolling=True)
            else:
                st.error(f"Failed to generate. Python Error: {result.stderr}")
    else:
        st.warning("Please enter a League ID first.")