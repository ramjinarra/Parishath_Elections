import streamlit as st
import requests

# --- PAGE CONFIG ---
st.set_page_config(page_title="AP Election Dashboard", layout="wide")
st.title("Andhra Pradesh Parishad Elections 2026")

LATEST_URL = "https://d1cbf5vryixueg.cloudfront.net/2026-11-07/latest.json"

# --- DATA FETCHING ---
col_title, col_btn = st.columns([4, 1])
with col_btn:
    st.write("") 
    if st.button("🔄 Fetch Latest Data"):
        st.cache_data.clear() # Clears the cache to force a fresh pull

@st.cache_data(ttl=300)
def fetch_all_data():
    try:
        # 1. Ask the server for the newest file paths
        latest_resp = requests.get(LATEST_URL)
        latest_resp.raise_for_status()
        latest_data = latest_resp.json()
        
        # 2. Smart URL extractor: searches for keywords in the keys
        def get_url(keyword):
            for key, value in latest_data.items():
                if keyword.lower() in key.lower() and isinstance(value, list) and len(value) > 0:
                    return value[0].get("directory")
            return None

        # Dynamically find the paths by keyword rather than hardcoded keys
        urls = {
            "lead": get_url("lead"),
            "districts": get_url("regionwise"), # ETV stores District data here
            "mandals": get_url("districtwise")  # ETV stores Mandal data here
        }
        
        # 3. Fetch the actual JSONs
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
    # --- DEBUG HELPER (You can delete this block later once it's working) ---
    with st.expander("🛠️ API Debug Info (Click to expand)"):
        st.write("Keys found in latest.json:", data.get("latest_keys"))
        st.write("Target URLs matched:", data.get("urls_found"))
    
    # Safely extract the lists of districts and mandals for both ZP and MP
    district_list_mp = data.get("districts", {}).get("Mandal Parishad", [])
    mandal_list_mp = data.get("mandals", {}).get("Mandal Parishad", [])
    
    district_list_zp = data.get("districts", {}).get("Zilla Parishad", [])
    mandal_list_zp = data.get("mandals", {}).get("Zilla Parishad", [])
    
    # Create lists of names for the dropdowns
    district_names = ["All Districts"] + [d.get("name_in_english") for d in district_list_mp if d.get("name_in_english")]
    mandal_names = ["All Mandals"] + [m.get("name_in_english") for m in mandal_list_mp if m.get("name_in_english")]

    # Render the selectboxes
    selected_district = st.sidebar.selectbox("Select District", district_names)
    selected_mandal = st.sidebar.selectbox("Select Mandal", mandal_names)

    # --- FILTERING LOGIC ---
    display_data_mp = {}
    display_data_zp = {}
    display_title = "Statewide Standings"

    # Waterfall logic: Check Mandal first, then District, then default to Statewide
    if selected_mandal != "All Mandals":
        display_data_mp = next((m for m in mandal_list_mp if m.get("name_in_english") == selected_mandal), {})
        display_data_zp = next((z for z in mandal_list_zp if z.get("name_in_english") == selected_mandal), {})
        display_title = f"{selected_mandal} Standings"
        
    elif selected_district != "All Districts":
        display_data_mp = next((d for d in district_list_mp if d.get("name_in_english") == selected_district), {})
        display_data_zp = next((z for z in district_list_zp if z.get("name_in_english") == selected_district), {})
        display_title = f"{selected_district} District Standings"
        
    else:
        display_data_mp = data.get("lead", {}).get("Mandal Parishad", {})
        display_data_zp = data.get("lead", {}).get("Zilla Parishad", {})

    # --- DASHBOARD UI ---
    tab1, tab2 = st.tabs(["🏛️ Zilla Parishad (ZPTC)", "🌿 Mandal Parishad (MPTC)"])
    
    # Helper function to render a results grid so we don't repeat code
    def render_results(dataset, title):
        if not dataset:
            st.info("Data unavailable for this specific selection.")
            return
            
        st.subheader(title)
        col1, col2 = st.columns(2)
        col1.metric("Total Seats", dataset.get("total_seats", "N/A"))
        
        # Depending on the level (state vs local), the 'won' key might vary slightly
        total_won = dataset.get("total_won") or sum([p.get("win", 0) for p in dataset.get("parties", [])])
        col2.metric("Total Won", total_won)
        
        st.markdown("---")
        parties = dataset.get("parties", [])
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
            st.info("No party data available at this level.")

    # Render the tabs
    with tab1:
        render_results(display_data_zp, f"Zilla Parishad: {display_title}")

    with tab2:
        render_results(display_data_mp, f"Mandal Parishad: {display_title}")

else:
    st.info("Loading data from ETV servers...")
