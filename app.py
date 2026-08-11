import streamlit as st
import pandas as pd
import requests
import time

st.set_page_config(page_title="FPL Draft Tracker", layout="wide")

LEAGUE_CODE = "25152"  # Update with your league ID
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

# Optional xPPG map
player2xPts = {}
max_points = max(player2xPts.values()) if player2xPts else 1

def custom_styling(val):
    if pd.isna(val):
        return 'background-color: #f0f0f0;'
    
    pos = id2pos.get(val)
    if pos == 1: color = "#ccebc5"
    elif pos == 2: color = "#fed9a6"
    elif pos == 3: color = "#b3cde3"
    elif pos == 4: color = "#fbb4ae"
    else: color = 'lightgray'

    xpts = player2xPts.get(val, 0)
    width_percent = (100 * xpts / max_points) if max_points > 0 else 0

    return (
        f'background-image: linear-gradient(270deg, {color} {width_percent}%, transparent {width_percent}%);'
        f'background-color: lightgray;'
        'background-repeat: no-repeat;'
        'background-position: right center;'
        'background-size: 100% 100%;'
        'text-align: right;'
        'border: 1px solid black;'
    )

def render_board():
    try:
        choices = load_draft(LEAGUE_CODE)
        picks = choices.get('choices', [])
    except Exception:
        picks = []

    # Fallback for finished drafts
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

    # Column header totals
    viz.columns = [
        f"{col} ({sum(player2xPts.get(x, 0) for x in viz[col].dropna()):.2f})"
        for col in viz.columns
    ]

    styler = viz.style.format(lambda x: id2baller.get(x, ""))
    styler.map(custom_styling)
    
    st.write(styler.to_html(), unsafe_allow_html=True)

st.title("FPL Live Draft Board")

# Auto-refresh loop control
auto_refresh = st.checkbox("Enable Auto-Refresh (10s)", value=True)
render_board()

if auto_refresh:
    time.sleep(10)
    st.rerun()

