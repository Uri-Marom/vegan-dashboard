"""
Vegan Friendly — Israeli Pension Fund Vegan Grade Dashboard
Reads from GS_VEGAN_EXPORT Google Sheet (Funds + Parent Companies tabs).
Run locally: streamlit run vegan_dashboard.py
Deploy: Streamlit Community Cloud, set GOOGLE_SERVICE_ACCOUNT_JSON in secrets.
"""
import json
import os

import pandas as pd
import plotly.express as px
import streamlit as st

SHEET_ID = "13TBGxhTo970evb5VCZ-hMDJzGKqY7SlDO5bV74rlSDo"

GRADE_COLORS = {1: "#2ecc71", 2: "#a8e063", 3: "#f5a623", 4: "#e67e22", 5: "#e74c3c"}
GRADE_LABELS = {1: "1 – Best", 2: "2", 3: "3 – Mid", 4: "4", 5: "5 – Worst"}
ANIMAL_RED = "#e74c3c"


def _get_credentials():
    """Return google-auth Credentials, from st.secrets or env var."""
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    # Streamlit Cloud: secrets stored as TOML dict under [gcp_service_account]
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        return Credentials.from_service_account_info(info, scopes=scopes)

    # Streamlit Cloud: secrets stored as raw JSON string
    if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
        raw = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
        info = json.loads(raw) if isinstance(raw, str) else dict(raw)
        return Credentials.from_service_account_info(info, scopes=scopes)

    # Local: env var pointing to a file path or containing JSON
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if raw.strip().startswith("{"):
        return Credentials.from_service_account_info(json.loads(raw), scopes=scopes)
    if raw:
        return Credentials.from_service_account_file(raw, scopes=scopes)

    raise EnvironmentError("No Google credentials found. Set GOOGLE_SERVICE_ACCOUNT_JSON.")


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

    # DB stores values in thousands of ILS
    for col in ["vegan_flagged_sum"]:
        if col in funds.columns:
            funds[col] = funds[col] * 1000

    for col in ["parent_vegan_grade", "parent_vegan_flagged_pct", "parent_vegan_flagged_sum",
                "parent_ENVA_grade", "parent_flagged_pct"]:
        if col in parents.columns:
            parents[col] = pd.to_numeric(parents[col], errors="coerce")

    # DB stores values in thousands of ILS
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
        page_title="Vegan Money — Israeli Pension Funds",
        page_icon="🐄",
        layout="wide",
    )

    # load .env for local runs (ignored if package not installed)
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        load_dotenv(Path(__file__).parent / ".env")
    except Exception:
        pass

    with st.spinner("Loading data…"):
        funds, parents = load_data()

    graded = funds[funds["vegan_grade"].notna()].copy()
    graded["vegan_grade_int"] = graded["vegan_grade"].astype(int)

    # ── Sidebar filters ───────────────────────────────────────────────────────
    st.sidebar.title("Filters")
    subsystems = sorted(graded["subsystem"].dropna().unique())
    sel_sub = st.sidebar.multiselect("Fund type", subsystems, default=subsystems)
    sel_grades = st.sidebar.multiselect(
        "Vegan grade", [1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5],
        format_func=lambda g: GRADE_LABELS[g],
    )
    filtered = graded[
        graded["subsystem"].isin(sel_sub) & graded["vegan_grade_int"].isin(sel_grades)
    ]

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <h1 style='text-align:center;color:#2c3e50;margin-bottom:0'>
        🐄 Your Pension Funds Animal Exploitation
        </h1>
        <p style='text-align:center;color:#7f8c8d;font-size:1.1em;margin-top:4px'>
        Israeli pension &amp; savings funds graded 1–5 on vegan exposure · 2025 Q4
        </p><hr>
        """,
        unsafe_allow_html=True,
    )

    # ── Scorecards ────────────────────────────────────────────────────────────
    total_funds = len(graded)
    worst_pct = (graded["vegan_grade_int"] >= 4).mean() * 100
    total_nis = graded["vegan_flagged_sum"].sum()
    avg_grade = graded["vegan_grade"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Funds analysed", f"{total_funds:,}")
    c2.metric("Funds graded 4–5 (worst)", f"{worst_pct:.0f}%")
    c3.metric("Total NIS in animal exploitation", fmt_nis(total_nis))
    c4.metric("Average vegan grade", f"{avg_grade:.2f} / 5")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: grade distribution + NIS by subsystem ──────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Grade distribution")
        dist = graded["vegan_grade_int"].value_counts().sort_index().reset_index()
        dist.columns = ["Grade", "Funds"]
        dist["Label"] = dist["Grade"].map(GRADE_LABELS)
        fig = px.bar(
            dist, x="Label", y="Funds",
            color="Label",
            color_discrete_map={GRADE_LABELS[g]: GRADE_COLORS[g] for g in range(1, 6)},
            text="Funds",
        )
        fig.update_layout(showlegend=False, xaxis_title="Vegan grade",
                          plot_bgcolor="white", height=320)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("NIS in animal exploitation by fund type")
        by_sub = (
            graded.groupby("subsystem")["vegan_flagged_sum"]
            .sum().sort_values(ascending=False).reset_index()
        )
        by_sub["NIS_fmt"] = by_sub["vegan_flagged_sum"].apply(fmt_nis)
        fig2 = px.bar(
            by_sub, x="vegan_flagged_sum", y="subsystem",
            orientation="h", text="NIS_fmt",
            color_discrete_sequence=[ANIMAL_RED],
        )
        fig2.update_layout(showlegend=False, xaxis_title="NIS (₪)", yaxis_title="",
                           plot_bgcolor="white", height=320)
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Worst parent companies ─────────────────────────────────────────────────
    st.subheader("Worst investment houses by NIS in animal exploitation")
    worst_parents = (
        parents[parents["parent_vegan_flagged_sum"].notna()]
        .sort_values("parent_vegan_flagged_sum", ascending=False)
        .head(15)
    )
    worst_parents = worst_parents.copy()
    worst_parents["NIS_fmt"] = worst_parents["parent_vegan_flagged_sum"].apply(fmt_nis)
    worst_parents["Grade label"] = worst_parents["parent_vegan_grade"].apply(
        lambda g: GRADE_LABELS.get(int(g), str(g)) if pd.notna(g) else "—"
    )
    name_col = "parent_short_name" if "parent_short_name" in worst_parents.columns else "parent_company_legal_id"
    fig3 = px.bar(
        worst_parents, x="parent_vegan_flagged_sum", y=name_col,
        orientation="h", text="NIS_fmt",
        color="Grade label",
        color_discrete_map={GRADE_LABELS[g]: GRADE_COLORS[g] for g in range(1, 6)},
    )
    fig3.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="NIS (₪)", yaxis_title="",
        plot_bgcolor="white", height=440, legend_title="Grade",
    )
    fig3.update_traces(textposition="outside")
    st.plotly_chart(fig3, use_container_width=True)

    # ── Funds tables ──────────────────────────────────────────────────────────
    tab_worst, tab_best, tab_all = st.tabs(
        ["🔴 Worst funds (grade 4–5)", "🟢 Best funds (grade 1)", "All funds"]
    )

    display_cols = [c for c in [
        "fund_name", "parent_short_name", "subsystem", "vegan_grade",
        "vegan_flagged_pct", "vegan_flagged_sum", "top_vegan_flagged_holdings_str",
    ] if c in filtered.columns]

    def fmt_table(df):
        out = df[display_cols].copy()
        if "vegan_flagged_sum" in out.columns:
            out["vegan_flagged_sum"] = out["vegan_flagged_sum"].apply(fmt_nis)
        if "vegan_flagged_pct" in out.columns:
            out["vegan_flagged_pct"] = out["vegan_flagged_pct"].apply(
                lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
            )
        return out.rename(columns={
            "fund_name": "Fund",
            "parent_short_name": "Investment house",
            "subsystem": "Type",
            "vegan_grade": "Grade",
            "vegan_flagged_pct": "% animal exploitation",
            "vegan_flagged_sum": "NIS in animal exploitation",
            "top_vegan_flagged_holdings_str": "Top offending companies",
        })

    with tab_worst:
        worst_funds = filtered[filtered["vegan_grade_int"] >= 4].sort_values(
            "vegan_flagged_sum", ascending=False
        )
        st.caption(f"{len(worst_funds)} funds")
        st.dataframe(fmt_table(worst_funds), use_container_width=True, hide_index=True)

    with tab_best:
        best_funds = filtered[filtered["vegan_grade_int"] == 1].sort_values(
            "vegan_flagged_sum"
        )
        st.caption(f"{len(best_funds)} funds — lower NIS exposure, better for vegans")
        st.dataframe(fmt_table(best_funds), use_container_width=True, hide_index=True)

    with tab_all:
        search = st.text_input("Search fund name", "")
        view = filtered if not search else filtered[
            filtered["fund_name"].str.contains(search, case=False, na=False)
        ]
        st.caption(f"{len(view)} funds")
        st.dataframe(
            fmt_table(view.sort_values("vegan_grade", ascending=False)),
            use_container_width=True, hide_index=True,
        )

    st.markdown("---")
    st.markdown(
        "<p style='text-align:center;color:#aaa;font-size:0.85em'>"
        "Data: ENVA · Flags: CrueltyFreeInvesting.org · Period: 2025 Q4"
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
