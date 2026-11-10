import streamlit as st
import subprocess
import streamlit.components.v1 as components
import os
import sys

st.set_page_config(page_title="League Data", layout="wide")
st.title("League Data Generator")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

league_id = st.text_input("Enter League ID:")

# Expanded to 3 columns
col1, col2, col3 = st.columns(3)
run_script1 = col1.button("Get Top 20 Scores")
run_script2 = col2.button("Run Trade Analyzer")
run_script3 = col3.button("Run All-Play Matrix")

if run_script1:
    if league_id:
        with st.spinner('Running API Script...'):
            script_path = os.path.join(BASE_DIR, 'sleeper_api_script.py')
            html_path = os.path.join(BASE_DIR, 'top_20_scores.html')
            
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

# Output for Script 3
if run_script3:
    if league_id:
        with st.spinner('Running All-Play Matrix...'):
            script_path = os.path.join(BASE_DIR, 'all_play.py')
            html_path = os.path.join(BASE_DIR, 'advanced_records.html')
            
            result = subprocess.run([sys.executable, script_path, league_id], cwd=BASE_DIR, capture_output=True, text=True)
            
            if os.path.exists(html_path):
                with open(html_path, "r", encoding='utf-8') as f:
                    components.html(f.read(), height=900, scrolling=True)
            else:
                st.error(f"Failed to generate. Python Error: {result.stderr}")
    else:
        st.warning("Please enter a League ID first.")