import streamlit as st
import pandas as pd
import requests
import time

st.set_page_config(
    page_title="FPL Draft Board", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Callbacks for League Buttons & Custom Input
def set_league_bbl1():
    st.session_state.custom_league_input = "16273"
    st.session_state.auto_refresh = False

def set_league_bbl2():
    st.session_state.custom_league_input = "11004"
    st.session_state.auto_refresh = False

def on_custom_code_change():
    st.session_state.auto_refresh = False

# Initialize session_state defaults
if "custom_league_input" not in st.session_state:
    st.session_state.custom_league_input = "11004"

# Custom CSS
st.markdown("""
<style>
    /* Clean layout spacing */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        z-index: 1 !important;
    }
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.25rem !important;
        padding-right: 0.25rem !important;
    }

    /* Mobile Side-Scroll Wrapper */
    .mobile-scroll-wrapper {
        width: 100%;
        overflow-x: auto !important;
        overflow-y: visible !important;
        -webkit-overflow-scrolling: touch;
        padding-bottom: 20px;
    }

    /* Force Streamlit Columns to stay side-by-side & narrow on mobile */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: stretch !important;
        width: max-content !important;
        min-width: 100% !important;
    }

    div[data-testid="column"] {
        width: 88px !important;
        min-width: 88px !important;
        max-width: 88px !important;
        flex: 0 0 88px !important;
        padding: 0 1px !important;
        box-sizing: border-box !important;
    }

    /* Fixed Narrow Pick Card Sizing */
    .pick-card {
        padding: 3px 1px;
        border-radius: 4px;
        margin-bottom: 3px;
        text-align: center;
        font-size: 0.68rem;
        font-weight: 600;
        color: white;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        box-shadow: 0 1px 3px rgba(0,0,0,0.25);
        height: 28px;
        line-height: 22px;
        box-sizing: border-box;
    }
    
    .empty-card {
        padding: 3px 1px;
        border-radius: 4px;
        margin-bottom: 3px;
        text-align: center;
        font-size: 0.68rem;
        color: #666;
        border: 1px dashed #444;
        height: 28px;
        line-height: 22px;
        box-sizing: border-box;
    }

    /* Compact Popover Toggle Button */
    button[data-testid="stPopoverButton"] {
        padding: 2px 1px !important;
        font-size: 0.7rem !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        height: 30px !important;
    }

    /* --- POPOVER CONTENT SIZE OVERRIDES --- */
    /* Break out of column width constraints for the popover panel */
    div[data-testid="stPopoverBody"] {
        width: 560px !important;
        min-width: 320px !important;
        max-width: 90vw !important;
        padding: 12px !important;
    }

    /* Larger text and elements inside the squad popover */
    div[data-testid="stPopoverBody"] p,
    div[data-testid="stPopoverBody"] strong {
        font-size: 0.95rem !important;
    }

    /* Expanded Pitch Badges inside Popover */
    .pitch-row {
        display: flex;
        justify-content: center;
        gap: 6px;
        margin-bottom: 8px;
    }

    .pitch-badge {
        flex: 1;
        padding: 6px 4px;
        border-radius: 4px;
        font-size: 0.82rem;
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
        color: #777;
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

# Header Area Layout
top_col1, top_col2 = st.columns([2, 2])

with top_col1:
    st.title("⚽ FPL Live Draft Board")
    auto_refresh = st.checkbox("Enable Auto-Refresh (10s)", key="auto_refresh", value=True)

with top_col2:
    st.write("### League Selection")
    btn_col1, btn_col2 = st.columns(2)
    
    btn_col1.button("BBL1 (16273)", on_click=set_league_bbl1, use_container_width=True)
    btn_col2.button("BBL2 (11004)", on_click=set_league_bbl2, use_container_width=True)

    league_code = st.text_input(
        "Custom League Code", 
        key="custom_league_input",
        on_change=on_custom_code_change
    )

if not league_code:
    st.warning("Please enter a valid Draft League Code.")
    st.stop()

# Load Data
try:
    footballers = load_static()
    data, player_data = load_league(league_code)

    id2baller = {x['id']: x['web_name'] for x in footballers['elements']}
    id2pos = {x['id']: POSITION_MAP.get(x['element_type'], "UNK") for x in footballers['elements']}
    
    entry2owner = {x['entry_id']: x['player_first_name'] for x in data['league_entries']}
    entry2name = {x['entry_id']: x['entry_name'] for x in data['league_entries']}

    # Load Choices
    picks = []
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
                'entry': item['owner'],
                'round': (idx // entries_count) + 1,
                'choice': idx + 1
            }
            for idx, item in enumerate(player_data['element_status'])
            if item.get('owner') is not None
        ]

    df = pd.DataFrame(picks) if picks else pd.DataFrame(columns=['entry', 'element', 'round'])

    if not df.empty:
        df['manager'] = df['entry'].map(lambda x: entry2owner.get(x, entry2name.get(x, "Unknown")))
        df['player_name'] = df['element'].map(lambda x: id2baller.get(x, "Unknown"))
        df['position'] = df['element'].map(lambda x: id2pos.get(x, "UNK"))

except Exception as e:
    st.error(f"Error fetching data for league code {league_code}. Please check the ID.")
    st.stop()

# Correct Round 1 Pick Sequence
# Derives draft_order strictly from Round 1 choice order so pick #1 is in column 1
if not df.empty and 'round' in df.columns and 1 in df['round'].values:
    round1_df = df[df['round'] == 1].sort_values(by='choice' if 'choice' in df.columns else 'index', ascending=True)
    entry_ids = list(round1_df['entry'].unique())
else:
    entry_ids = [x['entry_id'] for x in data['league_entries']]

draft_order = [entry2owner.get(eid, entry2name.get(eid, f"Team {idx+1}")) for idx, eid in enumerate(entry_ids)]
num_cols = len(draft_order)
max_rounds = 15

# Wrapper for Mobile Side Scrolling
st.markdown('<div class="mobile-scroll-wrapper">', unsafe_allow_html=True)

# Manager Header Row
header_cols = st.columns(num_cols)

for idx, (manager, entry_id) in enumerate(zip(draft_order, entry_ids)):
    manager_picks = df[df['entry'] == entry_id].sort_values(by='round') if not df.empty else pd.DataFrame()
    manager_label = str(manager) if str(manager).strip() else f"Team {idx + 1}"
    
    with header_cols[idx].popover(manager_label, use_container_width=True):
        st.markdown(f"**{manager_label}'s Squad**")
        
        for pos, slot_count in POSITION_SLOTS.items():
            pos_picks = manager_picks[manager_picks['position'] == pos]['player_name'].tolist() if not manager_picks.empty else []
            bg_color = POSITION_COLORS.get(pos, "#424242")
            
            row_badges = []
            for slot in range(slot_count):
                if slot < len(pos_picks):
                    p_name = pos_picks[slot]
                    row_badges.append(
                        f'<div class="pitch-badge" style="background-color: {bg_color};" title="{p_name}">{p_name}</div>'
                    )
                else:
                    row_badges.append('<div class="pitch-badge pitch-badge-empty">?</div>')
            
            st.markdown(f'<div class="pitch-row">{"".join(row_badges)}</div>', unsafe_allow_html=True)

st.write("")

# Draft Grid Rows
for r in range(1, max_rounds + 1):
    round_df = df[df['round'] == r] if not df.empty else pd.DataFrame()
    is_odd = (r % 2 != 0)
    
    cols = st.columns(num_cols)
    
    for c_idx, (manager, entry_id) in enumerate(zip(draft_order, entry_ids)):
        # Snake Direction Arrow
        if is_odd:
            arrow = "↓" if c_idx == num_cols - 1 else "→"
        else:
            arrow = "↓" if c_idx == 0 else "←"

        # Exact match per manager & round
        pick = round_df[round_df['entry'] == entry_id] if not round_df.empty else pd.DataFrame()

        if not pick.empty:
            p_name = pick.iloc[0]['player_name']
            p_pos = pick.iloc[0]['position']
            bg_color = POSITION_COLORS.get(p_pos, "#424242")
            
            cols[c_idx].markdown(
                f"""
                <div class="pick-card" style="background-color: {bg_color};" title="R{r} P{c_idx+1}: {p_name} ({p_pos})">
                    {p_name} <span style="opacity:0.8; font-size:0.6rem;">{arrow}</span>
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

st.markdown('</div>', unsafe_allow_html=True)

# Auto-refresh Loop at Bottom
if auto_refresh:
    time.sleep(10)
    st.rerun()
