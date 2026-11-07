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
        
        def get_exact_url(key_name):
            pointers = latest_data.get(key_name, [])
            if pointers and isinstance(pointers, list) and len(pointers) > 0:
                return pointers[0].get("directory")
            return None

        urls = {
            "lead": get_exact_url("pointers-by-lead"),
            "districts": get_exact_url("pointers-by-district"), 
            "constituencies": get_exact_url("pointers-by-loksabhaWise"), 
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
    
    # Load the base lists for lookups later
    district_list_mp = data.get("districts", {}).get("Mandal Parishad", [])
    constituency_list_mp = data.get("constituencies", {}).get("Mandal Parishad", [])
    mandal_list_mp = data.get("mandals", {}).get("Mandal Parishad", [])
    
    district_list_zp = data.get("districts", {}).get("Zilla Parishad", [])
    constituency_list_zp = data.get("constituencies", {}).get("Zilla Parishad", [])
    mandal_list_zp = data.get("mandals", {}).get("Zilla Parishad", [])
    
    # --- CASCADING FILTER LOGIC ---
    # We use the detailed candidates table to map what regions belong to each other
    raw_cands = data.get("candidates", {}).get("Mandal Parishad", {})
    cand_array = raw_cands.get("Results", []) if isinstance(raw_cands, dict) else raw_cands
    df_map = pd.DataFrame(cand_array)
    
    dist_col = "district_in_english" if "district_in_english" in df_map.columns else None
    const_col = "constituency_in_english" if "constituency_in_english" in df_map.columns else ("loksabha_in_english" if "loksabha_in_english" in df_map.columns else None)
    mand_col = "name_in_english" if "name_in_english" in df_map.columns else None

    # 1. District Filter
    all_dists = sorted(df_map[dist_col].dropna().unique().tolist()) if dist_col else sorted(list(set(d.get("name_in_english") for d in district_list_mp if d.get("name_in_english"))))
    selected_district = st.sidebar.selectbox("Select District", ["All Districts"] + all_dists)
    
    # 2. Constituency Filter (Automatically updates based on District)
    df_filtered = df_map.copy()
    if selected_district != "All Districts" and dist_col:
        df_filtered = df_filtered[df_filtered[dist_col] == selected_district]
        
    all_consts = sorted(df_filtered[const_col].dropna().unique().tolist()) if const_col else []
    selected_constituency = st.sidebar.selectbox("Select Constituency", ["All Constituencies"] + all_consts)
    
    # 3. Mandal Filter (Automatically updates based on Constituency)
    if selected_constituency != "All Constituencies" and const_col:
        df_filtered = df_filtered[df_filtered[const_col] == selected_constituency]
        
    all_mandals = sorted(df_filtered[mand_col].dropna().unique().tolist()) if mand_col else []
    selected_mandal = st.sidebar.selectbox("Select Mandal", ["All Mandals"] + all_mandals)

    # --- FILTERING SUMMARY NUMBERS ---
    display_data_mp = {}
    display_data_zp = {}
    display_title = "Statewide Standings"
    
    # Helper to fix capitalization issues (e.g. "ADDANKI" vs "Addanki")
    def find_match(dataset_list, target_name):
        if not target_name: return {}
        target = str(target_name).strip().lower()
        return next((item for item in dataset_list if str(item.get("name_in_english", "")).strip().lower() == target), {})

    if selected_mandal != "All Mandals":
        display_data_mp = find_match(mandal_list_mp, selected_mandal)
        display_data_zp = find_match(mandal_list_zp, selected_mandal)
        display_title = f"{selected_mandal} Mandal Standings"
        
    elif selected_constituency != "All Constituencies":
        display_data_mp = find_match(constituency_list_mp, selected_constituency)
        display_data_zp = find_match(constituency_list_zp, selected_constituency)
        display_title = f"{selected_constituency} Constituency Standings"
        
    elif selected_district != "All Districts":
        display_data_mp = find_match(district_list_mp, selected_district)
        display_data_zp = find_match(district_list_zp, selected_district)
        display_title = f"{selected_district} District Standings"
        
    else:
        display_data_mp = data.get("lead", {}).get("Mandal Parishad", {})
        display_data_zp = data.get("lead", {}).get("Zilla Parishad", {})

    # --- DASHBOARD UI ---
    tab1, tab2 = st.tabs(["🏛️ Zilla Parishad (ZPTC)", "🌿 Mandal Parishad (MPTC)"])
    
    def render_results(dataset, list_data_source, title, level_key):
        if not dataset:
            # Displays a soft warning instead of completely failing if ETV hasn't published the top-level numbers for this exact region yet
            st.warning(f"Aggregate number data unavailable for '{title}'. (The detailed candidate list below may still have records).")
        else:
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
                    
        st.markdown("---")
        st.subheader("Detailed Candidate List")
        
        raw_results = data.get("candidates", {}).get(level_key, {})
        candidate_list = raw_results.get("Results", []) if isinstance(raw_results, dict) else raw_results
        
        if candidate_list:
            df = pd.DataFrame(candidate_list)
            
            # Case-insensitive table filtering
            if selected_mandal != "All Mandals":
                if "name_in_english" in df.columns:
                    df = df[df["name_in_english"].str.lower() == selected_mandal.lower()]
            elif selected_constituency != "All Constituencies":
                if "constituency_in_english" in df.columns:
                    df = df[df["constituency_in_english"].str.lower() == selected_constituency.lower()]
                elif "loksabha_in_english" in df.columns:
                    df = df[df["loksabha_in_english"].str.lower() == selected_constituency.lower()]
            elif selected_district != "All Districts":
                if "district_in_english" in df.columns:
                    df = df[df["district_in_english"].str.lower() == selected_district.lower()]
            
            cols_to_keep = {}
            if "district_in_english" in df.columns: cols_to_keep["district_in_english"] = "District"
            if "constituency_in_english" in df.columns: cols_to_keep["constituency_in_english"] = "Constituency"
            if "loksabha_in_english" in df.columns: cols_to_keep["loksabha_in_english"] = "Constituency"
            if "name_in_english" in df.columns: cols_to_keep["name_in_english"] = "Region/Mandal"
            if "candidate_in_english" in df.columns: cols_to_keep["candidate_in_english"] = "Candidate Name"
            if "party_in_english" in df.columns: cols_to_keep["party_in_english"] = "Party"
            if "status" in df.columns: cols_to_keep["status"] = "Status"
            
            if not df.empty:
                st.dataframe(df.rename(columns=cols_to_keep)[list(cols_to_keep.values())], use_container_width=True, hide_index=True)
            else:
                st.info("No candidates found for this specific filter.")
        else:
            st.info("Detailed candidate list is currently loading or unavailable.")

    with tab1:
        render_results(display_data_zp, data.get("candidates", {}), f"Zilla Parishad: {display_title}", "Zilla Parishad")

    with tab2:
        render_results(display_data_mp, data.get("candidates", {}), f"Mandal Parishad: {display_title}", "Mandal Parishad")

else:
    st.info("Loading data from ETV servers...")
