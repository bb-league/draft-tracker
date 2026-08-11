import streamlit as st
import pandas as pd
import requests
import time

st.set_page_config(page_title="FPL Draft Tracker", layout="wide")

LEAGUE_CODE = "28664"  # Update with your league ID
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

@st.cache_data(ttl=3600)
def load_static():
    res = requests.get("https://draft.premierleague.com/api/bootstrap-static", headers=HEADERS)
    return res.json()

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
id2pos = {x['id']: x['element_type'] for x in footballers['elements']}
id2owner = {x['entry_name']: x['player_first_name'] for x in data['league_entries']}

# Optional expected points dictionary (empty dict triggers positional fallback colors)
player2xPts = {}
max_points = max(player2xPts.values()) if player2xPts else 0

def custom_styling(val):
    if pd.isna(val) or val == "":
        return 'background-color: #f9f9f9; text-align: center;'
    
    pos = id2pos.get(val)
    if pos == 1: color = "#ccebc5"    # GKP (Green)
    elif pos == 2: color = "#fed9a6"  # DEF (Orange)
    elif pos == 3: color = "#b3cde3"  # MID (Blue)
    elif pos == 4: color = "#fbb4ae"  # FWD (Red)
    else: color = '#e0e0e0'

    # Check if expected points are available
    xpts = player2xPts.get(val, 0)
    has_xpts = max_points > 0 and val in player2xPts

    if has_xpts:
        width_percent = (100 * xpts / max_points)
        bg_style = (
            f'background-image: linear-gradient(270deg, {color} {width_percent}%, transparent {width_percent}%);'
            f'background-color: lightgray;'
            'background-repeat: no-repeat;'
            'background-position: right center;'
            'background-size: 100% 100%;'
        )
    else:
        # Fallback to full solid positional color
        bg_style = f'background-color: {color};'

    return (
        f'{bg_style}'
        'text-align: center;'
        'border: 1px solid #333;'
        'font-weight: 500;'
    )

def render_board():
    try:
        choices = load_draft(LEAGUE_CODE)
        picks = choices.get('choices', [])
    except Exception:
        picks = []

    # Fallback for completed drafts
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
    if df.empty:
        st.error("No pick data found for this league.")
        return

    df['entry_name'] = df['entry_name'].map(lambda x: id2owner.get(x, x))
    
    # Preserve Round 1 Order
    round1 = df[df['round'] == 1]
    draft_order = list(round1['entry_name']) if not round1.empty else list(df['entry_name'].unique())

    viz = df.pivot(index='round', columns='entry_name', values='element')
    viz = viz.reindex(columns=draft_order)

    num_cols = len(viz.columns)

    # Format cell content with player names and directional snake arrows
    formatted_viz = viz.copy().astype(object)
    for round_num in viz.index:
        is_odd = (round_num % 2 != 0)
        for col_idx, col_name in enumerate(viz.columns):
            player_id = viz.loc[round_num, col_name]
            player_name = id2baller.get(player_id, "") if pd.notna(player_id) else ""

            if not player_name:
                formatted_viz.loc[round_num, col_name] = ""
                continue

            # Determine snake direction arrows
            if is_odd:
                if col_idx == num_cols - 1:
                    arrow = " ↓"  # Right edge down arrow to even round
                else:
                    arrow = " →"  # Odd round going right
            else:
                if col_idx == 0:
                    arrow = " ↓"  # Left edge down arrow to odd round
                else:
                    arrow = " ←"  # Even round going left

            formatted_viz.loc[round_num, col_name] = f"{player_name}{arrow}"

    # Format column header totals if xPPG exists
    has_xpts = max_points > 0 and len(player2xPts) > 0
    if has_xpts:
        viz.columns = [
            f"{col} ({sum(player2xPts.get(x, 0) for x in viz[col].dropna()):.2f})"
            for col in viz.columns
        ]
        formatted_viz.columns = viz.columns

    # Render Styler
    styler = viz.style.format(lambda val: id2baller.get(val, "") if pd.notna(val) else "")
    styler.map(custom_styling)

    # Inject formatted text (player name + arrow) into styled cells
    html_out = styler.to_html()
    for col_name in viz.columns:
        for round_num in viz.index:
            p_id = viz.loc[round_num, col_name]
            if pd.notna(p_id):
                raw_name = id2baller.get(p_id, "")
                arrow_text = formatted_viz.loc[round_num, col_name]
                html_out = html_out.replace(f">{raw_name}<", f">{arrow_text}<", 1)

    st.write(html_out, unsafe_allow_html=True)

st.title("FPL Live Draft Board")

# Auto-refresh loop
auto_refresh = st.checkbox("Enable Auto-Refresh (10s)", value=True)
render_board()

if auto_refresh:
    time.sleep(10)
    st.rerun()
    