"""
Vegan Friendly — Israeli Pension Fund Vegan Grade Dashboard (Hebrew)
Reads from GS_VEGAN_EXPORT Google Sheet (Funds + Parent Companies tabs).
"""
import json
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

SHEET_ID = "13TBGxhTo970evb5VCZ-hMDJzGKqY7SlDO5bV74rlSDo"

GRADE_COLORS = {1: "#2ecc71", 2: "#a8e063", 3: "#f5a623", 4: "#e67e22", 5: "#e74c3c"}
GRADE_LABELS = {1: "1 – מיטבי", 2: "2", 3: "3 – בינוני", 4: "4", 5: "5 – הגרוע ביותר"}
ANIMAL_RED = "#e74c3c"

# Logos: Google favicon service for most; Wikimedia for Berkshire; static file for Coca-Cola
LOGO_URLS = {
    "TEVA": "https://www.google.com/s2/favicons?domain=tevapharm.com&sz=64",
    "AMZN": "https://www.google.com/s2/favicons?domain=amazon.com&sz=64",
    "LLY":  "https://www.google.com/s2/favicons?domain=lilly.com&sz=64",
    "ABBV": "https://www.google.com/s2/favicons?domain=abbvie.com&sz=64",
    "WMT":  "https://www.google.com/s2/favicons?domain=walmart.com&sz=64",
    "HD":   "https://www.google.com/s2/favicons?domain=homedepot.com&sz=64",
    "BABA": "https://www.google.com/s2/favicons?domain=alibaba.com&sz=64",
    "BRK":  "app/static/BH-logo.png",
    "HON":  "https://www.google.com/s2/favicons?domain=honeywell.com&sz=64",
    "KO":   "app/static/coca-cola.svg",
}

# Major parent company legal IDs (from parent_company.is_major = 1)
MAJOR_PARENT_IDS = {
    "513621110", "513173393", "511880460", "520023185", "513026484",
    "520004078", "512267592", "513611509", "520024647", "512244146",
    "520004896", "512237744", "514956465", "512065202", "520042540", "512245812",
}

# Number of Israelis with pension/savings accounts (source: Israeli CBS / Clearance authority)
ISRAELI_SAVERS = 4_500_000

# Top 10 animal-exploiting companies by total NIS invested across all funds (2025Q4)
# NIS values: SUM(holdings_flagged.value * Animal_Exploitation_flag) per figi_name_norm × 1000 (thousands→ILS)
TOP_COMPANIES = [
    {
        "company": "Teva Pharmaceutical",
        "ticker": "TEVA",
        "domain": "tevapharm.com",
        "category": "ניסויים בבעלי חיים",
        "nis": 20_007_316_813,
        "desc": "טבע מפתחת ובודקת תרופות גנריות וייחודיות על בעלי חיים, ובכלל זה מחקרים על מודלים של מחלות דלקתיות.",
    },
    {
        "company": "Amazon.com",
        "ticker": "AMZN",
        "domain": "amazon.com",
        "category": "מזון, עור, פרווה",
        "nis": 8_480_817_380,
        "desc": "אמזון מוכרת מוצרי בשר, חלב וביצים, פריטי עור ופרווה, ואף שיווקה פואה גרה מיצרנים שתועדה אצלם אכזריות כלפי בעלי חיים.",
    },
    {
        "company": "Eli Lilly",
        "ticker": "LLY",
        "domain": "lilly.com",
        "category": "ניסויים בבעלי חיים",
        "nis": 2_246_871_530,
        "desc": "אלי לילי מבצעת ניסויים בבעלי חיים לצורך בדיקת בטיחות תרופותיה, בהתאם לדרישות ה-FDA.",
    },
    {
        "company": "AbbVie",
        "ticker": "ABBV",
        "domain": "abbvie.com",
        "category": "ניסויים בבעלי חיים",
        "nis": 1_065_820_751,
        "desc": "אבווי מבצעת ניסויים נרחבים בבעלי חיים במסגרת המחקר והפיתוח של מוצריה הביו-פרמצבטיים.",
    },
    {
        "company": "Walmart",
        "ticker": "WMT",
        "domain": "walmart.com",
        "category": "מזון, עור, חיות מחמד",
        "nis": 929_573_593,
        "desc": "וולמארט מוכרת מזון מן החי, מוצרי עור ופרווה, וכן חיות מחמד בחלק מהסניפים.",
    },
    {
        "company": "Home Depot",
        "ticker": "HD",
        "domain": "homedepot.com",
        "category": "עור, מזון",
        "nis": 915_038_785,
        "desc": "הום דיפו מוכרת כפפות עבודה ופריטי עור נוספים, וכן מזון המכיל מוצרים מן החי.",
    },
    {
        "company": "Alibaba Group",
        "ticker": "BABA",
        "domain": "alibaba.com",
        "category": "מזון, עור, פרווה",
        "nis": 914_846_125,
        "desc": "עליבאבא משווקת מוצרי עור, פרווה ומזון מן החי דרך הפלטפורמות הדיגיטליות שלה.",
    },
    {
        "company": "Berkshire Hathaway",
        "ticker": "BRK",
        "domain": "berkshirehathaway.com",
        "category": "עור, מזון",
        "nis": 760_380_671,
        "desc": "ברקשייר מחזיקה בחברות בתחום ההנעלה מעור, ברשתות מזון (Dairy Queen, Kraft Heinz) ועוד.",
    },
    {
        "company": "Honeywell International",
        "ticker": "HON",
        "domain": "honeywell.com",
        "category": "עור",
        "nis": 711_754_291,
        "desc": "האניוול מייצרת ומשווקת נעליים מעור באמצעות חברת הבת Muck Boots.",
    },
    {
        "company": "Coca-Cola",
        "ticker": "KO",
        "domain": "coca-cola.com",
        "category": "מזון, ניסויים",
        "nis": 681_399_864,
        "desc": "קוקה-קולה משתמשת בג'לטין מדגים כחומר מייצב בחלק ממשקאותיה, ומסתמכת על ניסויים בבעלי חיים לבדיקת בטיחותם של מרכיבים.",
    },
]


