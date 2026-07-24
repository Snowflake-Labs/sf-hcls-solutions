"""Field Targeting Intelligence Dashboard — Streamlit in Snowflake (SiS) version.

Read-only what-if scenario dashboard for Zenixar PsO field targeting.
Queries FIELD_TARGETING schema in SF_SOLUTIONS database.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from snowflake.snowpark.context import get_active_session

session = get_active_session()

st.set_page_config(
    page_title="Zenixar PsO | Field Targeting Intelligence",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    .main-header {
        background: linear-gradient(135deg, #0460A9 0%, #034B87 100%);
        padding: 1.5rem 2rem; border-radius: 8px;
        margin-bottom: 1.5rem; color: white;
    }
    .main-header h1 { color: white; font-size: 1.8rem; margin: 0; }
    .main-header p  { color: rgba(255,255,255,0.85); margin: 0.25rem 0 0 0; font-size: 0.95rem; }
    .section-header { border-left: 4px solid #0460A9; padding-left: 12px; margin: 1.5rem 0 1rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="main-header">
    <h1>Acme Pharma | Field Targeting Intelligence</h1>
    <p>Zenixar (zenimab) — Plaque Psoriasis — Q2 2026 Cycle</p>
</div>
""",
    unsafe_allow_html=True,
)

SCHEMA = "SF_SOLUTIONS.FIELD_TARGETING"
BRAND_BLUE = "#0460A9"
BRAND_RED = "#E40046"


def q(sql):
    """Run SQL query, return empty DataFrame if table missing."""
    try:
        return session.sql(sql).to_pandas()
    except Exception:
        return pd.DataFrame()


tab1, tab2, tab3 = st.tabs(["What-If Scenario", "Competitive Forces", "Recommendations"])

