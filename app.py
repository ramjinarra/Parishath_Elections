import streamlit as st
import requests
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="AP Election Dashboard", layout="wide")
st.title("Andhra Pradesh Parishad Elections 2026")

LATEST_URL = "https://d1cbf5vryixueg.cloudfront.net/2026-11-07/latest.json"

# --- DATA FETCHING ---
col_title, col_btn = st.columns([4, 1])
with col_btn:
    st.write("") 
    if st.button("🔄 Fetch Latest Data"):
        st.cache_data.clear()

@st.cache_data(ttl=300)
def fetch_all_data():
    try:
        latest_resp = requests.get(LATEST_URL)
        latest_resp.raise_for_status()
        latest_data = latest_resp.json()
        
        # Safely extract the exact URL paths
        def get_exact_url(key_name):
            pointers = latest_data.get(key_name, [])
            if pointers and isinstance(pointers, list) and len(pointers) > 0:
                return pointers[0].get("directory")
            return None

        # Grab all the different layers of data
        urls = {
            "lead": get_exact_url("pointers-by-lead"),
            "districts": get_exact_url("pointers-by-district"), 
            "constituencies": get_exact_url("pointers-by-loksabhaWise"), # <-- Added Constituency file
            "mandals": get_exact_url("pointers-by-mandal"), 
            "candidates": get_exact_url("pointers-by-mptc_zptc") 
        }
        
        datasets = {"latest_keys": list(latest_data.keys()), "urls_found": urls}
        for key, url in urls.items():
            if url:
                resp = requests.get(url)
                resp.raise_for_status()
                datasets[key] = resp.json()
            else:
                datasets[key] = {}
                
        return datasets
            
    except Exception as e:
        st.error(f"Error fetching live data: {e}")
        return None

data = fetch_all_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Results")

if data:
    with st.expander("🛠️ API Debug Info (Check this if filters are empty)"):
        st.write("Keys found in latest.json:", data.get("latest_keys"))
        st.write("URLs matched:", data.get("urls_found"))
    
    # Extract dropdown lists safely for Mandal Parishad (used for dropdown names)
    district_list_mp = data.get("districts", {}).get("Mandal Parishad", [])
    constituency_list_mp = data.get("constituencies", {}).get("Mandal Parishad", [])
    mandal_list_mp = data.get("mandals", {}).get("Mandal Parishad", [])
    
    # Extract lists for Zilla Parishad (used later for filtering numbers)
    district_list_zp = data.get("districts", {}).get("Zilla Parishad", [])
    constituency_list_zp = data.get("constituencies", {}).get("Zilla Parishad", [])
    mandal_list_zp = data.get("mandals", {}).get("Zilla Parishad", [])
    
    # Sort and remove duplicates for the dropdown UI
    district_names = ["All Districts"] + sorted(list(set(d.get("name_in_english") for d in district_list_mp if d.get("name_in_english"))))
    constituency_names = ["All Constituencies"] + sorted(list(set(c.get("name_in_english") for c in constituency_list_mp if c.get("name_in_english"))))
    mandal_names = ["All Mandals"] + sorted(list(set(m.get("name_in_english") for m in mandal_list_mp if m.get("name_in_english"))))

    # Render the selectboxes in order of size
    selected_district = st.sidebar.selectbox("Select District", district_names)
    selected_constituency = st.sidebar.selectbox("Select Constituency", constituency_names)
    selected_mandal = st.sidebar.selectbox("Select Mandal", mandal_names)

    # --- FILTERING SUMMARY NUMBERS ---
    display_data_mp = {}
    display_data_zp = {}
    display_title = "Statewide Standings"

    # Waterfall Logic: Check smallest region first (Mandal -> Constituency -> District -> Statewide)
    if selected_mandal != "All Mandals":
        display_data_mp = next((m for m in mandal_list_mp if m.get("name_in_english") == selected_mandal), {})
        display_data_zp = next((z for z in mandal_list_zp if z.get("name_in_english") == selected_mandal), {})
        display_title = f"{selected_mandal} Mandal Standings"
        
    elif selected_constituency != "All Constituencies":
        display_data_mp = next((c for c in constituency_list_mp if c.get("name_in_english") == selected_constituency), {})
        display_data_zp = next((z for z in constituency_list_zp if z.get("name_in_english") == selected_constituency), {})
        display_title = f"{selected_constituency} Constituency Standings"
        
    elif selected_district != "All Districts":
        display_data_mp = next((d for d in district_list_mp if d.get("name_in_english") == selected_district), {})
        display_data_zp = next((z for z in district_list_zp if z.get("name_in_english") == selected_district), {})
        display_title = f"{selected_district} District Standings"
        
    else:
        display_data_mp = data.get("lead", {}).get("Mandal Parishad", {})
        display_data_zp = data.get("lead", {}).get("Zilla Parishad", {})

    # --- DASHBOARD UI ---
    tab1, tab2 = st.tabs(["🏛️ Zilla Parishad (ZPTC)", "🌿 Mandal Parishad (MPTC)"])
    
    # Helper to render the numbers AND the table
    def render_results(dataset, list_data_source, title, level_key):
        if not dataset:
            st.info("Aggregate data unavailable for this selection.")
            return
            
        # 1. Show the top-level numbers
        st.subheader(title)
        col1, col2 = st.columns(2)
        col1.metric("Total Seats", dataset.get("total_seats", "N/A"))
        total_won = dataset.get("total_won") or sum([p.get("win", 0) for p in dataset.get("parties", [])])
        col2.metric("Total Won", total_won)
        
        st.markdown("---")
        parties = dataset.get("parties", [])
        if parties:
            cols = st.columns(max(len(parties), 1))
            for i, party in enumerate(parties):
                with cols[i]:
                    st.markdown(f"### {party.get('party_name_in_english', 'Unknown')}")
                    st.metric("Won", party.get("win", 0))
                    st.metric("Leading", party.get("lead", 0))
                    
        # 2. Show the detailed candidate table
        st.markdown("---")
        st.subheader("Detailed Candidate List")
        
        raw_results = data.get("candidates", {}).get(level_key, {})