def _get_credentials():
    from google.oauth2.service_account import Credentials
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        return Credentials.from_service_account_info(info, scopes=scopes)
    if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
        raw = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
        info = json.loads(raw) if isinstance(raw, str) else dict(raw)
        return Credentials.from_service_account_info(info, scopes=scopes)
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if raw.strip().startswith("{"):
        return Credentials.from_service_account_info(json.loads(raw), scopes=scopes)
    if raw:
        return Credentials.from_service_account_file(raw, scopes=scopes)
    raise EnvironmentError("No Google credentials found.")


@st.cache_data(ttl=3600)
def load_data():
    import gspread
    gc = gspread.authorize(_get_credentials())
    sh = gc.open_by_key(SHEET_ID)

    funds = pd.DataFrame(sh.worksheet("Funds").get_all_records())
    parents = pd.DataFrame(sh.worksheet("Parent Companies").get_all_records())

    for col in ["vegan_grade", "vegan_flagged_pct", "vegan_flagged_sum",
                "ENVA_grade", "enva_flagged_pct", "covered_of_total_pct"]:
        if col in funds.columns:
            funds[col] = pd.to_numeric(funds[col], errors="coerce")
    if "vegan_flagged_sum" in funds.columns:
        funds["vegan_flagged_sum"] = funds["vegan_flagged_sum"] * 1000  # thousands → ILS

    # Fix HTML-encoded ampersands in fund names (e.g. "S&amp;P" or "S1;P" → "S&P")
    import html as _html
    if "fund_name" in funds.columns:
        funds["fund_name"] = (
            funds["fund_name"]
            .apply(_html.unescape)
            .str.replace(r"[Ss]\d+;[Pp]", "S&P", regex=True)
            .str.replace(r"S&P(\d)", r"S&P \1", regex=True)
        )

    for col in ["parent_vegan_grade", "parent_vegan_flagged_pct", "parent_vegan_flagged_sum",
                "parent_ENVA_grade", "parent_flagged_pct"]:
        if col in parents.columns:
            parents[col] = pd.to_numeric(parents[col], errors="coerce")
    if "parent_vegan_flagged_sum" in parents.columns:
        parents["parent_vegan_flagged_sum"] = parents["parent_vegan_flagged_sum"] * 1000

    # Normalise legal_id for major-company filter
    if "parent_company_legal_id" in parents.columns:
        parents["_legal_id_str"] = (
            parents["parent_company_legal_id"].astype(str).str.replace(r"\.0+$", "", regex=True)
        )

    return funds, parents


