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

# Clean CSS Styling + Mobile Horizontal Scroll Override
st.markdown("""
<style>
    /* Remove header padding & white bar overlap */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        z-index: 1 !important;
    }
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }

    /* ----------------------------------------------------------------
       MOBILE HORIZONTAL SCROLL OVERRIDE
       ---------------------------------------------------------------- */
    /* Container wrapper allowing smooth horizontal swiping */
    .mobile-scroll-wrapper {
        width: 100%;
        overflow-x: auto !important;
        overflow-y: visible !important;
        -webkit-overflow-scrolling: touch;
        padding-bottom: 15px;
    }

    /* Prevent Streamlit from stacking columns vertically on mobile */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            min-width: max-content !important;
        }

        /* Force columns to stay side-by-side with a compact width */
        div[data-testid="column"] {
            min-width: 110px !important;
            max-width: 120px !important;
            flex: 1 0 110px !important;
            padding: 0 2px !important;
        }

        /* Adjust popover button padding on small screens */
        button[data-testid="stPopoverButton"] {
            padding: 4px 2px !important;
            font-size: 0.75rem !important;
        }
    }

    /* Fixed size pick cards for tight horizontal alignment */
    .pick-card {
        padding: 4px 2px;
        border-radius: 4px;
        margin-bottom: 4px;
        text-align: center;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        box-shadow: 0 1px 3px rgba(0,0,0,0.25);
        height: 32px;
        line-height: 24px;
        box-sizing: border-box;
    }
    
    .empty-card {
        padding: 4px 2px;
        border-radius: 4px;
        margin-bottom: 4px;
        text-align: center;
        font-size: 0.75rem;
        color: #666;
        border: 1px dashed #444;
        height: 32px;
        line-height: 24px;
        box-sizing: border-box;
    }

    /* Roster Pitch Badges inside Popover */
    .pitch-row {
        display: flex;
        justify-content: center;
        gap: 4px;
        margin-bottom: 6px;
    }

    .pitch-badge {
        flex: 1;
        padding: 4px 2px;
        border-radius: 4px;
        font-size: 0.7rem;
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
    df['manager'] = df['entry_name'].map(lambda x: id2owner.get(x, x)).fillna("Unknown Manager")
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

# START MOBILE SCROLL WRAPPER
st.markdown('<div class="mobile-scroll-wrapper">', unsafe_allow_html=True)

# Header Manager Row using Streamlit Popovers
header_cols = st.columns(num_cols)

for idx, manager in enumerate(draft_order):
    manager_picks = df[df['manager'] == manager].sort_values(by='round')
    
    manager_label = str(manager) if pd.notna(manager) and str(manager).strip() else f"Team {idx + 1}"
    
    with header_cols[idx].popover(manager_label, use_container_width=True):
        st.markdown(f"**{manager_label}'s Squad**")
        
        for pos, slot_count in POSITION_SLOTS.items():
            pos_picks = manager_picks[manager_picks['position'] == pos]['player_name'].tolist()
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

st.write("") # Spacer

# Draft Grid Rows
for r in range(1, max_rounds + 1):
    round_df = df[df['round'] == r]
    is_odd = (r % 2 != 0)
    
    cols = st.columns(num_cols)
    
    for c_idx, manager in enumerate(draft_order):
        pick = round_df[round_df['manager'] == manager]
        
        # Snake Direction Arrow
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
                    {p_name} <span style="opacity:0.8; font-size:0.7rem;">{arrow}</span>
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

# CLOSE MOBILE SCROLL WRAPPER
st.markdown('</div>', unsafe_allow_html=True)

# Auto-refresh Loop at Bottom
if auto_refresh:
    time.sleep(10)
    st.rerun()