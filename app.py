"""
청라 식물공장 재배대별 온습도 도면 투영 시각화
실행: python app.py
접속: http://127.0.0.1:8050
"""

import json
import os
from datetime import date

import numpy as np
import pandas as pd
import plotly.colors as pc
import plotly.graph_objects as go
from dash import Dash, Input, Output, callback, ctx, dcc, html

# ─────────────────────────────────────────────
# 1. 데이터 로딩
# ─────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))

df_hourly   = pd.read_excel(os.path.join(HERE, "재배대간_시간대별_온습도_분포.xlsx"))
df_seasonal = pd.read_excel(os.path.join(HERE, "재배대간_계절별_시간대_온습도_분포.xlsx"))
df_summary  = pd.read_excel(
    os.path.join(HERE, "청라_재배대별_온습도.xlsx"),
    sheet_name="재배대별 평균 온습도 데이터",
)

df_hourly["재배대"]   = df_hourly["재배대"].astype(str)
df_seasonal["재배대"] = df_seasonal["재배대"].astype(str)
df_summary["재배대"]  = df_summary["재배대"].astype(str)

SEASONS = sorted(df_seasonal["계절"].unique().tolist())

# 재배 현황 JSON 로딩 (없으면 빈 dict)
BED_STATUS_PATH = os.path.join(HERE, "bed_status.json")
if os.path.exists(BED_STATUS_PATH):
    with open(BED_STATUS_PATH, encoding="utf-8") as f:
        BED_STATUS = json.load(f)
else:
    BED_STATUS = {}

# ─────────────────────────────────────────────
# 2. 도면 좌표 정의
# ─────────────────────────────────────────────
BED_LAYOUT = {
    "7":  (15, 10, 18, 6.5), "6":  (15, 18, 18, 6.5), "5":  (15, 26, 18, 6.5),
    "4":  (15, 34, 18, 6.5), "3":  (15, 42, 18, 6.5), "2":  (15, 50, 18, 6.5),
    "1":  (15, 58, 18, 6.5), "T3": (15, 68, 18, 6.5), "T2": (15, 76, 18, 6.5),
    "T1": (15, 84, 18, 6.5),
    "18": (65, 10, 18, 6.5), "17": (65, 18, 18, 6.5), "16": (65, 26, 18, 6.5),
    "15": (65, 34, 18, 6.5), "14": (65, 42, 18, 6.5), "13": (65, 50, 18, 6.5),
    "12": (65, 58, 18, 6.5), "11": (65, 66, 18, 6.5), "10": (65, 74, 18, 6.5),
    "9":  (65, 82, 18, 6.5), "8":  (65, 90, 18, 6.5),
    "19": (87, 22, 8,  13),  "20": (87, 38, 8,  13),
}

# ─────────────────────────────────────────────
# 3. 온습도 헬퍼 함수
# ─────────────────────────────────────────────
def get_values(mode, hour, season=None):
    col = "temp_mean" if mode == "temp" else "hum_mean"
    if season and season != "전체":
        df = df_seasonal[
            (df_seasonal["계절"] == season) & (df_seasonal["시간"] == hour)
        ]
    else:
        df = df_hourly[df_hourly["시간"] == hour]
    return dict(zip(df["재배대"].astype(str), df[col]))


def val_to_color(v, vmin, vmax, colorscale):
    t   = max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))
    r, g, b = pc.unlabel_rgb(pc.sample_colorscale(colorscale, [t])[0])
    return f"rgb({int(r)},{int(g)},{int(b)})"


