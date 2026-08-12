import streamlit as st
import pandas as pd
import requests
import time

st.set_page_config(
    page_title="FPL Draft Board", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Custom CSS fixing white bar overlay and styling visual pitch roster tooltips
st.markdown("""
<style>
    /* Remove white bar padding and fix top clipping */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        z-index: 1 !important;
    }
    
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }

    /* Hover Tooltip Header Button */
    .tooltip-header {
        position: relative;
        display: block;
        width: 100%;
        text-align: center;
        background-color: #1e1e1e;
        color: #ffffff;
        padding: 8px 4px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 0.95rem;
        cursor: pointer;
        border: 1px solid #444;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.3);
    }

    /* Pitch Visual Tooltip Box */
    .tooltip-header .tooltip-text {
        visibility: hidden;
        width: 320px;
        background-color: #121212;
        color: #fff;
        text-align: center;
        border-radius: 8px;
        padding: 12px;
        position: absolute;
        z-index: 99999 !important;
        top: 110%;
        left: 50%;
        transform: translateX(-50%);
        box-shadow: 0px 8px 24px rgba(0,0,0,0.8);
        border: 1px solid #333;
        font-weight: normal;
    }

    /* Show Tooltip on Mouseover */
    .tooltip-header:hover .tooltip-text {
        visibility: visible;
    }

    /* Formation Pitch Rows */
    .pitch-row {
        display: flex;
        justify-content: center;
        gap: 4px;
        margin-bottom: 6px;
    }

    /* Individual Formation Badges */
    .pitch-badge {
        flex: 1;
        padding: 4px 2px;
        border-radius: 4px;
        font-size: 0.68rem;
        font-weight: bold;
        color: white;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        text-align: center;
    }

    .pitch-badge-empty {
        background-color: #000000;
        border: 1px dashed #555;
        color: #888;
    }

    /* Pick Cards */
    .pick-card {
        padding: 6px 6px;
        border-radius: 4px;
        margin-bottom: 4px;
        text-align: center;
        font-size: 0.82rem;
        font-weight: 600;
        color: white;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        box-shadow: 0 1px 3px rgba(0,0,0,0.25);
        line-height: 1.3;
    }
    
    .empty-card {
        padding: 6px 6px;
        border-radius: 4px;
        margin-bottom: 4px;
        text-align: center;
        font-size: 0.82rem;
        color: #666;
        border: 1px dashed #444;
        line-height: 1.3;
    }
</style>
""", unsafe_allow_html=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

POSITION_MAP = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
POSITION_COLORS = {
    "GKP": "#2e7d32",  # Dark Green
    "DEF": "#e65100",  # Dark Orange
    "MID": "#1565c0",  # Dark Blue
    "FWD": "#c62828",  # Dark Red
}

POSITION_SLOTS = {
    "GKP": 2,
    "DEF": 5,
    "MID": 5,
    "FWD": 3
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

# Manage active league code in session state
if "league_code" not in st.session_state:
    st.session_state.league_code = "11004"

# Header Layout: Title & Refresh Toggle on Left | League Quick Toggles on Right
top_col1, top_col2 = st.columns([2, 2])

with top_col1:
    st.title("⚽ FPL Live Draft Board")
    auto_refresh = st.checkbox("Enable Auto-Refresh (10s)", value=True)

with top_col2:
    st.write("### League Selection")
    btn_col1, btn_col2 = st.columns(2)
    
    if btn_col1.button("BBL1 (16273)", use_container_width=True):
        st.session_state.league_code = "16273"
        st.rerun()
        
    if btn_col2.button("BBL2 (11004)", use_container_width=True):
        st.session_state.league_code = "11004"
        st.rerun()

    league_code = st.text_input("Custom League Code", value=st.session_state.league_code)
    st.session_state.league_code = league_code

if not league_code:
    st.warning("Please enter a valid Draft League Code.")
    st.stop()

# Load API Data
try:
    footballers = load_static()
    data, player_data = load_league(league_code)

    id2baller = {x['id']: x['web_name'] for x in footballers['elements']}
    id2pos = {x['id']: POSITION_MAP.get(x['element_type'], "UNK") for x in footballers['elements']}
    id2owner = {x['entry_name']: x['player_first_name'] for x in data['league_entries']}

    try:
        choices = load_draft(league_code)
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

except Exception as e:
    st.error(f"Error fetching data for league code {league_code}. Please check the ID.")
    st.stop()

# Order Managers by Round 1 Draft Sequence
round1 = df[df['round'] == 1]
draft_order = list(round1['manager']) if not round1.empty else list(df['manager'].unique())
num_cols = len(draft_order)
max_rounds = int(df['round'].max()) if not df.empty else 15

# Header Columns with Squad Visual Tooltips
header_cols = st.columns(num_cols)

for idx, manager in enumerate(draft_order):
    manager_picks = df[df['manager'] == manager].sort_values(by='round')
    
    # Build Visual Pitch Rows (GKP:2, DEF:5, MID:5, FWD:3)
    pitch_html_rows = []
    
    for pos, slot_count in POSITION_SLOTS.items():
        pos_picks = manager_picks[manager_picks['position'] == pos]['player_name'].tolist()
        bg_color = POSITION_COLORS.get(pos, "#424242")
        
        row_badges = []
        for slot in range(slot_count):
            if slot < len(pos_picks):
                player_name = pos_picks[slot]
                row_badges.append(
                    f'<div class="pitch-badge" style="background-color: {bg_color};" title="{player_name}">{player_name}</div>'
                )
            else:
                row_badges.append(
                    '<div class="pitch-badge pitch-badge-empty">?</div>'
                )
        
        badges_str = "".join(row_badges)
        pitch_html_rows.append(f'<div class="pitch-row">{badges_str}</div>')
    
    full_pitch_html = "".join(pitch_html_rows)
    
    header_cols[idx].markdown(
        f"""
        <div class="tooltip-header">
            {manager}
            <div class="tooltip-text">
                <div style="font-weight:bold; border-bottom: 1px solid #444; margin-bottom: 8px; padding-bottom:4px;">
                    {manager}'s Squad
                </div>
                {full_pitch_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.write("") # Micro-spacer

# Render Grid
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
                    {p_name} <span style="opacity:0.8; font-size:0.75rem;">{arrow}</span>
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

# Auto-refresh Loop at the Bottom
if auto_refresh:
    time.sleep(10)
    st.rerun()