def fmt_nis(val, decimals=1):
    if pd.isna(val):
        return "—"
    if abs(val) >= 1e9:
        return f"₪{val/1e9:.{decimals}f}B"
    if abs(val) >= 1e6:
        return f"₪{val/1e6:.{decimals}f}M"
    if abs(val) >= 1e3:
        return f"₪{val/1e3:.{decimals}f}K"
    return f"₪{val:.0f}"


def main():
    st.set_page_config(
        page_title="כספי הפנסיה של כולנו מממנים פגיעה בבעלי חיים",
        page_icon="🐄",
        layout="wide",
    )

    try:
        from dotenv import load_dotenv
        from pathlib import Path
        load_dotenv(Path(__file__).parent / ".env")
    except Exception:
        pass

    st.markdown(
        """
        <style>
        html, body, [class*="css"] { direction: rtl; }
        .stApp { direction: rtl; }
        section[data-testid="stSidebar"] { direction: rtl; }
        .stMarkdown, .stText, .stCaption,
        div[data-testid="metric-container"],
        div[data-testid="stExpander"],
        .stTabs, .stDataFrame,
        label, p, h1, h2, h3, span { direction: rtl; text-align: right; }
        .js-plotly-plot { direction: ltr; }
        div[data-testid="metric-container"] > div { text-align: right; }
        .stTabs [data-baseweb="tab-list"] { justify-content: flex-end; }
        input[type="text"] { direction: rtl; text-align: right; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.spinner("טוען נתונים..."):
        funds, parents = load_data()

    graded = funds[funds["vegan_grade"].notna()].copy()
    graded["vegan_grade_int"] = graded["vegan_grade"].astype(int)

    subsystems = sorted(graded["subsystem"].dropna().unique())

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style='text-align:center;padding:1rem 0 0.5rem'>
          <h1 style='color:#2c3e50;margin-bottom:0.2rem'>
            🐄 כספי הפנסיה של כולנו מממנים פגיעה בבעלי חיים.<br>
            <span style='font-size:0.7em;color:#e74c3c;display:block;text-align:center'>כן, גם שלך.</span>
          </h1>
          <p style='color:#7f8c8d;font-size:1.1em;margin:0'>
            קופות פנסיה וחיסכון ישראליות — ניתוח חשיפה לחברות הפוגעות בבעלי חיים · רבעון 4, 2025
          </p>
        </div>
        <hr style='margin:0.5rem 0 1rem'>
        """,
        unsafe_allow_html=True,
    )

    # ── Big central metric ────────────────────────────────────────────────────
    total_nis = graded["vegan_flagged_sum"].sum()
    avg_per_person = total_nis / ISRAELI_SAVERS

    st.markdown(
        f"""
        <div style='text-align:center;background:linear-gradient(135deg,#c0392b,#e74c3c);
                    border-radius:16px;padding:2rem 1rem;margin-bottom:1.5rem;color:white'>
          <div style='font-size:1.1rem;opacity:0.9;margin-bottom:0.4rem'>
            סך החסכונות של הציבור הישראלי המושקע בחברות הפוגעות בבעלי חיים
          </div>
          <div style='font-size:4rem;font-weight:800;letter-spacing:-1px;line-height:1.1'>
            {fmt_nis(total_nis)}
          </div>
          <div style='font-size:1rem;opacity:0.85;margin-top:0.6rem'>
            ממוצע לאדם: <strong>{fmt_nis(avg_per_person, decimals=0)}</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Impact calculator ────────────────────────────────────────────────────
    CURRENT_EXPLOIT_PCT = 6.56
    GRADE1_EXPLOIT_PCT  = CURRENT_EXPLOIT_PCT / 2

    VF_MEMBERS    = 6_500
    VF_FOLLOWERS  = 400_000

    # ── Impact equivalencies ─────────────────────────────────────────────────
    def _fmt_big(val):
        if val >= 1e12: return f"{val/1e12:.1f}T"
        if val >= 1e9:  return f"{val/1e9:.1f}B"
        if val >= 1e6:  return f"{val/1e6:.1f}M"
        if val >= 1e3:  return f"{val/1e3:.0f}K"
        return f"{int(val):,}"

    # Category fractions from 2025Q4 holdings data joined with CFI Animal Usage:
    #   Animal Testing 60.6%, Meat/Dairy/Eggs 14.4%, Leather/Hide/Fur 13.1%, other 12%
    # Food equivalencies (chickens, burgers) apply only to Meat/Dairy/Eggs companies.
    # Water/CO₂ apply to Meat + Leather (both categories require livestock).
    MEAT_PCT    = 0.144
    LIVESTOCK_PCT = 0.144 + 0.131  # Meat/Dairy/Eggs + Leather/Hide/Fur

    chickens     = total_nis * 0.057 * MEAT_PCT
    burgers_day  = total_nis * 0.005 * MEAT_PCT
    water_liters = total_nis * 1700  * LIVESTOCK_PCT
    co2_kg       = total_nis * 6     * LIVESTOCK_PCT

    st.markdown("**במונחים שאנחנו מבינים, זה שווה ערך ל:**")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric(
        "🐔 עופות ממומנים / שנה", _fmt_big(chickens),
        help="רק 14.4% מהסכום מושקע בחברות מזון מן החי (Meat/Dairy/Eggs) — מבוסס על הכנסות תעשיית החקלאות העולמית ו-80 מיליארד בעלי חיים שנשחטים מדי שנה.",
    )
    e1.caption(f"לחוסך הישראלי הממוצע: {_fmt_big(chickens / ISRAELI_SAVERS)} עופות/שנה")
    e2.metric(
        "🍔 המבורגרים בקר / יום", _fmt_big(burgers_day),
        help="רק 14.4% מהסכום מושקע בחברות בשר/חלב — מבוסס על שרשרת אספקת הבקר העולמית וצריכה של ~340 מיליון טון בקר בשנה.",
    )
    e2.caption(f"לחוסך הישראלי הממוצע: {_fmt_big(burgers_day / ISRAELI_SAVERS)} המבורגרים/יום")
    e3.metric(
        "💧 ליטרים של מים", _fmt_big(water_liters),
        help=f"27.5% מהסכום מושקע בחברות הדורשות בקר (מזון + עור) — מבוסס על ~15,400 ל׳ לק״ג בקר (UNESCO/WWF). שווה ל-{_fmt_big(water_liters / 2_500_000)} בריכות אולימפיות.",
    )
    e3.caption(f"לחוסך הישראלי הממוצע: {_fmt_big(water_liters / ISRAELI_SAVERS)} ליטרים")
    e4.metric(
        "🌍 ק״ג מקביל CO₂", _fmt_big(co2_kg),
        help=f"27.5% מהסכום מושקע בחברות הקשורות לגידול בקר — מבוסס על נתוני FAO (~7.1B טון CO₂ בשנה מבע״ח). שווה ל-{_fmt_big(co2_kg / 4_600)} שנות נסיעה ברכב ממוצע.",
    )
    e4.caption(f"לחוסך הישראלי הממוצע: {_fmt_big(co2_kg / ISRAELI_SAVERS)} ק״ג CO₂")

    st.markdown("---")
    st.subheader("כוח השינוי של קהילת ויגן פרנדלי")
    st.markdown(
        "מה יקרה אם חברי וחברות ויגן פרנדלי יגלו איפה הכסף שלהם מושקע?"
    )

    avg_savings = st.slider(
        "חיסכון ממוצע לאדם בכל הקופות (פנסיה, גמל, השתלמות, ביטוח)",
        min_value=100_000,
        max_value=1_500_000,
        value=500_000,
        step=50_000,
        format="₪%d",
    )

    current_per_person = avg_savings * CURRENT_EXPLOIT_PCT / 100
    clean_per_person   = avg_savings * GRADE1_EXPLOIT_PCT  / 100
    saving_per_person  = current_per_person - clean_per_person

    def _impact_card(group_name, n_people, color):
        cur   = n_people * current_per_person
        saved = n_people * saving_per_person

        # Community (annual for animals; daily for water/CO₂ as requested)
        chick_c   = _fmt_big(saved * 0.057 * MEAT_PCT)
        burg_c    = _fmt_big(saved * 0.005 * MEAT_PCT * 365)
        water_c   = _fmt_big(saved * 1700  * LIVESTOCK_PCT / 365)
        co2_km_c  = _fmt_big(saved * 6     * LIVESTOCK_PCT / 0.2 / 365)

        # Per-person (same units)
        chick_pp  = _fmt_big(saving_per_person * 0.057 * MEAT_PCT)
        burg_pp   = _fmt_big(saving_per_person * 0.005 * MEAT_PCT * 365)
        water_pp  = _fmt_big(saving_per_person * 1700  * LIVESTOCK_PCT / 365)
        co2_km_pp = _fmt_big(saving_per_person * 6     * LIVESTOCK_PCT / 0.2 / 365)

        return f"""
        <div style='background:{color};border-radius:14px;padding:1.5rem;color:white'>
          <div style='text-align:center;font-size:1.1rem;font-weight:700;margin-bottom:0.3rem'>{group_name}</div>
          <div style='text-align:center;font-size:0.8rem;opacity:0.75;margin-bottom:1rem'>
            מצב נוכחי: <strong>{fmt_nis(cur)}</strong> מושקעים בחברות מנצלות &nbsp;·&nbsp;
            הפחתה פוטנציאלית: <strong>{fmt_nis(saved)}</strong>
          </div>
          <div style='font-size:0.82rem;font-weight:700;text-align:center;opacity:0.9;margin-bottom:0.7rem'>
            ✨ מה הפחתה זו אומרת בפועל?
          </div>
          <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.75rem'>
            <div style='background:rgba(255,255,255,0.18);border-radius:10px;padding:1rem;text-align:center'>
              <div style='font-size:0.72rem;opacity:0.85;margin-bottom:0.5rem;font-weight:600'>💰 בשקלים</div>
              <div style='font-size:1.9rem;font-weight:800;line-height:1.1'>{fmt_nis(saved)}</div>
              <div style='font-size:0.68rem;opacity:0.7;margin-top:0.3rem'>יוצאים מהניצול</div>
            </div>
            <div style='background:rgba(255,255,255,0.18);border-radius:10px;padding:1rem'>
              <div style='font-size:0.72rem;opacity:0.85;margin-bottom:0.5rem;font-weight:600;text-align:center'>🌍 כקהילה</div>
              <div style='font-size:0.83rem;line-height:2'>
                🐔 {chick_c} עופות/שנה<br>
                🍔 {burg_c} המבורגרים/שנה<br>
                💧 {water_c} ל׳ ביום<br>
                🚗 {co2_km_c} ק״מ ביום
              </div>
            </div>
            <div style='background:rgba(255,255,255,0.18);border-radius:10px;padding:1rem'>
              <div style='font-size:0.72rem;opacity:0.85;margin-bottom:0.5rem;font-weight:600;text-align:center'>👤 לאדם</div>
              <div style='font-size:0.83rem;line-height:2'>
                🐔 {chick_pp} עופות/שנה<br>
                🍔 {burg_pp} המבורגרים/שנה<br>
                💧 {water_pp} ל׳ ביום<br>
                🚗 {co2_km_pp} ק״מ ביום
              </div>
            </div>
          </div>
        </div>
        """

    st.markdown(
        _impact_card("6,500 חברי ויגן אקטיב", VF_MEMBERS, "#8e44ad"),
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    st.markdown(
        _impact_card("400,000 עוקבי ויגן פרנדלי", VF_FOLLOWERS, "#2980b9"),
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<p style='color:#888;font-size:0.82rem;margin-top:0.6rem;text-align:right'>"
        f"הנחות: שיעור ניצול ממוצע היום — {CURRENT_EXPLOIT_PCT}% · "
        f"שיעור ניצול אחרי מעבר לקופה נקייה — {GRADE1_EXPLOIT_PCT:.2f}% (מחצית מהממוצע הנוכחי) · "
        f"חיסכון ממוצע לאדם — {fmt_nis(avg_savings)}</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── Investment houses by % (major only) ──────────────────────────────────
    st.subheader("מדרג בתי השקעות")
    name_col = "parent_short_name" if "parent_short_name" in parents.columns else "parent_company_legal_id"
    major_parents = parents[
        parents["_legal_id_str"].isin(MAJOR_PARENT_IDS) &
        parents["parent_vegan_flagged_pct"].notna()
    ].copy()
    # Aggregate in case same short_name has multiple legal IDs
    major_agg = (
        major_parents.groupby(name_col)["parent_vegan_flagged_pct"]
        .mean()
        .sort_values(ascending=True)
        .reset_index()
    )
    major_agg["pct_fmt"] = major_agg["parent_vegan_flagged_pct"].apply(lambda x: f"{x:.1f}%")

    fig2 = go.Figure(go.Bar(
        x=major_agg["parent_vegan_flagged_pct"],
        y=major_agg[name_col],
        orientation="h",
        text=major_agg["pct_fmt"],
        textposition="outside",
        marker_color=ANIMAL_RED,
    ))
    fig2.update_layout(
        xaxis=dict(title="% מהתיק המכוסה", ticksuffix="%"),
        yaxis=dict(title="", automargin=True),
        plot_bgcolor="white",
        height=420,
        margin=dict(l=120, r=80, t=10, b=40),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Methodology ───────────────────────────────────────────────────────────
    with st.expander("כיצד חושב המדד? על המתודולוגיה"):
        st.markdown(
            """
            <div dir="rtl" style="text-align:right">

            <p><strong>מקור הנתונים:</strong> <a href="https://crueltyfreeinvesting.org" target="_blank">CrueltyFreeInvesting.org</a> — ארגון עצמאי המפרסם רשימה של חברות ציבוריות הפועלות בניגוד לערכי הטבעונות.</p>

            <p><strong>שיטת הסיווג:</strong> עבור כל חברה נבדקו האתר הרשמי שלה ופרסומים בתקשורת. החברות שברשימה עושות שימוש בבעלי חיים באחת מהדרכים הבאות:</p>

            <ol style="padding-right:2rem;padding-left:0;margin-right:1rem">
              <li>ייצור או הגשה של <strong>מזון</strong> המכיל מוצרים מן החי (בשר, חלב, ביצים)</li>
              <li>ייצור או מכירה של <strong>ביגוד</strong> הכרוך בפגיעה בבעלי חיים (עור, פרווה)</li>
              <li>ייצור או מכירה של מוצרים הכרוכים ב<strong>ניסויים</strong> בבעלי חיים</li>
              <li><strong>גידול</strong> בעלי חיים לצורכי מזון ו/או ניסויים</li>
            </ol>

            <p><strong>ניתוח ההחזקות:</strong> אנחנו מנתחים לעומק את ההחזקות של כל קופה, כולל החזקות מורכבות דרך מדדים.</p>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Top 10 companies ──────────────────────────────────────────────────────
    st.subheader("10 החברות הפוגעות בבעלי חיים שמושקע בהן הסכום הגבוה ביותר")
    st.caption('סה"כ השקעה בכל חברה על ידי קופות הפנסיה * רבעון 4, 2025')

    top_df = pd.DataFrame(TOP_COMPANIES).sort_values("nis")
    top_df["nis_fmt"] = top_df["nis"].apply(fmt_nis)

    # Cap display at ₪3B; Teva (₪20B) and Amazon (₪8.5B) are truncated
    CAP = 3_000_000_000
    top_df["nis_display"] = top_df["nis"].clip(upper=CAP)
    top_df["is_truncated"] = top_df["nis"] > CAP
    top_df["bar_color"] = top_df["is_truncated"].map({True: "#c0392b", False: ANIMAL_RED})
    top_df["label"] = top_df.apply(
        lambda r: f"  {r['nis_fmt']}  ✂" if r["is_truncated"] else f"  {r['nis_fmt']}",
        axis=1,
    )

    fig_top = go.Figure(go.Bar(
        x=top_df["nis_display"],
        y=top_df["company"],
        orientation="h",
        text=top_df["label"],
        textposition="outside",
        cliponaxis=False,
        marker_color=top_df["bar_color"].tolist(),
        marker_pattern_shape=top_df["is_truncated"].map({True: "/", False: ""}).tolist(),
        marker_pattern_fgcolor="white",
        marker_pattern_size=6,
    ))
    fig_top.update_layout(
        xaxis=dict(range=[0, 3_500_000_000], title="₪", tickformat=",.0f"),
        yaxis=dict(title="", automargin=True),
        plot_bgcolor="white",
        height=420,
        margin=dict(l=210, r=20, t=10, b=10),
        showlegend=False,
    )
    # Dashed cutoff line at CAP
    fig_top.add_shape(
        type="line", xref="x", yref="paper",
        x0=CAP, x1=CAP, y0=0, y1=1,
        line=dict(color="#aaa", width=1.5, dash="dot"),
    )
    # Annotation next to the top-2 truncated bars
    fig_top.add_annotation(
        text="✂ בר מקוצר<br>הערך המלא<br>מוצג בתווית",
        xref="x", yref="paper",
        x=CAP * 1.42, y=0.88,
        xanchor="left", yanchor="middle",
        showarrow=False,
        font=dict(size=10, color="#888"),
        bgcolor="white",
        bordercolor="#ccc",
        borderwidth=1,
        borderpad=5,
        align="center",
    )
    st.plotly_chart(fig_top, use_container_width=True)

    # Company cards with logos
    for row in TOP_COMPANIES:
        logo_url = LOGO_URLS.get(row["ticker"], "")
        st.markdown(
            f"""
            <div style='display:flex;align-items:center;gap:1.2rem;padding:0.9rem 0;
                        border-bottom:1px solid #f0f0f0'>
              <img src='{logo_url}' width='40' height='40'
                   style='border-radius:8px;background:#f8f8f8;padding:4px;flex-shrink:0'
                   onerror="this.style.visibility='hidden'">
              <div style='flex-shrink:0;min-width:150px'>
                <div style='font-weight:700;font-size:1rem'>{row['company']}</div>
                <div style='color:{ANIMAL_RED};font-size:1.1rem;font-weight:800'>{fmt_nis(row['nis'])}</div>
                <div style='color:#999;font-size:0.78rem'>{row['category']}</div>
              </div>
              <div style='color:#555;font-size:0.93rem;border-right:3px solid {ANIMAL_RED};
                          padding-right:1rem;flex:1'>{row['desc']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Fund tables ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("דירוג טבעוני של כל קופות הפנסיה, הגמל, ההשתלמות והביטוח")
    sel_sub = st.multiselect(
        "סוג קופה",
        subsystems,
        default=[s for s in subsystems if s == "פנסיה מקיפה"],
        key="subsystem_filter",
    )
    filtered = graded[graded["subsystem"].isin(sel_sub)]

    # RTL column order: most contextual info on the right, details on the left
    display_cols_ltr = [c for c in [
        "fund_name", "parent_short_name", "subsystem", "vegan_grade",
        "vegan_flagged_pct", "vegan_flagged_sum", "top_vegan_flagged_holdings_str",
    ] if c in filtered.columns]
    display_cols = list(reversed(display_cols_ltr))

    COL_CONFIG = {
        "קופה": st.column_config.TextColumn("קופה"),
        "בית השקעות": st.column_config.TextColumn("בית השקעות"),
        "סוג": st.column_config.TextColumn("סוג"),
        "דירוג": st.column_config.NumberColumn("דירוג", format="%d"),
        "% חשיפה לפגיעה בבעלי חיים": st.column_config.NumberColumn("% חשיפה לפגיעה בבעלי חיים", format="%.1f%%"),
        "₪ מושקעים בפגיעה בבעלי חיים": st.column_config.NumberColumn("₪ מושקעים בפגיעה בבעלי חיים", format="₪%,.0f"),
        "חברות עם חשיפה גבוהה": st.column_config.TextColumn("חברות עם חשיפה גבוהה"),
    }

    def fmt_table(df):
        return df[display_cols].copy().rename(columns={
            "fund_name": "קופה",
            "parent_short_name": "בית השקעות",
            "subsystem": "סוג",
            "vegan_grade": "דירוג",
            "vegan_flagged_pct": "% חשיפה לפגיעה בבעלי חיים",
            "vegan_flagged_sum": "₪ מושקעים בפגיעה בבעלי חיים",
            "top_vegan_flagged_holdings_str": "חברות עם חשיפה גבוהה",
        })

    search = st.text_input("חיפוש לפי שם קופה", "")
    view = filtered if not search else filtered[
        filtered["fund_name"].str.contains(search, case=False, na=False)
    ]
    st.dataframe(
        fmt_table(view.sort_values("vegan_flagged_pct", ascending=False)),
        use_container_width=True, hide_index=True, column_config=COL_CONFIG,
    )

    st.markdown("---")
    st.markdown(
        "<p style='text-align:center;color:#aaa;font-size:0.85em'>"
        "נתונים: ENVA · סימון חברות: CrueltyFreeInvesting.org · תקופה: רבעון 4, 2025"
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
