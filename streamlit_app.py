"""
Vegan Friendly — Israeli Pension Fund Vegan Grade Dashboard (Hebrew)
Reads from GS_VEGAN_EXPORT Google Sheet (Funds + Parent Companies tabs).
"""
import json
import os

import pandas as pd
import plotly.express as px
import streamlit as st

SHEET_ID = "13TBGxhTo970evb5VCZ-hMDJzGKqY7SlDO5bV74rlSDo"

GRADE_COLORS = {1: "#2ecc71", 2: "#a8e063", 3: "#f5a623", 4: "#e67e22", 5: "#e74c3c"}
GRADE_LABELS = {1: "1 – מיטבי", 2: "2", 3: "3 – בינוני", 4: "4", 5: "5 – הגרוע ביותר"}
ANIMAL_RED = "#e74c3c"

# Top 10 animal-exploiting companies by total NIS invested across all funds (2025Q4)
# NIS values computed from holdings_flagged: SUM(value * Animal_Exploitation_flag) per figi_name_norm
# value column is in thousands ILS → multiplied by 1000 for actual ILS
TOP_COMPANIES = [
    {
        "company": "Teva Pharmaceutical",
        "ticker": "TEVA",
        "category": "ניסויים בבעלי חיים",
        "nis": 20_007_316_813,
        "desc": "טבע מפתחת ובודקת תרופות גנריות וייחודיות על בעלי חיים, ובכלל זה מחקרים על מודלים של מחלות דלקתיות.",
    },
    {
        "company": "Amazon.com",
        "ticker": "AMZN",
        "category": "מזון, עור, פרווה",
        "nis": 8_480_817_380,
        "desc": "אמזון מוכרת מוצרי בשר, חלב וביצים, פריטי עור ופרווה, ואף שיווקה פואה גרה מיצרנים שתועדה אצלם אכזריות כלפי בעלי חיים.",
    },
    {
        "company": "Eli Lilly",
        "ticker": "LLY",
        "category": "ניסויים בבעלי חיים",
        "nis": 2_246_871_530,
        "desc": "אלי לילי מבצעת ניסויים בבעלי חיים לצורך בדיקת בטיחות תרופותיה, בהתאם לדרישות ה-FDA.",
    },
    {
        "company": "AbbVie",
        "ticker": "ABBV",
        "category": "ניסויים בבעלי חיים",
        "nis": 1_065_820_751,
        "desc": "אבווי מבצעת ניסויים נרחבים בבעלי חיים במסגרת המחקר והפיתוח של מוצריה הביו-פרמצבטיים.",
    },
    {
        "company": "Walmart",
        "ticker": "WMT",
        "category": "מזון, עור, חיות מחמד",
        "nis": 929_573_593,
        "desc": "וולמארט מוכרת מזון מן החי, מוצרי עור ופרווה, וכן חיות מחמד בחלק מהסניפים.",
    },
    {
        "company": "Home Depot",
        "ticker": "HD",
        "category": "עור, מזון",
        "nis": 915_038_785,
        "desc": "הום דיפו מוכרת כפפות עבודה ופריטי עור נוספים, וכן מזון המכיל מוצרים מן החי.",
    },
    {
        "company": "Alibaba Group",
        "ticker": "BABA",
        "category": "מזון, עור, פרווה",
        "nis": 914_846_125,
        "desc": "עליבאבא משווקת מוצרי עור, פרווה ומזון מן החי דרך הפלטפורמות הדיגיטליות שלה.",
    },
    {
        "company": "Berkshire Hathaway",
        "ticker": "BRK",
        "category": "עור, מזון",
        "nis": 760_380_671,
        "desc": "ברקשייר מחזיקה בחברות בתחום ההנעלה מעור, ברשתות מזון (Dairy Queen, Kraft Heinz) ועוד.",
    },
    {
        "company": "Honeywell International",
        "ticker": "HON",
        "category": "עור",
        "nis": 711_754_291,
        "desc": "האניוול מייצרת ומשווקת נעליים מעור באמצעות חברת הבת Muck Boots.",
    },
    {
        "company": "Coca-Cola",
        "ticker": "KO",
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

    for col in ["parent_vegan_grade", "parent_vegan_flagged_pct", "parent_vegan_flagged_sum",
                "parent_ENVA_grade", "parent_flagged_pct"]:
        if col in parents.columns:
            parents[col] = pd.to_numeric(parents[col], errors="coerce")
    if "parent_vegan_flagged_sum" in parents.columns:
        parents["parent_vegan_flagged_sum"] = parents["parent_vegan_flagged_sum"] * 1000

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
        page_title="כספי הפנסיה שלך מממנים פגיעה בבעלי חיים",
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
        /* RTL for the entire app */
        html, body, [class*="css"] { direction: rtl; }
        .stApp { direction: rtl; }
        /* Sidebar RTL */
        section[data-testid="stSidebar"] { direction: rtl; }
        /* Main content blocks */
        .stMarkdown, .stText, .stCaption,
        div[data-testid="metric-container"],
        div[data-testid="stExpander"],
        .stTabs, .stDataFrame,
        label, p, h1, h2, h3, span { direction: rtl; text-align: right; }
        /* Keep charts LTR so axes render correctly */
        .js-plotly-plot { direction: ltr; }
        /* Metric value stays centered */
        div[data-testid="metric-container"] > div { text-align: right; }
        /* Tab labels */
        .stTabs [data-baseweb="tab-list"] { justify-content: flex-end; }
        /* Text inputs */
        input[type="text"] { direction: rtl; text-align: right; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.spinner("טוען נתונים..."):
        funds, parents = load_data()

    graded = funds[funds["vegan_grade"].notna()].copy()
    graded["vegan_grade_int"] = graded["vegan_grade"].astype(int)

    # ── Sidebar filters ───────────────────────────────────────────────────────
    st.sidebar.title("סינון")
    subsystems = sorted(graded["subsystem"].dropna().unique())
    sel_sub = st.sidebar.multiselect("סוג קופה", subsystems, default=subsystems)
    sel_grades = st.sidebar.multiselect(
        "דירוג טבעונות", [1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5],
        format_func=lambda g: GRADE_LABELS[g],
    )
    filtered = graded[
        graded["subsystem"].isin(sel_sub) & graded["vegan_grade_int"].isin(sel_grades)
    ]

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style='text-align:center;padding:1rem 0 0.5rem'>
          <h1 style='color:#2c3e50;margin-bottom:0.2rem'>🐄 כספי הפנסיה שלך מממנים פגיעה בבעלי חיים</h1>
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
    total_funds = len(graded)

    st.markdown(
        f"""
        <div style='text-align:center;background:linear-gradient(135deg,#c0392b,#e74c3c);
                    border-radius:16px;padding:2rem 1rem;margin-bottom:1.5rem;color:white'>
          <div style='font-size:1.1rem;opacity:0.9;margin-bottom:0.4rem'>
            סך הכסף שלכם המושקע בחברות הפוגעות בבעלי חיים
          </div>
          <div style='font-size:4rem;font-weight:800;letter-spacing:-1px;line-height:1.1'>
            {fmt_nis(total_nis)}
          </div>
          <div style='font-size:0.95rem;opacity:0.85;margin-top:0.5rem'>
            מתוך {total_funds:,} קופות שנבדקו · ממוצע של {total_nis/total_funds/1e6:.0f}M ש"ח לקופה
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Two charts ────────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("היקף ההשקעה בחברות הפוגעות בבעלי חיים לפי סוג קופה")
        by_sub = (
            graded.groupby("subsystem")["vegan_flagged_sum"]
            .sum().sort_values(ascending=False).reset_index()
        )
        by_sub["NIS_fmt"] = by_sub["vegan_flagged_sum"].apply(fmt_nis)
        fig1 = px.bar(
            by_sub, x="vegan_flagged_sum", y="subsystem",
            orientation="h", text="NIS_fmt",
            color_discrete_sequence=[ANIMAL_RED],
        )
        fig1.update_layout(showlegend=False, xaxis_title="₪", yaxis_title="",
                           plot_bgcolor="white", height=320)
        fig1.update_traces(textposition="outside")
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        st.subheader("בתי ההשקעות עם החשיפה הגבוהה ביותר לפגיעה בבעלי חיים")
        worst_parents = (
            parents[parents["parent_vegan_flagged_sum"].notna()]
            .sort_values("parent_vegan_flagged_sum", ascending=False)
            .head(12)
            .copy()
        )
        worst_parents["NIS_fmt"] = worst_parents["parent_vegan_flagged_sum"].apply(fmt_nis)
        name_col = "parent_short_name" if "parent_short_name" in worst_parents.columns else "parent_company_legal_id"
        fig2 = px.bar(
            worst_parents, x="parent_vegan_flagged_sum", y=name_col,
            orientation="h", text="NIS_fmt",
            color_discrete_sequence=[ANIMAL_RED],
        )
        fig2.update_layout(
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="₪", yaxis_title="",
            plot_bgcolor="white", height=320,
        )
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Methodology ───────────────────────────────────────────────────────────
    with st.expander("כיצד חושב המדד? על המתודולוגיה"):
        st.markdown(
            """
            **מקור הנתונים:** [CrueltyFreeInvesting.org](https://crueltyfreeinvesting.org) — ארגון עצמאי המפרסם רשימה של חברות ציבוריות הפועלות בניגוד לערכי הטבעונות.

            **שיטת הסיווג:** עבור כל חברה נבדקו האתר הרשמי שלה ופרסומים בתקשורת. החברות שברשימה עושות שימוש בבעלי חיים באחת מהדרכים הבאות:

            - ייצור או הגשה של **מזון** המכיל מוצרים מן החי (בשר, חלב, ביצים)
            - ייצור או מכירה של **ביגוד** הכרוך בפגיעה בבעלי חיים (עור, פרווה)
            - ייצור או מכירה של מוצרים הכרוכים ב**ניסויים** בבעלי חיים
            - **גידול** בעלי חיים לצורכי מזון ו/או ניסויים

            **חישוב הסכום:** עבור כל קופה סיכמנו את שווי ההחזקות בחברות המסווגות כפוגעות בבעלי חיים (בש"ח). שקלול סכום הכסף — ולא רק האחוז — מאפשר להבין את ההיקף הכספי האמיתי.
            """
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Top 10 companies ──────────────────────────────────────────────────────
    st.subheader("10 החברות הפוגעות בבעלי חיים שמושקע בהן הסכום הגבוה ביותר")
    st.caption("מחושב לפי סך הש\"ח המושקעים בכל חברה על ידי קופות הפנסיה הישראליות · רבעון 4, 2025")

    top_df = pd.DataFrame(TOP_COMPANIES)
    top_df["nis_fmt"] = top_df["nis"].apply(fmt_nis)

    fig_top = px.bar(
        top_df.sort_values("nis"), x="nis", y="company",
        orientation="h", text="nis_fmt",
        color_discrete_sequence=[ANIMAL_RED],
    )
    fig_top.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="₪", yaxis_title="",
        plot_bgcolor="white", height=360,
    )
    fig_top.update_traces(textposition="outside")
    st.plotly_chart(fig_top, use_container_width=True)

    for row in TOP_COMPANIES:
        with st.container():
            c1, c2 = st.columns([1, 5])
            with c1:
                st.metric(row["company"], fmt_nis(row["nis"]))
                st.caption(row["category"])
            with c2:
                st.markdown(
                    f"<div style='padding:0.6rem 0 0.6rem 1rem;border-left:3px solid {ANIMAL_RED};"
                    f"color:#555;font-size:0.95rem'>{row['desc']}</div>",
                    unsafe_allow_html=True,
                )
        st.divider()

    # ── Fund tables ───────────────────────────────────────────────────────────
    tab_worst, tab_best, tab_all = st.tabs(
        ["🔴 קופות בעייתיות (דירוג 4–5)", "🟢 קופות מיטביות (דירוג 1)", "כל הקופות"]
    )

    display_cols = [c for c in [
        "fund_name", "parent_short_name", "subsystem", "vegan_grade",
        "vegan_flagged_pct", "vegan_flagged_sum", "top_vegan_flagged_holdings_str",
    ] if c in filtered.columns]

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

    with tab_worst:
        worst_funds = filtered[filtered["vegan_grade_int"] >= 4].sort_values(
            "vegan_flagged_sum", ascending=False
        )
        st.caption(f"{len(worst_funds)} קופות")
        st.dataframe(fmt_table(worst_funds), use_container_width=True, hide_index=True, column_config=COL_CONFIG)

    with tab_best:
        best_funds = filtered[filtered["vegan_grade_int"] == 1].sort_values("vegan_flagged_sum")
        st.caption(f"{len(best_funds)} קופות — חשיפה נמוכה לפגיעה בבעלי חיים")
        st.dataframe(fmt_table(best_funds), use_container_width=True, hide_index=True, column_config=COL_CONFIG)

    with tab_all:
        search = st.text_input("חיפוש לפי שם קופה", "")
        view = filtered if not search else filtered[
            filtered["fund_name"].str.contains(search, case=False, na=False)
        ]
        st.caption(f"{len(view)} קופות")
        st.dataframe(
            fmt_table(view.sort_values("vegan_grade", ascending=False)),
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
