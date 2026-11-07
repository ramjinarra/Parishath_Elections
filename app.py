import streamlit as st
import requests

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
        # 1. Ask the server for the newest file paths
        latest_resp = requests.get(LATEST_URL)
        latest_resp.raise_for_status()
        latest_data = latest_resp.json()
        
        # Helper to safely extract URLs from the latest.json dictionary
        def get_url(key):
            pointers = latest_data.get(key, [])
            return pointers[0].get("directory") if pointers else None

        # 2. Extract the dynamic URLs for leads, districts, and mandals
        urls = {
            "lead": get_url("pointers-by-lead"),
            "districts": get_url("pointers-by-regionWise"), # ETV stores Districts here
            "mandals": get_url("pointers-by-districtWise")  # ETV stores Mandals here
        }
        
        # 3. Fetch the actual JSONs
        datasets = {}
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
    # Safely extract the lists of districts and mandals from the fetched JSON
    # We default to empty lists if the keys aren't found
    district_list = data["districts"].get("Mandal Parishad", [])
    mandal_list = data["mandals"].get("Mandal Parishad", [])
    
    # Create lists of names for the dropdowns
    district_names = ["All Districts"] + [d.get("name_in_english") for d in district_list if d.get("name_in_english")]
    mandal_names = ["All Mandals"] + [m.get("name_in_english") for m in mandal_list if m.get("name_in_english")]

    # Render the selectboxes
    selected_district = st.sidebar.selectbox("Select District", district_names)
    selected_mandal = st.sidebar.selectbox("Select Mandal", mandal_names)

    # --- FILTERING LOGIC ---
    # Determine which dataset to show based on the user's selection
    display_data_mp = {}
    display_data_zp = {}
    display_title = "Statewide Standings"

    if selected_mandal != "All Mandals":
        # Find the specific mandal in the list
        mandal_record = next((m for m in mandal_list if m.get("name_in_english") == selected_mandal), {})
        display_data_mp = mandal_record
        display_data_zp = next((z for z in data["mandals"].get("Zilla Parishad", []) if z.get("name_in_english") == selected_mandal), {})
        display_title = f"{selected_mandal} Standings"
        
    elif selected_district != "All Districts":
        # Find the specific district in the list
        district_record = next((d for d in district_list if d.get("name_in_english") == selected_district), {})
        display_data_mp = district_record
        display_data_zp = next((z for z in data["districts"].get("Zilla Parishad", []) if z.get("name_in_english") == selected_district), {})
        display_title = f"{selected_district} District Standings"
        
    else:
        # Default to top-level leads
        display_data_mp = data["lead"].get("Mandal Parishad", {})
        display_data_zp = data["lead"].get("Zilla Parishad", {})

    # --- DASHBOARD UI ---
    tab1, tab2 = st.tabs(["🏛️ Zilla Parishad (ZPTC)", "🌿 Mandal Parishad (MPTC)"])
    
    # Helper function to render a results grid so we don't repeat code
    def render_results(dataset, title):
        if not dataset:
            st.info("Data unavailable for this selection.")
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

    with tab1:
        render_results(display_data_zp, f"Zilla Parishad: {display_title}")

    with tab2:
        render_results(display_data_mp, f"Mandal Parishad: {display_title}")

else:
    st.info("Loading data...")