# ─────────────────────────────────────────────
# 4. 온습도 도면 Figure 생성 (기존)
# ─────────────────────────────────────────────
def make_floor_figure(values, mode, hour, season_label):
    col_label  = "온도 (°C)" if mode == "temp" else "습도 (%)"
    colorscale = "RdYlGn_r" if mode == "temp" else "RdYlBu"
    vmin, vmax = (18.0, 21.5) if mode == "temp" else (74.0, 82.0)
    if values:
        vmin = min(vmin, min(values.values()))
        vmax = max(vmax, max(values.values()))

    fig = go.Figure()
    for x0, x1, color in [
        (5, 25,  "rgba(220,235,255,0.5)"),
        (55, 80, "rgba(220,255,235,0.5)"),
        (83, 92, "rgba(255,240,220,0.5)"),
    ]:
        fig.add_shape(
            type="rect", x0=x0, y0=6, x1=x1, y1=97,
            fillcolor=color, line=dict(color="#ccc", width=1),
        )

    for text, x, y in [
        ("Beds 1~7, T1~T3", 15, 3),
        ("Beds 8~20",        65, 3),
        ("19/20",            87, 3),
    ]:
        fig.add_annotation(
            x=x, y=y, text=text, showarrow=False,
            font=dict(size=9, color="#888"), align="center",
        )

    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(
            colorscale=colorscale, cmin=vmin, cmax=vmax, color=[vmin],
            colorbar=dict(
                title=dict(text=col_label, side="right"),
                thickness=16, len=0.7, tickfont=dict(size=11),
            ),
            showscale=True, size=0.1,
        ),
        hoverinfo="skip", showlegend=False,
    ))

    hover_x, hover_y, hover_text = [], [], []
    for bed_id, (cx, cy, w, h) in BED_LAYOUT.items():
        val  = values.get(bed_id)
        x0, x1_, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
        fill = val_to_color(val, vmin, vmax, colorscale) if val is not None else "#e0e0e0"
        tc   = "white" if val and (val - vmin) / (vmax - vmin) > 0.6 else "#222"

        fig.add_shape(
            type="rect", x0=x0, y0=y0, x1=x1_, y1=y1,
            fillcolor=fill, line=dict(color="white", width=1.5),
        )
        fig.add_annotation(
            x=cx, y=cy + 1.2, text=f"<b>{bed_id}</b>",
            showarrow=False, font=dict(size=11, color=tc),
        )
        fig.add_annotation(
            x=cx, y=cy - 1.5,
            text=f"{val:.1f}" if val else "N/A",
            showarrow=False, font=dict(size=9, color=tc),
        )
        if val:
            unit = "°C" if mode == "temp" else "%"
            hover_x.append(cx); hover_y.append(cy)
            hover_text.append(f"<b>재배대 {bed_id}</b><br>{col_label}: {val:.2f}{unit}")

    fig.add_trace(go.Scatter(
        x=hover_x, y=hover_y, mode="markers",
        marker=dict(size=32, opacity=0),
        text=hover_text,
        hovertemplate="%{text}<extra></extra>",
        showlegend=False,
        customdata=list(range(len(hover_x))),
    ))

    title_icon = "🌡" if mode == "temp" else "💧"
    fig.update_layout(
        title=dict(
            text=f"{title_icon} {'온도' if mode=='temp' else '습도'} 분포도 — {season_label}  {hour:02d}:00",
            font=dict(size=17, family="Malgun Gothic, sans-serif"),
            x=0.5, xanchor="center",
        ),
        xaxis=dict(range=[0, 100], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True),
        yaxis=dict(range=[0, 100], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True, scaleanchor="x"),
        plot_bgcolor="#f8f9fa", paper_bgcolor="#fff",
        margin=dict(l=10, r=90, t=55, b=10), height=680,
    )
    return fig


