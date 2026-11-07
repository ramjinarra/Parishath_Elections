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
        
        # Aggressive URL matcher
        def get_url(keyword):
            for key, value in latest_data.items():
                # ETV sometimes uses hyphens, camelCase, or completely lowercase
                if keyword.lower() in key.lower().replace("-", "") and isinstance(value, list) and len(value) > 0:
                    return value[0].get("directory")
            return None

        # Grab all the different layers of data
        urls = {
            "lead": get_url("lead"),
            "districts": get_url("regionwise"), 
            "mandals": get_url("districtwise"), 
            "candidates": get_url("constituency") # <-- New: Grabs the actual list of winners/leads
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
    
    # Extract dropdown lists safely
    district_list_mp = data.get("districts", {}).get("Mandal Parishad", [])
    mandal_list_mp = data.get("mandals", {}).get("Mandal Parishad", [])
    
    district_names = ["All Districts"] + sorted(list(set(d.get("name_in_english") for d in district_list_mp if d.get("name_in_english"))))
    mandal_names = ["All Mandals"] + sorted(list(set(m.get("name_in_english") for m in mandal_list_mp if m.get("name_in_english"))))

    selected_district = st.sidebar.selectbox("Select District", district_names)
    selected_mandal = st.sidebar.selectbox("Select Mandal", mandal_names)

    # --- FILTERING SUMMARY NUMBERS ---
    display_data_mp = {}
    display_data_zp = {}
    display_title = "Statewide Standings"

    if selected_mandal != "All Mandals":
        display_data_mp = next((m for m in mandal_list_mp if m.get("name_in_english") == selected_mandal), {})
        display_data_zp = next((z for z in data.get("mandals", {}).get("Zilla Parishad", []) if z.get("name_in_english") == selected_mandal), {})
        display_title = f"{selected_mandal} Standings"
    elif selected_district != "All Districts":
        display_data_mp = next((d for d in district_list_mp if d.get("name_in_english") == selected_district), {})
        display_data_zp = next((z for z in data.get("districts", {}).get("Zilla Parishad", []) if z.get("name_in_english") == selected_district), {})
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
            
        # 1. Show the numbers
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
                    
        # 2. Show the detailed list (Candidates)
        st.markdown("---")
        st.subheader("Detailed Candidate List")
        
        # Safely extract the Results array for this specific tier (ZPTC or MPTC)
        raw_results = data.get("candidates", {}).get(level_key, {})
        candidate_list = raw_results.get("Results", []) if isinstance(raw_results, dict) else raw_results
        
        if candidate_list:
            # Convert JSON to a Pandas DataFrame for a nice, sortable table
            df = pd.DataFrame(candidate_list)
            
            # Filter the table based on sidebar selections
            if selected_district != "All Districts" and "district_in_english" in df.columns:
                df = df[df["district_in_english"].str.contains(selected_district, case=False, na=False)]
            
            # Only keep the columns we care about, rename them to look nice
            cols_to_keep = {}
            if "name_in_english" in df.columns: cols_to_keep["name_in_english"] = "Constituency/Region"
            if "candidate_in_english" in df.columns: cols_to_keep["candidate_in_english"] = "Candidate Name"
            if "party_in_english" in df.columns: cols_to_keep["party_in_english"] = "Party"
            if "status" in df.columns: cols_to_keep["status"] = "Status"
            
            # Display the interactive table
            if not df.empty:
                st.dataframe(df.rename(columns=cols_to_keep)[list(cols_to_keep.values())], use_container_width=True)
            else:
                st.info("No candidates found for this specific filter.")
        else:
            st.info("Detailed candidate list is currently loading or unavailable.")

    # Render the tabs
    with tab1:
        render_results(display_data_zp, data.get("candidates", {}), f"Zilla Parishad: {display_title}", "Zilla Parishad")

    with tab2:
        render_results(display_data_mp, data.get("candidates", {}), f"Mandal Parishad: {display_title}", "Mandal Parishad")

else:
    st.info("Loading data from ETV servers...")
