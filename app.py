import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh

# Page config must be the first Streamlit command
st.set_page_config(page_title="AP Election Dashboard", layout="wide")

# Automatically refresh the browser every 5 minutes (300,000 milliseconds)
st_autorefresh(interval=300000, key="data_refresh")

st.title("Andhra Pradesh Parishad Elections 2026")

# Using the 'latest.json' endpoint ensures the dashboard always finds the newest data URL
LATEST_URL = "https://d1cbf5vryixueg.cloudfront.net/2026-11-07/latest.json"

# Cache data for 4.5 minutes so it strictly pulls new data upon the 5-minute refresh
@st.cache_data(ttl=270)
def fetch_live_data():
    try:
        # 1. Ask the server what the newest data file is
        latest_resp = requests.get(LATEST_URL)
        latest_resp.raise_for_status()
        latest_data = latest_resp.json()
        
        # 2. Extract the dynamic URL for the leads
        lead_url = latest_data["pointers-by-lead"][0]["directory"]
        
        # 3. Fetch the actual results from that dynamic URL
        data_resp = requests.get(lead_url)
        data_resp.raise_for_status()
        return data_resp.json()
        
    except Exception as e:
        st.error(f"Error fetching live data: {e}")
        return None

data = fetch_live_data()

if data:
    st.subheader("Mandal Parishad Results")
    mp_data = data.get("Mandal Parishad", {})
    
    # Display top-level metrics
    col1, col2 = st.columns(2)
    col1.metric("Total Seats", mp_data.get("total_seats", 0))
    col2.metric("Total Won", mp_data.get("total_won", 0))
    
    st.markdown("---")
    
    # Display party results dynamically
    parties = mp_data.get("parties", [])
    if parties:
        cols = st.columns(len(parties))
        for i, party in enumerate(parties):
            with cols[i]:
                name = party.get("party_name_in_english", "Unknown")
                won = party.get("win", 0)
                lead = party.get("lead", 0)
                
                st.markdown(f"### {name}")
                st.metric("Won", won)
                st.metric("Leading", lead)
