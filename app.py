import streamlit as st
import requests

# Page config
st.set_page_config(page_title="AP Election Dashboard", layout="wide")
st.title("Andhra Pradesh Parishad Elections 2026")

LATEST_URL = "https://d1cbf5vryixueg.cloudfront.net/2026-11-07/latest.json"

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Results")
st.sidebar.markdown("*(Note: To fully activate these filters, you will need to map them to the `districtWise` and `constituency` JSON endpoints found in your network scan)*")

# Placeholder lists - you would populate these dynamically from your regionWise/districtWise JSONs
selected_district = st.sidebar.selectbox("Select District", ["All Districts", "Srikakulam", "Palnadu", "Markapuram", "Visakhapatnam"])
selected_constituency = st.sidebar.selectbox("Select Constituency", ["All Constituencies"])
selected_mandal = st.sidebar.selectbox("Select Mandal", ["All Mandals"])

# --- DATA FETCHING ---
col_title, col_btn = st.columns([4, 1])
with col_btn:
    st.write("") 
    if st.button("🔄 Fetch Latest Data"):
        st.cache_data.clear()

@st.cache_data(ttl=300)
def fetch_live_data():
    try:
        # 1. Ask the server for the newest file paths
        latest_resp = requests.get(LATEST_URL)
        latest_resp.raise_for_status()
        latest_data = latest_resp.json()
        
        # 2. Extract the dynamic URL for the top-level leads
        lead_url = latest_data.get("pointers-by-lead", [{}])[0].get("directory")
        
        # 3. Fetch the actual results
        if lead_url:
            data_resp = requests.get(lead_url)
            data_resp.raise_for_status()
            return data_resp.json()
            
    except Exception as e:
        st.error(f"Error fetching live data: {e}")
        return None

data = fetch_live_data()

# --- DASHBOARD UI ---
if data:
    # Create tabs for Zilla Parishad and Mandal Parishad
    tab1, tab2 = st.tabs(["🏛️ Zilla Parishad (ZPTC)", "🌿 Mandal Parishad (MPTC)"])
    
    # --- ZILLA PARISHAD TAB ---
    with tab1:
        zp_data = data.get("Zilla Parishad", {})
        if zp_data:
            st.subheader("Statewide Zilla Parishad Standings")
            col1, col2 = st.columns(2)
            col1.metric("Total Seats", zp_data.get("total_seats", 0))
            col2.metric("Total Won", zp_data.get("total_won", 0))
            
            st.markdown("---")
            parties = zp_data.get("parties", [])
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
        else:
            st.info("Zilla Parishad data is currently unavailable or still loading.")

    # --- MANDAL PARISHAD TAB ---
    with tab2:
        mp_data = data.get("Mandal Parishad", {})
        if mp_data:
            st.subheader("Statewide Mandal Parishad Standings")
            col1, col2 = st.columns(2)
            col1.metric("Total Seats", mp_data.get("total_seats", 0))
            col2.metric("Total Won", mp_data.get("total_won", 0))
            
            st.markdown("---")
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
        else:
            st.info("Mandal Parishad data is currently unavailable or still loading.")
