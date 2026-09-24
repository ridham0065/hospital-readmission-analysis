"""Build a self-contained interactive MIMIC-III 30-day readmissions dashboard.

Reads the five readmission CSVs in this folder and writes mimic_dashboard.html
to the Desktop (the parent folder of this project).
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "mimic_dashboard.html"

NAVY = "#1B2A4A"
NAVY_MID = "#2F4A7A"
INK = "#1F2937"
MUTED = "#6B7280"
GRID = "#E5E7EB"
FONT = "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
# Sequential navy ramp (light -> dark) for magnitude on the heatmap.
NAVY_SCALE = [
    [0.0, "#F1F4F9"],
    [0.25, "#C9D4E6"],
    [0.5, "#8AA0C6"],
    [0.75, "#46639A"],
    [1.0, "#16233F"],
]

DISCHARGE_LABELS = {
    "HOME HEALTH CARE": "Home Health Care",
    "HOME": "Home",
    "SNF": "Skilled Nursing Facility",
    "REHAB/DISTINCT PART HOSP": "Rehab / Distinct Part Hosp.",
    "LONG TERM CARE HOSPITAL": "Long-Term Care Hospital",
    "SHORT TERM HOSPITAL": "Short-Term Hospital",
    "LEFT AGAINST MEDICAL ADVI": "Left Against Medical Advice",
    "DISC-TRAN CANCER/CHLDRN H": "Transfer: Cancer/Children's Hosp.",
    "HOSPICE-HOME": "Hospice (Home)",
    "DISCH-TRAN TO PSYCH HOSP": "Transfer: Psych Hospital",
    "OTHER FACILITY": "Other Facility",
    "ICF": "Intermediate Care Facility",
    "HOME WITH HOME IV PROVIDR": "Home with IV Provider",
}

CONFIG = {"displaylogo": False, "responsive": True,
          "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}


def base_layout(fig, title, subtitle, height=440, margin=None, **kw):
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b><br><span style='font-size:12px;color:{MUTED}'>{subtitle}</span>",
            x=0.01, xanchor="left", y=0.96, font=dict(size=16, color=NAVY),
        ),
        font=dict(family=FONT, size=12, color=INK),
        paper_bgcolor="white", plot_bgcolor="white",
        height=height, margin={"l": 80, "r": 24, "t": 84, "b": 64, **(margin or {})},
        hoverlabel=dict(bgcolor="white", bordercolor=NAVY, font=dict(family=FONT, color=INK)),
        showlegend=False, **{"bargap": 0.28, **kw},
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=MUTED), automargin=False, title_standoff=12,
                     title_font=dict(color=MUTED, size=12))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(color=MUTED),
                     automargin=False, title_font=dict(color=MUTED, size=12))
    return fig


def insurance_chart(df):
    df = df.sort_values("total_readmissions", ascending=False)
    fig = go.Figure(go.Bar(
        x=df["INSURANCE"], y=df["total_readmissions"],
        marker=dict(color=NAVY, cornerradius=4),
        text=df["pct_of_readmissions"].map(lambda p: f"{p:.1f}%"),
        textposition="outside", textfont=dict(color=INK),
        customdata=df[["pct_of_readmissions", "readmission_rate"]],
        hovertemplate="<b>%{x}</b><br>Readmissions: %{y:,}<br>Share of readmissions: %{customdata[0]:.2f}%"
                      "<br>Readmission rate: %{customdata[1]:.2f}%<extra></extra>",
        cliponaxis=False,
    ))
    base_layout(fig, "30-Day Readmissions by Insurance Type",
                "Count of readmissions; bar labels show share of all readmissions")
    fig.update_xaxes(title_text="Insurance type")
    fig.update_yaxes(title_text="30-day readmissions", tickformat=",")
    return fig


def discharge_chart(df):
    df = df.sort_values("total_readmissions", ascending=False).copy()
    df["label"] = df["DISCHARGE_LOCATION"].map(DISCHARGE_LABELS).fillna(df["DISCHARGE_LOCATION"].str.title())
    fig = go.Figure(go.Bar(
        x=df["label"], y=df["total_readmissions"],
        marker=dict(color=NAVY, cornerradius=4),
        customdata=df[["DISCHARGE_LOCATION", "percentage"]],
        hovertemplate="<b>%{x}</b><br><span style='color:#6B7280'>%{customdata[0]}</span>"
                      "<br>Readmissions: %{y:,}<br>Share: %{customdata[1]:.2f}%<extra></extra>",
    ))
    base_layout(fig, "30-Day Readmissions by Discharge Location",
                "Where patients went after the index admission", height=480, margin={"b": 150})
    fig.update_xaxes(title_text="Discharge location", tickangle=-40)
    fig.update_yaxes(title_text="30-day readmissions", tickformat=",")
    return fig


def diagnosis_chart(df):
    df = df.sort_values("total_readmissions", ascending=True)
    fig = go.Figure(go.Bar(
        x=df["total_readmissions"], y=df["diagnosis_name"], orientation="h",
        marker=dict(color=NAVY, cornerradius=4),
        text=df["total_readmissions"], textposition="outside", textfont=dict(color=INK),
        hovertemplate="<b>%{y}</b><br>Readmissions: %{x:,}<extra></extra>",
        cliponaxis=False,
    ))
    base_layout(fig, "30-Day Readmissions by Diagnosis",
                "Top 10 primary diagnoses among readmitted patients", height=480, bargap=0.32, margin={"l": 190, "r": 40})
    fig.update_xaxes(title_text="30-day readmissions", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(title_text=None, showgrid=False)
    return fig


def risk_heatmap(master, diag_order):
    master = master.assign(day_weight=master["total_readmissions"] * master["avg_days_to_readmit"])
    g = master.groupby(["diagnosis_name", "INSURANCE"], as_index=False)[["total_readmissions", "day_weight"]].sum()
    g["avg_days"] = g["day_weight"] / g["total_readmissions"]

    ins_order = [i for i in ["Medicare", "Private", "Medicaid", "Government", "Self Pay"] if i in set(g["INSURANCE"])]
    counts = g.pivot(index="diagnosis_name", columns="INSURANCE", values="total_readmissions").reindex(
        index=diag_order, columns=ins_order)
    days = g.pivot(index="diagnosis_name", columns="INSURANCE", values="avg_days").reindex(
        index=diag_order, columns=ins_order)

    zmax = float(counts.max().max())
    fig = go.Figure(go.Heatmap(
        z=counts.values, x=ins_order, y=diag_order, customdata=days.values,
        colorscale=NAVY_SCALE, zmin=0, zmax=zmax, xgap=2, ygap=2,
        hovertemplate="<b>%{y}</b> · %{x}<br>Readmissions: %{z}<br>Avg days to readmit: %{customdata:.1f}<extra></extra>",
        hoverongaps=False,
        colorbar=dict(title=dict(text="Readmissions", side="right", font=dict(color=MUTED)),
                      thickness=12, outlinewidth=0, tickfont=dict(color=MUTED)),
    ))
    # Cell labels as annotations so ink can flip to white on dark cells.
    annotations = []
    for yi, dx in enumerate(diag_order):
        for xi, ins in enumerate(ins_order):
            v = counts.iloc[yi, xi]
            if pd.notna(v):
                annotations.append(dict(x=ins, y=dx, text=f"<b>{int(v)}</b>", showarrow=False,
                                        font=dict(size=12, color="white" if v > zmax * 0.45 else NAVY)))
    base_layout(fig, "Readmission Risk by Diagnosis and Insurance",
                "Readmissions per diagnosis × payer · blank = fewer than 5 cases<br>"
                "Hover a cell for average days to readmission",
                height=520, annotations=annotations, margin={"l": 190, "t": 100})
    fig.update_xaxes(title_text="Insurance type", side="bottom", showgrid=False)
    fig.update_yaxes(title_text=None, showgrid=False, autorange="reversed")
    fig.update_layout(plot_bgcolor="#FAFBFD")
    return fig


AGE_ORDER = ["Under 50", "50-65", "66-80", "Over 80"]


def age_chart(df):
    df = df.set_index("age_group").reindex(AGE_ORDER).reset_index()
    fig = go.Figure(go.Bar(
        x=df["age_group"], y=df["total_readmissions"],
        marker=dict(color=NAVY, cornerradius=4),
        text=df["percentage"].map(lambda p: f"{p:.1f}%"),
        textposition="outside", textfont=dict(color=INK),
        hovertemplate="<b>%{x}</b><br>Readmissions: %{y:,}<br>Share of readmissions: %{text}<extra></extra>",
        cliponaxis=False,
    ))
    base_layout(fig, "30-Day Readmissions by Age Group",
                "Age at admission, derived from patient date of birth")
    fig.update_xaxes(title_text="Age group")
    fig.update_yaxes(title_text="30-day readmissions", tickformat=",")
    return fig


def kpi(label, value, note):
    return (f'<div class="kpi"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>')


def main():
    ins = pd.read_csv(HERE / "readmissions_by_insurance.csv")
    dis = pd.read_csv(HERE / "readmissions_by_discharge.csv")
    diag = pd.read_csv(HERE / "readmissions_by_diagnosis.csv")
    master = pd.read_csv(HERE / "readmissions_master.csv")
    age = pd.read_csv(HERE / "readmissions_by_age.csv")

    total = int(ins["total_readmissions"].sum())
    top_ins = ins.loc[ins["total_readmissions"].idxmax()]
    top_dis = dis.loc[dis["total_readmissions"].idxmax()]
    wavg_days = (master["total_readmissions"] * master["avg_days_to_readmit"]).sum() / master["total_readmissions"].sum()
    diag_order = diag.sort_values("total_readmissions", ascending=False)["diagnosis_name"].tolist()

    figs = [
        insurance_chart(ins),
        discharge_chart(dis),
        diagnosis_chart(diag),
        risk_heatmap(master, diag_order),
        age_chart(age),
    ]
    divs = [
        f.to_html(full_html=False, include_plotlyjs=("inline" if i == 0 else False), config=CONFIG,
                  div_id=f"chart{i + 1}")
        for i, f in enumerate(figs)
    ]

    kpis = "".join([
        kpi("Total 30-day readmissions", f"{total:,}", "All payers"),
        kpi("Largest payer", top_ins["INSURANCE"], f"{top_ins['pct_of_readmissions']:.1f}% of readmissions"),
        kpi("Top discharge location", DISCHARGE_LABELS.get(top_dis["DISCHARGE_LOCATION"], top_dis["DISCHARGE_LOCATION"]),
            f"{top_dis['percentage']:.1f}% of readmissions"),
        kpi("Avg days to readmission", f"{wavg_days:.1f}", "Weighted, top diagnosis cohorts"),
    ])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MIMIC-III Readmissions Dashboard</title>
<style>
  :root {{ --navy:{NAVY}; --navy-mid:{NAVY_MID}; --ink:{INK}; --muted:{MUTED}; --line:{GRID}; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#ffffff; color:var(--ink); font-family:{FONT}; }}
  header {{ background:var(--navy); color:#fff; padding:28px 40px 24px; }}
  header h1 {{ margin:0; font-size:24px; font-weight:650; letter-spacing:-0.01em; }}
  header p {{ margin:6px 0 0; color:#C9D4E6; font-size:14px; }}
  main {{ max-width:1400px; margin:0 auto; padding:24px 40px 40px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:16px; margin-bottom:24px; }}
  .kpi {{ border:1px solid var(--line); border-top:3px solid var(--navy); border-radius:8px; padding:16px 18px; }}
  .kpi-label {{ font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }}
  .kpi-value {{ font-size:26px; font-weight:700; color:var(--navy); margin-top:6px; font-variant-numeric:tabular-nums; }}
  .kpi-note {{ font-size:12px; color:var(--muted); margin-top:4px; }}
  .grid {{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:24px; }}
  .card {{ border:1px solid var(--line); border-radius:10px; padding:8px; background:#fff;
           box-shadow:0 1px 2px rgba(16,24,40,.04); min-width:0; }}
  .card.wide {{ grid-column:1 / -1; }}
  footer {{ max-width:1400px; margin:0 auto; padding:0 40px 32px; font-size:12px; color:var(--muted); }}
  @media (max-width: 1000px) {{
    .grid {{ grid-template-columns:1fr; }}
    .kpis {{ grid-template-columns:repeat(2, minmax(0,1fr)); }}
  }}
  @media (max-width: 560px) {{
    header, main, footer {{ padding-left:16px; padding-right:16px; }}
    .kpis {{ grid-template-columns:1fr; }}
  }}
</style>
</head>
<body>
<header>
  <h1>30-Day Hospital Readmissions — Clinical Analytics</h1>
  <p>MIMIC-III Critical Care Database · Readmissions within 30 days of discharge by payer, discharge disposition and diagnosis</p>
</header>
<main>
  <section class="kpis">{kpis}</section>
  <section class="grid">
    <div class="card">{divs[0]}</div>
    <div class="card">{divs[1]}</div>
    <div class="card">{divs[2]}</div>
    <div class="card">{divs[3]}</div>
    <div class="card wide">{divs[4]}</div>
  </section>
</main>
<footer>Source: MIMIC-III v1.4 (PhysioNet). Hover any bar or cell for details; use the chart toolbar to zoom or download a PNG.</footer>
</body>
</html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