# =============================================================
# TAB 1: WHAT-IF SCENARIO
# =============================================================
with tab1:
    st.markdown(
        '<div class="section-header"><h3>Scenario: T1 = Top 15% of Prescribers</h3></div>', unsafe_allow_html=True
    )
    st.caption("Baseline: T1 = top 46% (current config) — Scenario: T1 restricted to top 15%")

    rx_impact = q(f"""
        SELECT
            ROUND(SUM(BASE_RX_LIFT), 0)::FLOAT AS BASELINE_RX,
            ROUND(SUM(COMP_RX_LIFT), 0)::FLOAT AS SCENARIO_RX,
            ROUND(SUM(RX_DELTA), 0)::FLOAT AS INCREMENTAL_RX,
            (SUM(COMP_CALLS) - SUM(BASE_CALLS))::FLOAT AS ADDITIONAL_CALLS
        FROM {SCHEMA}.SNAPSHOT_RX_IMPACT
    """)

    if not rx_impact.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Incremental TRx/Qtr", f"+{rx_impact['INCREMENTAL_RX'].iloc[0]:,.0f}")
        c2.metric("Additional Calls Required", f"{rx_impact['ADDITIONAL_CALLS'].iloc[0]:,.0f}")
        c3.metric("Scenario TRx/Qtr", f"{rx_impact['SCENARIO_RX'].iloc[0]:,.0f}")
        c4.metric("Territory Status", "50/50 Overloaded")
    else:
        st.info("Run the rules engine to populate scenario data. See NEXT_ACTIONS.md.")

    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Tier Distribution: Baseline vs Scenario")
        tier_dist = q(f"""
            WITH base_dist AS (
                SELECT REFINED_TIER AS TIER, COUNT(*) AS CNT
                FROM {SCHEMA}.RE_STEP4_REFINED_TIERED GROUP BY REFINED_TIER
            ), comp_dist AS (
                SELECT REFINED_TIER AS TIER, COUNT(*) AS CNT
                FROM {SCHEMA}.RE_STEP4_REFINED_TIERED_WHATIF GROUP BY REFINED_TIER
            )
            SELECT b.TIER, b.CNT AS BASELINE, c.CNT AS SCENARIO
            FROM base_dist b JOIN comp_dist c ON b.TIER = c.TIER
            ORDER BY CASE b.TIER WHEN 'T1' THEN 1 WHEN 'T2' THEN 2
                WHEN 'T3' THEN 3 WHEN 'T4' THEN 4 ELSE 5 END
        """)
        if not tier_dist.empty:
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    name="Baseline",
                    x=tier_dist["TIER"].tolist(),
                    y=tier_dist["BASELINE"].tolist(),
                    marker_color=BRAND_BLUE,
                )
            )
            fig.add_trace(
                go.Bar(
                    name="Scenario (T1@15%)",
                    x=tier_dist["TIER"].tolist(),
                    y=tier_dist["SCENARIO"].tolist(),
                    marker_color=BRAND_RED,
                )
            )
            fig.update_layout(
                barmode="group",
                height=380,
                margin=dict(t=30, b=40),
                legend=dict(orientation="h", y=1.1),
                yaxis_title="HCP Count",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No tier data yet. Run the rules engine first.")

    with col_right:
        st.subheader("Tier Movements (Top Flows)")
        movements = q(f"""
            SELECT
                BASELINE_TIER || ' to ' || COMPARISON_TIER AS MOVEMENT,
                HCP_COUNT::FLOAT AS COUNT,
                DIRECTION
            FROM {SCHEMA}.SNAPSHOT_TIER_MOVEMENT
            WHERE BASELINE_TIER != COMPARISON_TIER
            ORDER BY HCP_COUNT DESC LIMIT 8
        """)
        if not movements.empty:
            colors = ["#2E7D32" if d == "promoted" else "#C62828" for d in movements["DIRECTION"].tolist()]
            fig2 = go.Figure(
                go.Bar(
                    x=movements["COUNT"].tolist(),
                    y=movements["MOVEMENT"].tolist(),
                    orientation="h",
                    marker_color=colors,
                )
            )
            fig2.update_layout(
                height=380, margin=dict(t=30, l=100, b=40), xaxis_title="HCP Count", yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No movement data yet.")

    st.subheader("Top 10 Most-Affected Territories")
    terr = q(f"""
        SELECT TERR_ID, DELTA_T1::FLOAT AS DELTA_T1, DELTA_T2::FLOAT AS DELTA_T2,
            DELTA_T3::FLOAT AS DELTA_T3, BASE_TARGETS::FLOAT AS BASE_TARGETS,
            COMP_TARGETS::FLOAT AS COMP_TARGETS,
            (COMP_TARGETS - BASE_TARGETS)::FLOAT AS TARGET_DELTA,
            COMP_STATUS
        FROM {SCHEMA}.SNAPSHOT_TERRITORY_IMPACT
        ORDER BY ABS(COMP_TARGETS - BASE_TARGETS) DESC LIMIT 10
    """)
    if not terr.empty:
        st.dataframe(terr, use_container_width=True)
    else:
        st.info("No territory impact data yet.")

# =============================================================
# TAB 2: COMPETITIVE FORCES
# =============================================================
with tab2:
    st.markdown(
        '<div class="section-header"><h3>Competitive Landscape — Zenixar PsO</h3></div>', unsafe_allow_html=True
    )
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Competitor-A Opportunists by Tier")
        comp = q(f"""
            SELECT
                REFINED_TIER AS TIER,
                COUNT(*)::FLOAT AS TOTAL,
                SUM(CASE WHEN COMPETITOR_SEGMENT = 'COMPETITOR_A_OPPORTUNIST' THEN 1 ELSE 0 END)::FLOAT AS OPPORTUNISTS
            FROM {SCHEMA}.RE_STEP4_REFINED_TIERED
            GROUP BY REFINED_TIER
            ORDER BY CASE REFINED_TIER WHEN 'T1' THEN 1 WHEN 'T2' THEN 2
                WHEN 'T3' THEN 3 WHEN 'T4' THEN 4 ELSE 5 END
        """)
        if not comp.empty:
            non_opp = (comp["TOTAL"] - comp["OPPORTUNISTS"]).tolist()
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(name="Non-Opportunist", x=comp["TIER"].tolist(), y=non_opp, marker_color="#5BA4E5"))
            fig3.add_trace(
                go.Bar(
                    name="Competitor-A Opportunist",
                    x=comp["TIER"].tolist(),
                    y=comp["OPPORTUNISTS"].tolist(),
                    marker_color=BRAND_RED,
                )
            )
            fig3.update_layout(
                barmode="stack",
                height=350,
                margin=dict(t=30, b=40),
                legend=dict(orientation="h", y=1.12),
                yaxis_title="HCP Count",
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No competitive data yet. Run the rules engine first.")

    with col_b:
        st.subheader("GTN Score by Tier (Switch Dynamics)")
        gtn = q(f"""
            SELECT REFINED_TIER AS TIER, ROUND(AVG(GTN_NET_SCORE), 3)::FLOAT AS AVG_GTN
            FROM {SCHEMA}.RE_STEP4_REFINED_TIERED
            GROUP BY REFINED_TIER
            ORDER BY CASE REFINED_TIER WHEN 'T1' THEN 1 WHEN 'T2' THEN 2
                WHEN 'T3' THEN 3 WHEN 'T4' THEN 4 ELSE 5 END
        """)
        if not gtn.empty:
            fig4 = go.Figure(
                go.Bar(
                    x=gtn["TIER"].tolist(),
                    y=gtn["AVG_GTN"].tolist(),
                    marker_color=[BRAND_BLUE, BRAND_RED, "#5BA4E5", "#999", "#CCC"],
                )
            )
            fig4.add_hline(y=0.70, line_dash="dash", line_color="#666", annotation_text="High GTN (0.70)")
            fig4.update_layout(height=350, margin=dict(t=30, b=40), yaxis_title="Avg GTN Score", yaxis_range=[0, 1])
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No GTN data yet.")

    st.markdown("---")
    st.subheader("Field Intelligence from Call Notes")
    col_cn1, col_cn2 = st.columns(2)
    disp = q(f"""
        SELECT DISPOSITION, COUNT(*)::FLOAT AS COUNT,
            ROUND(AVG(SENTIMENT_SCORE::FLOAT), 3)::FLOAT AS AVG_SENTIMENT
        FROM {SCHEMA}.CALL_NOTES_ENRICHED
        GROUP BY DISPOSITION ORDER BY COUNT DESC
    """)
    if not disp.empty:
        colors_d = {"engaged": "#2E7D32", "resistant": "#C62828", "neutral": "#757575", "conversion_ready": BRAND_BLUE}
        mcolors = [colors_d.get(d, "#999") for d in disp["DISPOSITION"].tolist()]
        with col_cn1:
            fig5 = go.Figure(
                go.Bar(y=disp["DISPOSITION"].tolist(), x=disp["COUNT"].tolist(), orientation="h", marker_color=mcolors)
            )
            fig5.update_layout(height=280, margin=dict(t=20, b=30, l=130), xaxis_title="Notes")
            st.plotly_chart(fig5, use_container_width=True)
        with col_cn2:
            fig6 = go.Figure(
                go.Bar(
                    y=disp["DISPOSITION"].tolist(),
                    x=disp["AVG_SENTIMENT"].tolist(),
                    orientation="h",
                    marker_color=mcolors,
                )
            )
            fig6.add_vline(x=0, line_color="#1B1B1B", line_width=1)
            fig6.update_layout(height=280, margin=dict(t=20, b=30, l=130), xaxis_title="Avg Sentiment")
            st.plotly_chart(fig6, use_container_width=True)
    else:
        st.info("No call note data yet. Load data.sql first.")

# =============================================================
# TAB 3: RECOMMENDATIONS
# =============================================================
with tab3:
    st.markdown('<div class="section-header"><h3>AI-Driven Recommendations</h3></div>', unsafe_allow_html=True)

    st.markdown("""
    > **Scenario Verdict: Not Operationally Feasible**
    > Expanding T1 to top 15% generates incremental TRx/quarter but requires additional calls
    > across an already overloaded field force (all 50 territories exceed capacity).
    """)

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader("Recommended Actions")
        st.markdown("""
        **1. Reject T1 @ 15%** — Infeasible with current rep capacity.

        **2. Test Compromise: T1 @ 25-30%**
        - Captures high-value HCPs while reducing call burden
        - Expected to resolve some territory overload

        **3. Focus on Conversion-Ready HCPs**
        - HCPs flagged by Cortex AI as ready to switch
        - Prioritize these in T2 call plans for max ROI

        **4. Intensify T2 Competitive Effort**
        - T2 has highest Competitor-A opportunist penetration
        - Highest GTN scores — actively evaluating
        """)

    with col_r2:
        st.subheader("Rx Response Curve — ZENIXAR SC")
        rc = q(f"""
            SELECT TIER, CALLS::FLOAT AS CALLS, RX::FLOAT AS RX
            FROM {SCHEMA}.RESPONSE_CURVE
            WHERE PRODUCT_FAMILY = 'ZENIXAR SC'
            ORDER BY TIER, CALLS
        """)
        if not rc.empty:
            tier_colors = {"T1": BRAND_BLUE, "T2": BRAND_RED, "T3": "#5BA4E5", "T4": "#999", "NT": "#CCC"}
            fig7 = go.Figure()
            for tier in ["T1", "T2", "T3", "T4", "NT"]:
                df_t = rc[rc["TIER"] == tier]
                if not df_t.empty:
                    fig7.add_trace(
                        go.Scatter(
                            x=df_t["CALLS"].tolist(),
                            y=df_t["RX"].tolist(),
                            mode="lines+markers",
                            name=tier,
                            line=dict(color=tier_colors.get(tier, "#999"), width=2),
                            marker=dict(size=6),
                        )
                    )
            fig7.update_layout(
                height=320,
                margin=dict(t=30, b=40),
                xaxis_title="Calls per Quarter",
                yaxis_title="Incremental TRx",
                legend_title="Tier",
            )
            st.plotly_chart(fig7, use_container_width=True)
        else:
            st.info("No response curve data. Run setup.sql first.")

    st.markdown("""
    **Next Steps:**
    1. Run what-if at T1 = 25% using the rules engine
    2. Review territory-level workloads
    3. Export conversion-ready HCPs to CRM
    4. Schedule cycle-end review to compare actual Rx lift
    """)