def make_time_series(bed_id, mode, season):
    col    = "temp_mean" if mode == "temp" else "hum_mean"
    col_sd = "temp_sd"   if mode == "temp" else "hum_sd"
    unit   = "°C"        if mode == "temp" else "%"
    if season and season != "전체":
        df = df_seasonal[
            (df_seasonal["재배대"] == bed_id) & (df_seasonal["계절"] == season)
        ].sort_values("시간")
    else:
        df = df_hourly[df_hourly["재배대"] == bed_id].sort_values("시간")
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    if col_sd in df.columns:
        sd = df[col_sd]
        fig.add_trace(go.Scatter(
            x=df["시간"].tolist() + df["시간"].tolist()[::-1],
            y=(df[col] + sd).tolist() + (df[col] - sd).tolist()[::-1],
            fill="toself", fillcolor="rgba(99,179,237,0.2)",
            line=dict(color="rgba(0,0,0,0)"), hoverinfo="skip", showlegend=False,
        ))
    fig.add_trace(go.Scatter(
        x=df["시간"], y=df[col], mode="lines+markers",
        line=dict(color="#3182CE", width=2.5),
        marker=dict(size=6, color="#2C5282"),
        hovertemplate=f"%{{x:02d}}:00 — %{{y:.2f}}{unit}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(
            text=f"재배대 {bed_id} 시간대별 {'온도' if mode=='temp' else '습도'}",
            font=dict(size=13), x=0.5, xanchor="center",
        ),
        xaxis=dict(title="시간", tickvals=list(range(0, 24, 3)),
                   ticktext=[f"{h:02d}h" for h in range(0, 24, 3)]),
        yaxis=dict(title=f"{unit}"),
        plot_bgcolor="#f8f9fa", paper_bgcolor="#fff",
        height=280, margin=dict(l=45, r=15, t=40, b=40),
        hovermode="x unified",
    )
    return fig


# ─────────────────────────────────────────────
# 5. 재배 현황 도면 Figure 생성 (신규)
# ─────────────────────────────────────────────
def make_cultivation_figure():
    today = date.today()
    fig   = go.Figure()

    # 구역 배경
    for x0, x1, color in [
        (5, 25,  "rgba(220,235,255,0.5)"),
        (55, 80, "rgba(220,255,235,0.5)"),
        (83, 92, "rgba(255,240,220,0.5)"),
    ]:
        fig.add_shape(
            type="rect", x0=x0, y0=6, x1=x1, y1=97,
            fillcolor=color, line=dict(color="#ccc", width=1),
        )

    for text, x, y in [
        ("Beds 1~7, T1~T3", 15, 3),
        ("Beds 8~18",        65, 3),
        ("19/20",            87, 3),
    ]:
        fig.add_annotation(
            x=x, y=y, text=text, showarrow=False,
            font=dict(size=9, color="#888"), align="center",
        )

    hover_x, hover_y, hover_text, hover_ids = [], [], [], []

    for bed_id, (cx, cy, w, h) in BED_LAYOUT.items():
        x0, x1_, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2

        # 이식대(T1~T3)는 회색 처리
        if bed_id.startswith("T"):
            fig.add_shape(
                type="rect", x0=x0, y0=y0, x1=x1_, y1=y1,
                fillcolor="#e0e0e0", line=dict(color="white", width=1.5),
            )
            fig.add_annotation(
                x=cx, y=cy, text=f"<b>{bed_id}</b>",
                showarrow=False, font=dict(size=10, color="#888"),
            )
            continue

        info  = BED_STATUS.get(str(int(bed_id)), BED_STATUS.get(bed_id))
        fill  = "#c8e6c9"  # 기본 연초록
        tc    = "#1b5e20"
        label = bed_id
        sub   = "정보없음"

        if info:
            plant_date = info.get("plant_date")
            seed_date  = info.get("seed_date")
            pred       = info.get("prediction")

            # 정식 후 경과일 기반 색상
            if plant_date:
                try:
                    pd_obj    = date.fromisoformat(plant_date)
                    plant_days = (today - pd_obj).days
                    # 0~7일: 연하늘, 8~14일: 연두, 15~25일: 초록, 26~35일: 노랑, 36+일: 주황
                    if plant_days <= 7:
                        fill, tc = "#e3f2fd", "#1565c0"
                    elif plant_days <= 14:
                        fill, tc = "#f1f8e9", "#33691e"
                    elif plant_days <= 25:
                        fill, tc = "#c8e6c9", "#1b5e20"
                    elif plant_days <= 35:
                        fill, tc = "#fff9c4", "#f57f17"
                    else:
                        fill, tc = "#ffe0b2", "#bf360c"
                    sub = f"정식 {plant_days}일차"
                except Exception:
                    sub = plant_date or "정보없음"

        fig.add_shape(
            type="rect", x0=x0, y0=y0, x1=x1_, y1=y1,
            fillcolor=fill, line=dict(color="white", width=1.5),
        )
        fig.add_annotation(
            x=cx, y=cy + 1.3, text=f"<b>{label}</b>",
            showarrow=False, font=dict(size=11, color=tc),
        )
        fig.add_annotation(
            x=cx, y=cy - 1.5, text=sub,
            showarrow=False, font=dict(size=8, color=tc),
        )

        # hover 텍스트
        if info:
            plant_date = info.get("plant_date", "-")
            seed_date  = info.get("seed_date",  "-")
            pred       = info.get("prediction")
            hover_body = (
                f"<b>재배대 {bed_id}번</b><br>"
                f"파종일: {seed_date}<br>"
                f"정식일: {plant_date}<br>"
            )
            if pred:
                bh = pred["varieties"].get("버터헤드", {})
                kp = pred["varieties"].get("카이피라", {})
                hover_body += (
                    f"파종후: {pred['seed_days']}일 / 정식후: {pred['plant_days']}일<br>"
                    f"<b>버터헤드</b> {bh.get('current_weight_g',0):.0f}g"
                    f" → 목표({bh.get('days_remaining','?')}일후)<br>"
                    f"<b>카이피라</b> {kp.get('current_weight_g',0):.0f}g"
                    f" → 목표({kp.get('days_remaining','?')}일후)"
                )
        else:
            hover_body = f"<b>재배대 {bed_id}번</b><br>데이터 없음"

        hover_x.append(cx); hover_y.append(cy)
        hover_text.append(hover_body)
        hover_ids.append(bed_id)

    fig.add_trace(go.Scatter(
        x=hover_x, y=hover_y, mode="markers",
        marker=dict(size=32, opacity=0),
        text=hover_text,
        hovertemplate="%{text}<extra></extra>",
        showlegend=False,
        customdata=hover_ids,
    ))

    updated = BED_STATUS.get("1", {}).get("updated_at", "미확인")
    fig.update_layout(
        title=dict(
            text=f"🌱 재배 현황 도면 — 기준일: {today} (최종갱신: {updated})",
            font=dict(size=16, family="Malgun Gothic, sans-serif"),
            x=0.5, xanchor="center",
        ),
        xaxis=dict(range=[0, 100], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True),
        yaxis=dict(range=[0, 100], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True, scaleanchor="x"),
        plot_bgcolor="#f8f9fa", paper_bgcolor="#fff",
        margin=dict(l=10, r=20, t=55, b=10), height=680,
    )
    return fig


def make_bed_detail_card(bed_id_str):
    """클릭된 재배대의 상세 정보 카드"""
    info = BED_STATUS.get(str(int(bed_id_str)), BED_STATUS.get(bed_id_str))
    if not info:
        return html.P("데이터 없음", style={"color": "#a0aec0"})

    today      = date.today()
    plant_date = info.get("plant_date", "-")
    seed_date  = info.get("seed_date",  "-")
    pred       = info.get("prediction")

    rows = [
        html.H3(
            f"🌿 재배대 {bed_id_str}번 상세",
            style={"fontSize": "14px", "margin": "0 0 12px", "fontWeight": "700"},
        ),
        _info_row("📅 파종일", seed_date),
        _info_row("🌱 정식일", plant_date),
    ]

    if pred:
        rows += [
            _info_row("🗓 파종후", f"{pred['seed_days']}일"),
            _info_row("📆 정식후", f"{pred['plant_days']}일"),
            html.Hr(style={"margin": "10px 0", "borderColor": "#e2e8f0"}),
            html.P("📊 수확 예측 (목표 130g)",
                   style={"fontWeight": "600", "fontSize": "12px", "margin": "6px 0"}),
        ]
        for variety in ["버터헤드", "카이피라"]:
            v = pred["varieties"].get(variety, {})
            cw  = v.get("current_weight_g", 0)
            dr  = v.get("days_remaining")
            td_ = v.get("target_date")
            color = "#38a169" if cw >= 130 else ("#dd6b20" if cw >= 100 else "#3182ce")
            rows.append(html.Div([
                html.Div(variety,
                         style={"fontWeight": "600", "fontSize": "12px", "color": "#4a5568"}),
                html.Div([
                    html.Span(f"현재 {cw:.0f}g",
                              style={"color": color, "fontWeight": "700", "fontSize": "13px"}),
                    html.Span(
                        f"  {'✅ 수확가능' if dr == 0 else f'→ {dr}일 후 ({td_})'}" if dr is not None else "",
                        style={"color": "#718096", "fontSize": "11px"},
                    ),
                ]),
            ], style={"padding": "5px 0", "borderBottom": "1px solid rgba(0,0,0,0.06)"}))

    return html.Div(rows)


def _info_row(label, value):
    return html.Div([
        html.Span(label,  style={"color": "#718096",  "fontSize": "12px"}),
        html.Span(str(value), style={"fontWeight": "600", "color": "#2d3748", "fontSize": "12px"}),
    ], style={"display": "flex", "justifyContent": "space-between",
              "padding": "4px 0", "borderBottom": "1px solid rgba(0,0,0,0.06)"})


# ─────────────────────────────────────────────
# 6. 범례 컴포넌트
# ─────────────────────────────────────────────
def make_legend():
    items = [
        ("#e3f2fd", "#1565c0", "0~7일  (정식 초기)"),
        ("#f1f8e9", "#33691e", "8~14일  (활착기)"),
        ("#c8e6c9", "#1b5e20", "15~25일 (생육기)"),
        ("#fff9c4", "#f57f17", "26~35일 (수확임박)"),
        ("#ffe0b2", "#bf360c", "36일+   (수확대기)"),
    ]
    return html.Div(
        [html.Span("■ 색상 범례:  ", style={"fontWeight": "600", "fontSize": "11px", "color": "#4a5568"})]
        + [
            html.Span(
                f"■ {label}  ",
                style={"fontSize": "11px", "color": tc, "background": bg,
                       "padding": "2px 6px", "borderRadius": "4px", "marginRight": "4px"},
            )
            for bg, tc, label in items
        ],
        style={"display": "flex", "flexWrap": "wrap", "alignItems": "center",
               "padding": "6px 24px", "background": "#fff",
               "borderBottom": "1px solid #e2e8f0", "gap": "4px"},
    )


# ─────────────────────────────────────────────
# 7. Dash 레이아웃
# ─────────────────────────────────────────────
app = Dash(__name__, title="청라 식물공장")

SEASON_OPTIONS = [{"label": "📅 전체 평균", "value": "전체"}] + [
    {"label": f"🍂 {s}", "value": s} for s in SEASONS
]

TAB_STYLE     = {"fontWeight": "600", "fontSize": "13px", "padding": "8px 20px"}
TAB_SEL_STYLE = {**TAB_STYLE, "borderTop": "3px solid #3182CE", "color": "#3182CE"}

app.layout = html.Div([
    # 헤더
    html.Div([
        html.H1("🌱 청라 식물공장 통합 모니터링",
                style={"margin": 0, "fontSize": "20px", "color": "#1a365d"}),
        html.P("온습도 분포 · 재배 현황 · 수확 예측",
               style={"margin": 0, "color": "#4a5568", "fontSize": "12px"}),
    ], style={"background": "linear-gradient(135deg,#ebf8ff,#e6fffa)",
              "padding": "14px 24px", "borderBottom": "2px solid #bee3f8"}),

    # 탭
    dcc.Tabs(id="main-tabs", value="tab-temp", children=[
        dcc.Tab(label="🌡 온도 분포",    value="tab-temp",  style=TAB_STYLE, selected_style=TAB_SEL_STYLE),
        dcc.Tab(label="💧 습도 분포",    value="tab-hum",   style=TAB_STYLE, selected_style=TAB_SEL_STYLE),
        dcc.Tab(label="🌿 재배 현황",    value="tab-cult",  style=TAB_STYLE, selected_style=TAB_SEL_STYLE),
    ], style={"background": "#fff", "borderBottom": "1px solid #e2e8f0"}),

    # 탭 콘텐츠
    html.Div(id="tab-content"),

    dcc.Store(id="selected-bed"),
    dcc.Store(id="selected-cult-bed"),
    dcc.Store(id="play-state", data=False),
], style={"fontFamily": "'Malgun Gothic',sans-serif", "background": "#f7fafc", "minHeight": "100vh"})


# ─────────────────────────────────────────────
# 8. 콜백
# ─────────────────────────────────────────────

@callback(Output("tab-content", "children"), Input("main-tabs", "value"))
def render_tab(tab):
    if tab in ("tab-temp", "tab-hum"):
        mode = "temp" if tab == "tab-temp" else "hum"
        return html.Div([
            # 컨트롤
            html.Div([
                html.Div([
                    html.Label("🍂 계절", style={"fontWeight": "600", "fontSize": "12px", "color": "#4a5568"}),
                    dcc.Dropdown(id="season-dd", options=SEASON_OPTIONS, value="전체",
                                 clearable=False, style={"width": "170px", "fontSize": "13px"}),
                ], style={"flex": "0 0 185px"}),
                html.Div([
                    html.Label(id="hour-label", children="🕐 시간: 12:00",
                               style={"fontWeight": "600", "fontSize": "12px", "color": "#4a5568"}),
                    dcc.Slider(id="hour-slider", min=0, max=23, step=1, value=12,
                               marks={h: f"{h:02d}" for h in range(0, 24, 3)},
                               tooltip={"placement": "bottom", "always_visible": False}),
                ], style={"flex": "1", "minWidth": "280px"}),
                html.Div([
                    html.Button("▶ 재생", id="play-btn", n_clicks=0,
                                style={"background": "#3182CE", "color": "white", "border": "none",
                                       "borderRadius": "6px", "padding": "8px 16px", "cursor": "pointer",
                                       "fontSize": "13px", "fontWeight": "600"}),
                    dcc.Interval(id="anim-interval", interval=800, n_intervals=0, disabled=True),
                ], style={"display": "flex", "alignItems": "flex-end"}),
            ], style={"display": "flex", "flexWrap": "wrap", "gap": "20px", "alignItems": "flex-end",
                      "padding": "14px 24px", "background": "#fff",
                      "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"}),

            dcc.Store(id="mode-store", data=mode),

            # 메인 영역
            html.Div([
                dcc.Graph(id="floor-graph", config={"displayModeBar": False}, style={"flex": "1"}),
                html.Div([
                    html.Div([
                        html.H3("📈 시간대별 추이", style={"fontSize": "13px", "margin": "0 0 8px", "fontWeight": "600"}),
                        html.P("도면에서 재배대를 클릭하세요", id="ts-hint",
                               style={"fontSize": "12px", "color": "#718096", "textAlign": "center", "marginTop": "30px"}),
                        dcc.Graph(id="ts-graph", config={"displayModeBar": False},
                                  style={"display": "none", "height": "280px"}),
                    ], style={"background": "#fff", "borderRadius": "8px", "border": "1px solid #e2e8f0",
                              "padding": "14px", "marginBottom": "12px"}),
                    html.Div(id="stats-card",
                             style={"background": "linear-gradient(135deg,#ebf8ff,#e6fffa)",
                                    "borderRadius": "8px", "border": "1px solid #bee3f8", "padding": "14px"}),
                ], style={"width": "300px", "flexShrink": 0}),
            ], style={"display": "flex", "gap": "14px", "padding": "14px 24px", "background": "#f7fafc"}),
        ])

    # 재배 현황 탭
    return html.Div([
        make_legend(),
        html.Div([
            dcc.Graph(
                id="cult-floor-graph",
                figure=make_cultivation_figure(),
                config={"displayModeBar": False},
                style={"flex": "1"},
            ),
            html.Div([
                html.Div(
                    id="cult-detail-card",
                    children=html.Div([
                        html.H3("🌿 재배대 상세 정보",
                                style={"fontSize": "13px", "margin": "0 0 8px", "fontWeight": "600"}),
                        html.P("도면에서 재배대를 클릭하세요",
                               style={"fontSize": "12px", "color": "#718096", "textAlign": "center", "marginTop": "30px"}),
                    ]),
                    style={"background": "#fff", "borderRadius": "8px", "border": "1px solid #e2e8f0",
                           "padding": "14px", "marginBottom": "12px"},
                ),
                # 전체 현황 요약
                html.Div(_make_summary_card(),
                         style={"background": "linear-gradient(135deg,#ebf8ff,#e6fffa)",
                                "borderRadius": "8px", "border": "1px solid #bee3f8", "padding": "14px"}),
            ], style={"width": "300px", "flexShrink": 0}),
        ], style={"display": "flex", "gap": "14px", "padding": "14px 24px", "background": "#f7fafc"}),
    ])


def _make_summary_card():
    today   = date.today()
    harvest_soon  = []
    harvest_ready = []

    for bid, info in BED_STATUS.items():
        pred = info.get("prediction")
        if not pred:
            continue
        for variety in ["버터헤드", "카이피라"]:
            v  = pred["varieties"].get(variety, {})
            dr = v.get("days_remaining")
            if dr is None:
                continue
            if dr == 0:
                harvest_ready.append(f"{bid}번({variety[:2]})")
            elif dr <= 5:
                harvest_soon.append(f"{bid}번({variety[:2]}, {dr}일후)")

    items = [
        html.H3("📊 수확 현황 요약",
                style={"fontSize": "13px", "margin": "0 0 10px", "fontWeight": "600"}),
        html.Div([
            html.Span("✅ 수확 가능", style={"color": "#718096", "fontSize": "12px"}),
            html.Span(
                ", ".join(harvest_ready) if harvest_ready else "없음",
                style={"fontWeight": "700", "color": "#38a169", "fontSize": "11px"},
            ),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "padding": "5px 0", "borderBottom": "1px solid rgba(0,0,0,0.06)"}),
        html.Div([
            html.Span("⏰ 5일내 수확", style={"color": "#718096", "fontSize": "12px"}),
            html.Span(
                ", ".join(harvest_soon) if harvest_soon else "없음",
                style={"fontWeight": "700", "color": "#dd6b20", "fontSize": "11px"},
            ),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "padding": "5px 0", "borderBottom": "1px solid rgba(0,0,0,0.06)"}),
        html.P(f"분석 기준: {today} | 목표중량: 130g",
               style={"fontSize": "10px", "color": "#a0aec0", "marginTop": "8px", "marginBottom": 0}),
    ]
    return items


# 온습도 탭 콜백
@callback(Output("hour-label", "children"), Input("hour-slider", "value"))
def upd_label(h):
    return f"🕐 시간: {h:02d}:00"


@callback(
    Output("floor-graph",  "figure"),
    Output("stats-card",   "children"),
    Input("mode-store",    "data"),
    Input("hour-slider",   "value"),
    Input("season-dd",     "value"),
)
def upd_floor(mode, hour, season):
    values     = get_values(mode, hour, season)
    fig        = make_floor_figure(values, mode, hour, season if season != "전체" else "전체 평균")
    unit       = "°C" if mode == "temp" else "%"
    if values:
        avg  = np.mean(list(values.values()))
        maxb = max(values, key=values.get)
        minb = min(values, key=values.get)
        card = html.Div([
            html.H3("📊 현재 통계",
                    style={"fontSize": "13px", "margin": "0 0 10px", "fontWeight": "600"}),
            *[html.Div([
                html.Span(lbl, style={"color": "#718096", "fontSize": "12px"}),
                html.Span(f"{v:.1f}{unit}", style={"fontWeight": "700", "color": c, "fontSize": "13px"}),
            ], style={"display": "flex", "justifyContent": "space-between",
                      "padding": "5px 0", "borderBottom": "1px solid rgba(0,0,0,0.06)"})
              for lbl, v, c in [
                  ("전체 평균", avg, "#2d3748"),
                  (f"최고 (재배대 {maxb})", values[maxb], "#e53e3e"),
                  (f"최저 (재배대 {minb})", values[minb], "#3182CE"),
              ]],
            html.P(f"측정 재배대: {len(values)}개",
                   style={"fontSize": "11px", "color": "#a0aec0", "marginTop": "8px", "marginBottom": 0}),
        ])
    else:
        card = html.P("데이터 없음", style={"color": "#a0aec0"})
    return fig, card


@callback(
    Output("selected-bed", "data"),
    Input("floor-graph", "clickData"),
    prevent_initial_call=True,
)
def store_click(cd):
    if cd and "points" in cd:
        txt = cd["points"][0].get("text", "")
        if "재배대" in txt:
            import re
            m = re.search(r"재배대 (\w+)", txt)
            if m:
                return m.group(1)
    return None


@callback(
    Output("ts-graph", "figure"),
    Output("ts-graph", "style"),
    Output("ts-hint",  "style"),
    Input("selected-bed", "data"),
    Input("mode-store",   "data"),
    Input("season-dd",    "value"),
)
def upd_ts(bed_id, mode, season):
    hidden    = {"display": "none"}
    show      = {"height": "280px"}
    hint_show = {"fontSize": "12px", "color": "#718096", "textAlign": "center", "marginTop": "30px"}
    if not bed_id:
        return go.Figure(), hidden, hint_show
    return make_time_series(bed_id, mode, season or "전체"), show, {"display": "none"}


@callback(
    Output("hour-slider", "value"),
    Output("anim-interval", "disabled"),
    Output("play-btn", "children"),
    Output("play-state", "data"),
    Input("play-btn",       "n_clicks"),
    Input("anim-interval",  "n_intervals"),
    Input("play-state",     "data"),
    Input("hour-slider",    "value"),
    prevent_initial_call=True,
)
def animate(n_clicks, n_intervals, playing, hour):
    tid = ctx.triggered_id
    if tid == "play-btn":
        new = not playing
        return hour, not new, ("⏸ 일시정지" if new else "▶ 재생"), new
    if tid == "anim-interval" and playing:
        return (hour + 1) % 24, False, "⏸ 일시정지", True
    return hour, not playing, ("⏸ 일시정지" if playing else "▶ 재생"), playing


# 재배 현황 탭 콜백
@callback(
    Output("cult-detail-card", "children"),
    Input("cult-floor-graph",  "clickData"),
    prevent_initial_call=True,
)
def cult_click(cd):
    default = html.Div([
        html.H3("🌿 재배대 상세 정보",
                style={"fontSize": "13px", "margin": "0 0 8px", "fontWeight": "600"}),
        html.P("도면에서 재배대를 클릭하세요",
               style={"fontSize": "12px", "color": "#718096", "textAlign": "center", "marginTop": "30px"}),
    ])
    if not cd or "points" not in cd:
        return default
    cdata = cd["points"][0].get("customdata")
    if not cdata or str(cdata).startswith("T"):
        return default
    return make_bed_detail_card(str(cdata))


# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 45)
    print("  청라 식물공장 통합 모니터링")
    print("  브라우저: http://127.0.0.1:8050")
    print("=" * 45 + "\n")
    app.run(debug=True, port=8050)
