import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="FPL Draft Tracker", layout="wide")

LEAGUE_CODE = "25152"  # Update with your league ID
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

POSITION_MAP = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
POSITION_COLORS = {
    "GKP": "#2e7d32",  # Dark Green
    "DEF": "#e65100",  # Dark Orange
    "MID": "#1565c0",  # Dark Blue
    "FWD": "#c62828",  # Dark Red
}

@st.cache_data(ttl=3600)
def load_static():
    return requests.get("https://draft.premierleague.com/api/bootstrap-static", headers=HEADERS).json()

@st.cache_data(ttl=3600)
def load_league(league_code):
    data = requests.get(f"https://draft.premierleague.com/api/league/{league_code}/details", headers=HEADERS).json()
    player_data = requests.get(f"https://draft.premierleague.com/api/league/{league_code}/element-status", headers=HEADERS).json()
    return data, player_data

def load_draft(league_code):
    return requests.get(f"https://draft.premierleague.com/api/draft/{league_code}/choices", headers=HEADERS).json()

# Setup Data
footballers = load_static()
data, player_data = load_league(LEAGUE_CODE)

id2baller = {x['id']: x['web_name'] for x in footballers['elements']}
id2pos_id = {x['id']: x['element_type'] for x in footballers['elements']}
id2pos = {x['id']: POSITION_MAP.get(x['element_type'], "UNK") for x in footballers['elements']}
id2owner = {x['entry_name']: x['player_first_name'] for x in data['league_entries']}

# Fetch picks
try:
    choices = load_draft(LEAGUE_CODE)
    picks = choices.get('choices', [])
except Exception:
    picks = []

if not picks and 'element_status' in player_data:
    entries_count = len(data['league_entries'])
    picks = [
        {
            'element': item['element'],
            'entry_name': item['owner'],
            'round': (idx // entries_count) + 1
        }
        for idx, item in enumerate(player_data['element_status'])
    ]

df = pd.DataFrame(picks)
df['manager'] = df['entry_name'].map(lambda x: id2owner.get(x, x))
df['player_name'] = df['element'].map(lambda x: id2baller.get(x, "Unknown"))
df['position'] = df['element'].map(lambda x: id2pos.get(x, "UNK"))

# Layout UI
st.title("⚽ FPL Live Draft & Team Tracker")

view_mode = st.radio("Select View:", ["🎯 Draft Board", "👤 Team Rosters"], horizontal=True)

# ---------------------------------------------------------
# VIEW 1: CARDS DRAFT BOARD
# ---------------------------------------------------------
if view_mode == "🎯 Draft Board":
    st.subheader("Snake Draft Board")
    
    round1 = df[df['round'] == 1]
    draft_order = list(round1['manager']) if not round1.empty else list(df['manager'].unique())
    
    num_cols = len(draft_order)
    max_rounds = int(df['round'].max()) if not df.empty else 0

    # Header Row with Manager Names
    header_cols = st.columns(num_cols)
    for idx, manager in enumerate(draft_order):
        header_cols[idx].markdown(f"### **{manager}**")

    st.divider()

    # Grid of Rounds
    for r in range(1, max_rounds + 1):
        round_df = df[df['round'] == r]
        is_odd = (r % 2 != 0)
        
        cols = st.columns(num_cols)
        st.caption(f"**Round {r}** {'(→ Right)' if is_odd else '(← Left)'}")
        
        for c_idx, manager in enumerate(draft_order):
            pick = round_df[round_df['manager'] == manager]
            
            # Snake Arrows
            if is_odd:
                arrow = "↓" if c_idx == num_cols - 1 else "→"
            else:
                arrow = "↓" if c_idx == 0 else "←"

            if not pick.empty:
                p_name = pick.iloc[0]['player_name']
                p_pos = pick.iloc[0]['position']
                bg_color = POSITION_COLORS.get(p_pos, "#424242")
                
                # Render Individual Styled Card
                cols[c_idx].markdown(
                    f"""
                    <div style="
                        background-color: {bg_color}; 
                        color: white; 
                        padding: 8px; 
                        border-radius: 6px; 
                        margin-bottom: 5px; 
                        text-align: center;
                        font-weight: bold;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    ">
                        <small style="opacity: 0.8;">{p_pos} {arrow}</small><br>
                        {p_name}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            else:
                cols[c_idx].markdown(
                    f"""
                    <div style="
                        border: 1px dashed #ccc; 
                        padding: 8px; 
                        border-radius: 6px; 
                        text-align: center;
                        color: #888;
                    ">
                        {arrow}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

# ---------------------------------------------------------
# VIEW 2: INDIVIDUAL TEAM VIEW
# ---------------------------------------------------------
else:
    st.subheader("Team Roster Explorer")
    
    managers = sorted(list(df['manager'].unique()))
    
    # Manager selection tabs at top
    tabs = st.tabs(managers)
    
    for idx, manager in enumerate(managers):
        with tabs[idx]:
            team_df = df[df['manager'] == manager].copy()
            st.markdown(f"### **{manager}'s Squad** ({len(team_df)} Players)")
            
            # Group by Position
            col1, col2, col3, col4 = st.columns(4)
            
            for pos_name, container in zip(["GKP", "DEF", "MID", "FWD"], [col1, col2, col3, col4]):
                pos_players = team_df[team_df['position'] == pos_name]
                container.markdown(f"#### **{pos_name}** ({len(pos_players)})")
                
                for _, row in pos_players.iterrows():
                    bg_color = POSITION_COLORS.get(pos_name, "#424242")
                    container.markdown(
                        f"""
                        <div style="
                            background-color: {bg_color}; 
                            color: white; 
                            padding: 10px; 
                            border-radius: 6px; 
                            margin-bottom: 8px;
                        ">
                            <strong>{row['player_name']}</strong><br>
                            <small>Drafted Rd {row['round']}</small>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )