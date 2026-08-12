import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="FPL Draft Board", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Custom CSS for compact density and instant CSS tooltips
st.markdown("""
<style>
    /* Remove padding around main container for maximum screen space */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }
    
    /* Hover Tooltip Container */
    .tooltip-header {
        position: relative;
        display: inline-block;
        width: 100%;
        text-align: center;
        background-color: #1e1e1e;
        color: #ffffff;
        padding: 4px 2px;
        border-radius: 4px;
        font-weight: bold;
        cursor: pointer;
        border: 1px solid #444;
    }

    /* Hidden Tooltip Box */
    .tooltip-header .tooltip-text {
        visibility: hidden;
        width: 240px;
        background-color: #121212;
        color: #fff;
        text-align: left;
        border-radius: 6px;
        padding: 8px 10px;
        position: absolute;
        z-index: 999;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        box-shadow: 0px 4px 12px rgba(0,0,0,0.5);
        border: 1px solid #333;
        font-weight: normal;
        font-size: 0.75rem;
        line-height: 1.2;
    }

    /* Show Tooltip on Mouseover */
    .tooltip-header:hover .tooltip-text {
        visibility: visible;
    }

    /* Compact Badge Card */
    .pick-card {
        padding: 2px 4px;
        border-radius: 3px;
        margin-bottom: 2px;
        text-align: center;
        font-size: 0.73rem;
        font-weight: 600;
        color: white;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        box-shadow: 0 1px 2px rgba(0,0,0,0.15);
        line-height: 1.2;
    }
    
    .empty-card {
        padding: 2px 4px;
        border-radius: 3px;
        margin-bottom: 2px;
        text-align: center;
        font-size: 0.73rem;
        color: #666;
        border: 1px dashed #444;
    }
</style>
""", unsafe_allow_html=True)

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

# Load Data
footballers = load_static()
data, player_data = load_league(LEAGUE_CODE)

id2baller = {x['id']: x['web_name'] for x in footballers['elements']}
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

# Order Managers by Round 1
round1 = df[df['round'] == 1]
draft_order = list(round1['manager']) if not round1.empty else list(df['manager'].unique())
num_cols = len(draft_order)
max_rounds = int(df['round'].max()) if not df.empty else 15

# Header Columns with Mouseover Hover Tooltips
header_cols = st.columns(num_cols)

for idx, manager in enumerate(draft_order):
    manager_picks = df[df['manager'] == manager]
    
    # Generate Roster Breakdown HTML for Tooltip
    roster_lines = []
    for pos in ["GKP", "DEF", "MID", "FWD"]:
        pos_players = manager_picks[manager_picks['position'] == pos]['player_name'].tolist()
        if pos_players:
            players_str = ", ".join(pos_players)
            color = POSITION_COLORS.get(pos, "#fff")
            roster_lines.append(f"<strong style='color:{color}'>{pos}:</strong> {players_str}")
    
    tooltip_content = "<br>".join(roster_lines) if roster_lines else "No picks yet"
    
    header_cols[idx].markdown(
        f"""
        <div class="tooltip-header">
            {manager}
            <div class="tooltip-text">
                <div style="font-weight:bold; border-bottom: 1px solid #444; margin-bottom: 4px; padding-bottom:2px;">
                    {manager}'s Squad
                </div>
                {tooltip_content}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.write("") # Micro-spacer

# Render Single Desktop View Compact Draft Board Grid
for r in range(1, max_rounds + 1):
    round_df = df[df['round'] == r]
    is_odd = (r % 2 != 0)
    
    cols = st.columns(num_cols)
    
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
            
            cols[c_idx].markdown(
                f"""
                <div class="pick-card" style="background-color: {bg_color};" title="R{r} P{c_idx+1}: {p_name} ({p_pos})">
                    {p_name} <span style="opacity:0.75; font-size:0.65rem;">{arrow}</span>
                </div>
                """, 
                unsafe_allow_html=True
            )
        else:
            cols[c_idx].markdown(
                f"""
                <div class="empty-card">
                    {arrow}
                </div>
                """, 
                unsafe_allow_html=True
            )