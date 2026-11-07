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

if data:
    with st.expander("🛠️ API Debug Info"):
        st.write("Keys found in latest.json:", data.get("latest_keys"))
        st.write("URLs matched:", data.get("urls_found"))
        
    # --- DASHBOARD UI ---
    tab1, tab2 = st.tabs(["🏛️ Zilla Parishad (ZPTC)", "🌿 Mandal Parishad (MPTC)"])
    
    # Reusable function to render filters, numbers, and tables for a specific tab
    def render_tab_content(level_name):
        # 1. Base data extraction for this specific level
        raw_cands = data.get("candidates", {}).get(level_name, {})
        cand_array = raw_cands.get("Results", []) if isinstance(raw_cands, dict) else raw_cands
        df_map = pd.DataFrame(cand_array)
        
        # Identify ETV's dynamic column names
        dist_col = "district_in_english" if "district_in_english" in df_map.columns else None
        const_col = "constituency_in_english" if "constituency_in_english" in df_map.columns else ("loksabha_in_english" if "loksabha_in_english" in df_map.columns else None)
        mand_col = "name_in_english" if "name_in_english" in df_map.columns else None

        # 2. Render Inline Filters (Cascading)
        st.markdown(f"#### Filter {level_name} Results")
        f_col1, f_col2, f_col3 = st.columns(3)
        
        all_dists = sorted(df_map[dist_col].dropna().unique().tolist()) if dist_col else []
        with f_col1:
            # Using key= allows us to use identical dropdown names in both tabs without Streamlit throwing an error
            selected_dist = st.selectbox("Select District", ["All Districts"] + all_dists, key=f"dist_{level_name}")
            
        df_filtered = df_map.copy()
        if selected_dist != "All Districts" and dist_col:
            df_filtered = df_filtered[df_filtered[dist_col] == selected_dist]
            
        all_consts = sorted(df_filtered[const_col].dropna().unique().tolist()) if const_col else []
        with f_col2:
            selected_const = st.selectbox("Select Constituency", ["All Constituencies"] + all_consts, key=f"const_{level_name}")
            
        if selected_const != "All Constituencies" and const_col:
            df_filtered = df_filtered[df_filtered[const_col] == selected_const]
            
        all_mandals = sorted(df_filtered[mand_col].dropna().unique().tolist()) if mand_col else []
        with f_col3:
            selected_mand = st.selectbox("Select Mandal", ["All Mandals"] + all_mandals, key=f"mand_{level_name}")

        st.markdown("---")

        # 3. Determine Summary Numbers to Display
        def find_match(dataset_list, target_name):
            if not target_name: return {}
            target = str(target_name).strip().lower()
            return next((item for item in dataset_list if str(item.get("name_in_english", "")).strip().lower() == target), {})

        display_data = {}
        display_title = f"Statewide Standings"
        
        if selected_mand != "All Mandals":
            display_data = find_match(data.get("mandals", {}).get(level_name, []), selected_mand)
            display_title = f"{selected_mand} Mandal Standings"
        elif selected_const != "All Constituencies":
            display_data = find_match(data.get("constituencies", {}).get(level_name, []), selected_const)
            display_title = f"{selected_const} Constituency Standings"
        elif selected_dist != "All Districts":
            display_data = find_match(data.get("districts", {}).get(level_name, []), selected_dist)
            display_title = f"{selected_dist} District Standings"
        else:
            display_data = data.get("lead", {}).get(level_name, {})

        # 4. Render Summary Numbers
        if not display_data:
            st.warning(f"Aggregate number data unavailable for '{display_title}'. (The detailed candidate list below may still have records).")
        else:
            st.subheader(display_title)
            m_col1, m_col2 = st.columns(2)
            m_col1.metric("Total Seats", display_data.get("total_seats", "N/A"))
            total_won = display_data.get("total_won") or sum([p.get("win", 0) for p in display_data.get("parties", [])])
            m_col2.metric("Total Won", total_won)
            
            st.markdown("---")
            parties = display_data.get("parties", [])
            if parties:
                p_cols = st.columns(max(len(parties), 1))
                for i, party in enumerate(parties):
                    with p_cols[i]:
                        st.markdown(f"### {party.get('party_name_in_english', 'Unknown')}")
                        st.metric("Won", party.get("win", 0))
                        st.metric("Leading", party.get("lead", 0))
                    
        # 5. Render Detailed Candidate Table
        st.markdown("---")
        st.subheader(f"Detailed Candidate List: {level_name}")
        
        if not df_map.empty:
            # Filter the table based on the user's dropdown choices
            if selected_mand != "All Mandals" and mand_col:
                df_map = df_map[df_map[mand_col].str.lower() == selected_mand.lower()]
            elif selected_const != "All Constituencies" and const_col:
                df_map = df_map[df_map[const_col].str.lower() == selected_const.lower()]
            elif selected_dist != "All Districts" and dist_col:
                df_map = df_map[df_map[dist_col].str.lower() == selected_dist.lower()]
                
            # Clean up the column names for presentation
            cols_to_keep = {}
            if dist_col: cols_to_keep[dist_col] = "District"
            if const_col: cols_to_keep[const_col] = "Constituency"
            if mand_col: cols_to_keep[mand_col] = "Mandal"
            if "candidate_in_english" in df_map.columns: cols_to_keep["candidate_in_english"] = "Candidate Name"
            if "party_in_english" in df_map.columns: cols_to_keep["party_in_english"] = "Party"
            if "status" in df_map.columns: cols_to_keep["status"] = "Status"
            
            if not df_map.empty:
                st.dataframe(df_map.rename(columns=cols_to_keep)[list(cols_to_keep.values())], use_container_width=True, hide_index=True)
            else:
                st.info("No candidates found matching this selection.")
        else:
            st.info("Detailed candidate list is currently loading or unavailable.")

    # Generate the content for both tabs independently
    with tab1:
        render_tab_content("Zilla Parishad")

    with tab2:
        render_tab_content("Mandal Parishad")

else:
    st.info("Loading data from ETV servers...")
