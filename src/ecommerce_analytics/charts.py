"""Dependency-free SVG charts for the static report."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from .config import PALETTE, SEGMENT_ORDER, WEEKDAY_LABELS_ZH
from .svg import (
    circle,
    empty_chart,
    format_int,
    format_money,
    format_money_axis,
    format_month,
    format_pct,
    hatch_pattern,
    line,
    linear_gradient,
    path,
    polyline,
    rect,
    svg_document,
    text,
    truncate,
    write_svg,
)

INK = PALETTE["ink"]
MUTED = PALETTE["muted"]
LINE = PALETTE["line"]
GRID = PALETTE["grid"]
ACCENT = PALETTE["accent"]
TEAL = PALETTE["teal"]
GOLD = PALETTE["gold"]


def _header(title: str, subtitle: str, width: int, *, right_note: str | None = None) -> str:
    body = text(26, 30, title, size=17, weight=700)
    body += text(26, 50, subtitle, size=11, fill=MUTED)
    if right_note:
        body += text(width - 26, 30, right_note, size=10.5, fill=MUTED, anchor="end")
    return body


def _nice_scale(value: float, divisions: int = 4) -> tuple[float, float]:
    if value <= 0:
        return 1.0, 0.25
    raw = value / divisions
    magnitude = 10 ** math.floor(math.log10(raw))
    step = magnitude
    for multiplier in (1, 2, 2.5, 5, 10):
        step = multiplier * magnitude
        if raw <= step:
            break
    top = math.ceil(value / step) * step
    if top < value * 1.08:
        top += step
    return float(top), float(step)


def _ticks(top: float, step: float) -> list[float]:
    count = int(round(top / step))
    return [round(i * step, 6) for i in range(count + 1)]


def _blend(start: str, end: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    start = start.lstrip("#")
    end = end.lstrip("#")
    values = []
    for i in (0, 2, 4):
        a = int(start[i : i + 2], 16)
        b = int(end[i : i + 2], 16)
        values.append(round(a * (1 - t) + b * t))
    return "#" + "".join(f"{v:02x}" for v in values)


def _grid_y(
    left: float,
    right: float,
    top: float,
    bottom: float,
    ticks: list[float],
    maximum: float,
    formatter,
) -> str:
    body = ""
    for tick in ticks:
        y = bottom - (tick / maximum) * (bottom - top)
        body += line(left, y, right, y, stroke=GRID, stroke_width=1)
        body += text(left - 10, y + 4, formatter(tick), size=10, fill=MUTED, anchor="end")
    return body


def monthly_revenue_chart(monthly: pd.DataFrame, output: str | Path) -> str:
    width, height = 980, 440
    chart_id = "monthly"
    if monthly.empty:
        svg = empty_chart(width, height, title="月度销售趋势", message="没有可用的销售月份", chart_id=chart_id)
        write_svg(output, svg)
        return svg

    left, right, top, bottom_margin = 76, 66, 78, 70
    bottom = height - bottom_margin
    plot_w, plot_h = width - left - right, bottom - top
    n = len(monthly)
    slot = plot_w / n
    bar_w = min(48.0, slot * 0.60)
    max_rev, step_rev = _nice_scale(float(monthly["revenue"].max()), 4)
    rev_ticks = _ticks(max_rev, step_rev)
    max_orders, step_orders = _nice_scale(float(monthly["orders"].max()), 3)
    order_ticks = _ticks(max_orders, step_orders)

    body = _header(
        "月度销售趋势",
        "销售额（柱）与订单数（线）；虚线为 12 个完整月份均值，最后一个月份为部分月份",
        width,
        right_note="单位：英镑 / 订单",
    )
    body += _grid_y(left, width - right, top, bottom, rev_ticks, max_rev, format_money_axis)
    for tick in order_ticks:
        y = bottom - (tick / max_orders) * plot_h
        body += text(width - right + 10, y + 4, format_int(tick), size=9.5, fill=MUTED)

    avg_revenue = float(monthly.loc[~monthly["is_partial"], "revenue"].mean())
    avg_y = bottom - (avg_revenue / max_rev) * plot_h
    body += line(left, avg_y, width - right, avg_y, stroke=GOLD, stroke_width=1.2, dash="5 5", opacity=0.75)

    points: list[tuple[float, float]] = []
    peak_idx = 0
    peak_value = -1.0
    for i, row in enumerate(monthly.itertuples(index=False)):
        cx = left + slot * (i + 0.5)
        value = float(row.revenue)
        y = bottom - (value / max_rev) * plot_h
        fill = "url(#monthly-hatch)" if row.is_partial else "url(#monthly-fill)"
        body += rect(cx - bar_w / 2, y, bar_w, bottom - y, fill=fill, rx=2.5)
        if value > peak_value and not row.is_partial:
            peak_value = value
            peak_idx = i
        points.append((cx, bottom - (float(row.orders) / max_orders) * plot_h))
        body += text(
            cx,
            height - 46,
            format_month(row.invoice_month) + ("*" if row.is_partial else ""),
            size=9.5,
            fill=MUTED if not row.is_partial else ACCENT,
            anchor="middle",
            weight=600 if row.is_partial else 400,
        )

    body += polyline(points, stroke=TEAL, stroke_width=2.2, fill="none", opacity=0.95)
    for cx, cy in points:
        body += circle(cx, cy, 3.4, fill=PALETTE["card"], stroke=TEAL, stroke_width=1.8)

    peak_row = monthly.iloc[peak_idx]
    peak_cx = left + slot * (peak_idx + 0.5)
    peak_y = bottom - (float(peak_row["revenue"]) / max_rev) * plot_h
    body += line(peak_cx, peak_y - 8, peak_cx, peak_y - 30, stroke=ACCENT, stroke_width=1)
    body += circle(peak_cx, peak_y - 34, 2.5, fill=ACCENT)
    body += text(
        peak_cx,
        max(top + 6, peak_y - 54),
        f"11月峰值 {format_money(float(peak_row['revenue']))}",
        size=10,
        fill=ACCENT,
        anchor="middle",
        weight=700,
    )

    # Year markers below the month labels.
    year_2011_idx = [i for i, m in enumerate(monthly["invoice_month"]) if m.startswith("2011")]
    if year_2011_idx:
        x0 = left + slot * (min(year_2011_idx) + 0.5)
        x1 = left + slot * (max(year_2011_idx) + 0.5)
        body += text(left + slot * 0.5, height - 24, "2010", size=9.5, fill=MUTED, anchor="middle")
        body += text((x0 + x1) / 2, height - 24, "2011", size=9.5, fill=MUTED, anchor="middle")

    # Legend.
    body += rect(width - 270, 20, 9, 9, fill=ACCENT, rx=1)
    body += text(width - 256, 28, "销售额", size=9.5, fill=MUTED)
    body += line(width - 190, 24.5, width - 174, 24.5, stroke=TEAL, stroke_width=2.2)
    body += circle(width - 182, 24.5, 3, fill=PALETTE["card"], stroke=TEAL, stroke_width=1.6)
    body += text(width - 166, 28, "订单数", size=9.5, fill=MUTED)
    body += text(width - 26, height - 8, "* 12 月仅 9 天，不等同完整月份", size=9, fill=MUTED, anchor="end")

    defs = (
        linear_gradient("monthly-fill", [(0, "#D55A2A", 0.98), (1, "#E9A083", 0.93)])
        + hatch_pattern("monthly-hatch", ACCENT, "#F8E7DF")
    )
    svg = svg_document(
        width,
        height,
        body,
        title="月度销售趋势",
        description="柱状图显示每月销售额，折线显示订单数；11 月为销售峰值。",
        defs=defs,
        chart_id=chart_id,
    )
    write_svg(output, svg)
    return svg


def country_mix_chart(countries: pd.DataFrame, output: str | Path) -> str:
    width, height = 700, 390
    chart_id = "country"
    if countries.empty:
        svg = empty_chart(width, height, title="国家收入结构", message="没有可用数据", chart_id=chart_id)
        write_svg(output, svg)
        return svg

    top = countries.head(8).copy()
    other_revenue = float(countries.iloc[8:]["revenue"].sum()) if len(countries) > 8 else 0.0
    if other_revenue > 0:
        total = float(countries["revenue"].sum())
        top = pd.concat(
            [
                top,
                pd.DataFrame(
                    [
                        {
                            "country": "其他",
                            "revenue": other_revenue,
                            "share": other_revenue / total,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

    left, right, top_m, row_h = 168, 106, 76, 32
    plot_w = width - left - right
    body = _header("国家 / 地区收入结构", "按有效销售额排序；Top 8 与其他市场", width)
    max_share = float(top["share"].max())
    for i, row in enumerate(top.itertuples(index=False)):
        y = top_m + i * row_h
        bar_w = (float(row.share) / max_share) * plot_w
        color = ACCENT if i == 0 else (PALETTE["slate"] if row.country == "其他" else TEAL)
        body += text(left - 10, y + 14, truncate(row.country, 18), size=10.5, anchor="end", fill=INK)
        body += rect(left, y + 3, plot_w, 18, fill="#F6F2EC", rx=3)
        body += rect(left, y + 3, bar_w, 18, fill=color, rx=3, opacity=0.92)
        body += text(
            left + bar_w + 7,
            y + 16,
            f"{format_money(float(row.revenue))} · {format_pct(float(row.share))}",
            size=9.5,
            fill=MUTED,
        )
    body += text(
        width - 26,
        height - 16,
        f"共 {len(countries)} 个国家/地区；英国占 {format_pct(float(countries.iloc[0]['share']))}",
        size=9,
        fill=MUTED,
        anchor="end",
    )
    svg = svg_document(
        width,
        height,
        body,
        title="国家收入结构",
        description="横向条形图展示销售额最高的国家与地区，英国占据绝大部分收入。",
        chart_id=chart_id,
    )
    write_svg(output, svg)
    return svg


def pareto_chart(products: pd.DataFrame, output: str | Path) -> str:
    width, height = 700, 410
    chart_id = "pareto"
    if products.empty:
        svg = empty_chart(width, height, title="商品集中度", message="没有可用商品", chart_id=chart_id)
        write_svg(output, svg)
        return svg

    left, right, top, bottom_margin = 70, 34, 80, 58
    bottom = height - bottom_margin
    plot_w, plot_h = width - left - right, bottom - top

    x = np.r_[0.0, products["revenue_rank_pct"].to_numpy(dtype=float) * 100]
    y = np.r_[0.0, products["cumulative_share"].to_numpy(dtype=float) * 100]
    if len(x) > 260:
        keep = np.unique(np.linspace(0, len(x) - 1, 260).astype(int))
        keep = np.unique(np.r_[0, keep, len(x) - 1])
        x, y = x[keep], y[keep]

    body = _header("商品收入集中度", "Pareto 曲线：SKU 按销售额降序排列", width)
    for tick in (0, 20, 40, 60, 80, 100):
        gx = left + tick / 100 * plot_w
        gy = bottom - tick / 100 * plot_h
        body += line(left, gy, width - right, gy, stroke=GRID)
        body += text(left - 10, gy + 4, f"{tick}%", size=9.5, fill=MUTED, anchor="end")
        body += text(gx, bottom + 18, f"{tick}%", size=9.5, fill=MUTED, anchor="middle")

    curve_points = [(left + px / 100 * plot_w, bottom - py / 100 * plot_h) for px, py in zip(x, y)]
    area = (
        f"M {left},{bottom} "
        + " ".join(f"L {px:.2f},{py:.2f}" for px, py in curve_points)
        + f" L {left + plot_w},{bottom} Z"
    )
    body += path(area, fill="url(#pareto-fill)", opacity=0.55)
    body += polyline(curve_points, stroke=ACCENT, stroke_width=2.4)
    body += line(
        left,
        bottom - 0.8 * plot_h,
        width - right,
        bottom - 0.8 * plot_h,
        stroke=GOLD,
        stroke_width=1,
        dash="4 4",
        opacity=0.8,
    )
    body += line(
        left + 0.2 * plot_w,
        top,
        left + 0.2 * plot_w,
        bottom,
        stroke=GOLD,
        stroke_width=1,
        dash="4 4",
        opacity=0.8,
    )

    idx_20 = int(np.searchsorted(x, 20.0) - 1)
    idx_20 = max(0, min(idx_20, len(x) - 1))
    px = left + x[idx_20] / 100 * plot_w
    py = bottom - y[idx_20] / 100 * plot_h
    body += circle(px, py, 4.2, fill=ACCENT, stroke=PALETTE["card"], stroke_width=2)
    body += line(px + 8, py - 8, px + 55, py - 46, stroke=ACCENT, stroke_width=1)
    callout_x, callout_y = px + 58, py - 54
    body += text(
        callout_x,
        callout_y,
        f"Top 20% SKU → {format_pct(float(products.iloc[max(0, int(len(products) * 0.2) - 1)]['cumulative_share']))} 销售额",
        size=10.5,
        fill=INK,
        weight=700,
    )
    body += text(
        callout_x,
        callout_y + 16,
        f"80% 收入来自 {format_pct(float(products['cumulative_share'].lt(0.8).sum() + 1) / len(products))} 的 SKU",
        size=9.5,
        fill=MUTED,
    )
    body += text(26, height - 14, "SKU 累计占比（低 → 高）", size=9.5, fill=MUTED)
    body += text(left - 10, top - 12, "累计销售额占比", size=9.5, fill=MUTED, anchor="end")
    defs = linear_gradient("pareto-fill", [(0, ACCENT, 0.28), (1, ACCENT, 0.02)])
    svg = svg_document(
        width,
        height,
        body,
        title="商品收入集中度",
        description="Pareto 曲线显示头部 SKU 对销售额的贡献，20% 的 SKU 贡献约 80% 的销售额。",
        defs=defs,
        chart_id=chart_id,
    )
    write_svg(output, svg)
    return svg


def rfm_segment_chart(segments: pd.DataFrame, output: str | Path) -> str:
    width, height = 980, 474
    chart_id = "rfm"
    if segments.empty:
        svg = empty_chart(width, height, title="RFM 客群", message="没有可用客户", chart_id=chart_id)
        write_svg(output, svg)
        return svg

    left, right, top, row_h = 28, 28, 84, 43
    center = width / 2
    inner_gap = 78
    plot_w = center - inner_gap - left
    max_share = max(float(segments["customer_share"].max()), float(segments["revenue_share"].max()), 0.1)
    max_share = min(0.88, max_share * 1.28)

    body = _header("RFM 客群：人数与收入贡献", "客户数占比（左）与历史销售额占比（右）", width)
    body += text(center - inner_gap, 66, "客户数占比", size=9.5, fill=MUTED, anchor="end")
    body += text(center + inner_gap, 66, "收入贡献", size=9.5, fill=MUTED)

    ordered = segments.set_index("segment").reindex(SEGMENT_ORDER).dropna(how="all").reset_index()
    for i, row in enumerate(ordered.itertuples(index=False)):
        y = top + i * row_h
        cy = y + 13
        cust_w = float(row.customer_share) / max_share * plot_w
        rev_w = float(row.revenue_share) / max_share * plot_w
        color = row.color
        body += rect(center - inner_gap - cust_w, y + 4, cust_w, 18, fill=color, rx=3, opacity=0.45)
        body += rect(center + inner_gap, y + 4, rev_w, 18, fill=color, rx=3, opacity=0.95)
        body += text(
            center - inner_gap - cust_w - 6,
            cy,
            format_pct(float(row.customer_share)),
            size=9.5,
            fill=MUTED,
            anchor="end",
        )
        body += text(
            center + inner_gap + rev_w + 6,
            cy,
            format_pct(float(row.revenue_share)),
            size=9.5,
            fill=INK,
            weight=600,
        )
        body += text(center, cy - 1, row.segment_label, size=11.5, anchor="middle", weight=700)
        body += text(
            center,
            cy + 12,
            f"{format_int(int(row.customers))} 人",
            size=9,
            anchor="middle",
            fill=MUTED,
        )

    total_customers = int(segments["customers"].sum())
    body += text(
        width - 26,
        height - 16,
        f"客户口径：{format_int(total_customers)} 位有 CustomerID 的客户；颜色越深代表收入贡献",
        size=9,
        fill=MUTED,
        anchor="end",
    )
    svg = svg_document(
        width,
        height,
        body,
        title="RFM 客群结构",
        description="蝴蝶图对比各 RFM 客群的人数占比与收入贡献，冠军客户贡献了不成比例的收入。",
        chart_id=chart_id,
    )
    write_svg(output, svg)
    return svg


def lorenz_chart(lorenz: pd.DataFrame, top10_share: float, gini_value: float, output: str | Path) -> str:
    width, height = 700, 420
    chart_id = "lorenz"
    if lorenz.empty:
        svg = empty_chart(width, height, title="客户价值集中度", message="没有可用客户", chart_id=chart_id)
        write_svg(output, svg)
        return svg

    left, right, top, bottom_margin = 66, 32, 80, 58
    bottom = height - bottom_margin
    plot_w, plot_h = width - left - right, bottom - top

    body = _header("客户价值集中度", "Lorenz 曲线：越远离对角线，收入越集中", width)
    body += line(left, bottom, width - right, top, stroke=PALETTE["line"], stroke_width=1.2, dash="5 5")
    for tick in (0, 25, 50, 75, 100):
        gx = left + tick / 100 * plot_w
        gy = bottom - tick / 100 * plot_h
        body += line(left, gy, width - right, gy, stroke=GRID)
        body += text(left - 8, gy + 4, f"{tick}%", size=9, fill=MUTED, anchor="end")
        body += text(gx, bottom + 16, f"{tick}%", size=9, fill=MUTED, anchor="middle")

    points = [
        (left + float(row.customer_share) * plot_w, bottom - float(row.revenue_share) * plot_h)
        for row in lorenz.itertuples(index=False)
    ]
    body += polyline(points, stroke=ACCENT, stroke_width=2.2)
    area = (
        f"M {left},{bottom} "
        + " ".join(f"L {x:.2f},{y:.2f}" for x, y in points)
        + f" L {width - right},{top} Z"
    )
    body += path(area, fill=ACCENT, opacity=0.08)

    x90 = left + 0.90 * plot_w
    y90 = np.interp(0.90, lorenz["customer_share"].to_numpy(), lorenz["revenue_share"].to_numpy())
    y90_px = bottom - float(y90) * plot_h
    body += line(x90, bottom, x90, y90_px, stroke=GOLD, stroke_width=1, dash="4 4")
    body += line(left, y90_px, x90, y90_px, stroke=GOLD, stroke_width=1, dash="4 4")
    body += circle(x90, y90_px, 4, fill=GOLD, stroke=PALETTE["card"], stroke_width=2)
    body += text(
        x90 - 10,
        y90_px - 14,
        f"最高价值 10% 客户 → {format_pct(top10_share)} 收入",
        size=10,
        fill=INK,
        anchor="end",
        weight=700,
    )
    body += text(width - 26, 52, f"Gini = {gini_value:.2f}", size=10.5, fill=ACCENT, anchor="end", weight=700)
    body += text(26, height - 14, "客户累计占比（低 → 高）", size=9.5, fill=MUTED)
    body += text(left - 8, top - 12, "收入累计占比", size=9.5, fill=MUTED, anchor="end")
    svg = svg_document(
        width,
        height,
        body,
        title="客户价值集中度",
        description="Lorenz 曲线展示客户销售额集中度，最高价值 10% 客户贡献了显著比例的收入。",
        chart_id=chart_id,
    )
    write_svg(output, svg)
    return svg


def cohort_heatmap(rates: pd.DataFrame, sizes: pd.DataFrame, summary: dict, output: str | Path) -> str:
    width, height = 980, 500
    chart_id = "cohort"
    if rates.empty or 0 not in rates.columns:
        svg = empty_chart(
            width,
            height,
            title="首购 cohort 留存",
            message="样本不足以形成跨月 cohort",
            chart_id=chart_id,
        )
        write_svg(output, svg)
        return svg

    max_age = max((c for c in rates.columns if c > 0 and rates[c].notna().any()), default=0)
    columns = list(range(1, int(max_age) + 1))
    if not columns:
        svg = empty_chart(
            width,
            height,
            title="首购 cohort 留存",
            message="样本不足以形成跨月 cohort",
            chart_id=chart_id,
        )
        write_svg(output, svg)
        return svg

    left, right, top, row_h = 156, 30, 100, 32
    cell_w = (width - left - right) / len(columns)
    height = top + len(rates) * row_h + 80

    body = _header(
        "首购 cohort 留存率",
        "行 = 首购月；列 = 首购后第 N 个月仍下单的客户占比",
        width,
        right_note=f"M1 加权留存 {format_pct(float(summary.get('m1') or 0))}",
    )
    body += text(22, top - 14, "首购月 / 人数", size=9, fill=MUTED)
    for j, age in enumerate(columns):
        x = left + cell_w * (j + 0.5)
        body += text(x, top - 14, f"M{age}", size=9, fill=MUTED, anchor="middle")

    values = rates[columns].to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    vmax = max(0.35, float(finite.max()) if finite.size else 0.35)
    vmax = min(0.75, math.ceil(vmax * 20) / 20)

    size_map = sizes.set_index("cohort_month")["cohort_size"].to_dict()
    for i, cohort in enumerate(rates.index):
        y = top + i * row_h
        body += text(22, y + 20, str(cohort), size=9.5, weight=600)
        body += text(left - 12, y + 20, f"{format_int(size_map.get(cohort, 0))} 人", size=8.5, fill=MUTED, anchor="end")
        for j, age in enumerate(columns):
            x = left + j * cell_w
            value = rates.loc[cohort, age]
            if pd.isna(value):
                body += rect(x + 1, y + 2, cell_w - 2, row_h - 4, fill="#F8F5F0", rx=2)
                continue
            rate = float(value)
            t = rate / vmax if vmax else 0.0
            fill = _blend("#F6F1EA", "#0F766E", t)
            body += rect(x + 1, y + 2, cell_w - 2, row_h - 4, fill=fill, rx=2)
            body += text(
                x + cell_w / 2,
                y + 20,
                f"{rate * 100:.0f}%",
                size=9,
                fill="#FFFFFF" if t > 0.58 else INK,
                anchor="middle",
                weight=600,
            )

    legend_y = height - 34
    body += text(22, legend_y + 8, "留存率", size=8.5, fill=MUTED)
    legend_x, legend_w = 74, 160
    for k in range(10):
        body += rect(legend_x + k * (legend_w / 10), legend_y, legend_w / 10, 9, fill=_blend("#F6F1EA", "#0F766E", k / 9))
    body += text(legend_x, legend_y + 24, "0%", size=8, fill=MUTED)
    body += text(legend_x + legend_w / 2, legend_y + 24, format_pct(vmax / 2, 0), size=8, fill=MUTED, anchor="middle")
    body += text(legend_x + legend_w, legend_y + 24, format_pct(vmax, 0), size=8, fill=MUTED, anchor="end")
    body += text(
        width - 26,
        height - 14,
        "M0 恒为 100%，已省略；首购月为 2010-12 的 cohort 因左截断被排除",
        size=8.5,
        fill=MUTED,
        anchor="end",
    )
    svg = svg_document(
        width,
        height,
        body,
        title="首购 cohort 留存率",
        description="热力图展示每月首购客户在后续月份的留存率，颜色越深留存越高。",
        chart_id=chart_id,
    )
    write_svg(output, svg)
    return svg


def rhythm_heatmap(rhythm: pd.DataFrame, output: str | Path) -> str:
    width, height = 980, 390
    chart_id = "rhythm"
    if rhythm.empty:
        svg = empty_chart(width, height, title="下单时段", message="没有可用数据", chart_id=chart_id)
        write_svg(output, svg)
        return svg

    hours = list(range(8, 20))
    pivot = (
        rhythm.pivot(index="weekday_num", columns="hour", values="revenue")
        .reindex(index=range(7), columns=hours)
        .fillna(0)
    )
    max_rev = float(pivot.to_numpy().max())
    vmax = max(1.0, np.quantile(pivot.to_numpy()[pivot.to_numpy() > 0], 0.96) if max_rev > 0 else 1.0)

    left, right, top, row_h = 64, 28, 86, 34
    cell_w = (width - left - right) / len(hours)
    peak_pos = np.unravel_index(int(np.argmax(pivot.to_numpy())), pivot.shape)
    peak_day = WEEKDAY_LABELS_ZH[int(pivot.index[peak_pos[0]])]
    peak_hour = int(pivot.columns[peak_pos[1]])
    peak_value = float(pivot.iloc[peak_pos])

    body = _header(
        "下单时段热力图",
        "按星期与小时汇总有效销售额；颜色越深，销售越集中",
        width,
        right_note=f"峰值：{peak_day} {peak_hour}:00 · {format_money(peak_value)}",
    )
    for j, hour in enumerate(hours):
        body += text(left + cell_w * (j + 0.5), top - 12, f"{hour:02d}", size=9, fill=MUTED, anchor="middle")
    for i, day in enumerate(range(7)):
        y = top + i * row_h
        body += text(left - 12, y + 21, WEEKDAY_LABELS_ZH[day], size=9.5, fill=INK, anchor="end")
        for j, hour in enumerate(hours):
            x = left + j * cell_w
            value = float(pivot.loc[day, hour])
            t = value / vmax if vmax else 0.0
            fill = _blend("#FBF4EC", "#C2410C", min(1.0, t))
            body += rect(x + 1.5, y + 2, cell_w - 3, row_h - 4, fill=fill, rx=2)
            if value >= 5000:
                label = f"£{value / 1000:.0f}k" if value >= 1000 else f"£{value:.0f}"
                body += text(
                    x + cell_w / 2,
                    y + 21,
                    label,
                    size=7.5,
                    fill="#FFFFFF" if t > 0.55 else MUTED,
                    anchor="middle",
                )

    peak_x = left + peak_pos[1] * cell_w
    peak_y = top + peak_pos[0] * row_h
    body += rect(peak_x + 1.5, peak_y + 2, cell_w - 3, row_h - 4, fill="none", stroke=INK, stroke_width=1.6, rx=2)

    legend_y = height - 32
    body += text(22, legend_y + 8, "销售额", size=8.5, fill=MUTED)
    legend_x, legend_w = 68, 160
    for k in range(10):
        body += rect(legend_x + k * (legend_w / 10), legend_y, legend_w / 10, 8, fill=_blend("#FBF4EC", "#C2410C", k / 9))
    body += text(legend_x + legend_w + 10, legend_y + 8, f"高 {format_money(vmax)}", size=8, fill=MUTED)
    body += text(width - 26, height - 12, "周六无交易记录；周日晚间数据较少，不代表所有电商同理", size=8.5, fill=MUTED, anchor="end")
    svg = svg_document(
        width,
        height,
        body,
        title="下单时段热力图",
        description="按星期与小时展示销售额分布，工作日午间是订单高峰。",
        chart_id=chart_id,
    )
    write_svg(output, svg)
    return svg


def basket_rules_chart(rules: pd.DataFrame, output: str | Path) -> str:
    width, height = 980, 430
    chart_id = "basket"
    if rules.empty:
        svg = empty_chart(
            width,
            height,
            title="交叉销售组合",
            message="当前阈值下没有稳定的组合规则",
            chart_id=chart_id,
        )
        write_svg(output, svg)
        return svg

    left, right, top, row_h = 360, 82, 82, 46
    rows = rules.head(7)
    plot_w = width - left - right
    max_lift = max(float(rows["lift"].max()) * 1.12, 1.2)

    body = _header(
        "高提升度交叉销售组合",
        "Top 60 SKU 中，共同购买频率显著高于随机水平的商品对",
        width,
        right_note="Lift > 1 表示正向关联",
    )
    for i, row in enumerate(rows.itertuples(index=False)):
        y = top + i * row_h
        label = f"{truncate(row.antecedent, 25)} → {truncate(row.consequent, 25)}"
        body += text(left - 12, y + 16, label, size=9.4, fill=INK, anchor="end", weight=600)
        body += text(
            left - 12,
            y + 29,
            f"支持度 {format_pct(float(row.support))} · 置信度 {format_pct(float(row.confidence))} · 共现 {format_int(int(row.pair_orders))} 单",
            size=8.2,
            fill=MUTED,
            anchor="end",
        )
        bar_w = float(row.lift) / max_lift * plot_w
        body += rect(left, y + 6, plot_w, 17, fill="#F7F3ED", rx=3)
        body += rect(left, y + 6, bar_w, 17, fill="url(#basket-fill)", rx=3)
        body += text(left + bar_w + 8, y + 19, f"{float(row.lift):.1f}×", size=10, fill=ACCENT, weight=700)

    body += text(
        width - 26,
        height - 14,
        "指标口径：多商品购物篮；支持度 = 共现订单 / 购物篮数；仅展示 lift ≥ 1.2 的组合",
        size=8.5,
        fill=MUTED,
        anchor="end",
    )
    defs = linear_gradient("basket-fill", [(0, "#0F766E", 0.95), (1, "#2A9D8F", 0.8)])
    svg = svg_document(
        width,
        height,
        body,
        title="交叉销售组合",
        description="条形图展示提升度最高的商品组合，以及它们的支持度和置信度。",
        defs=defs,
        chart_id=chart_id,
    )
    write_svg(output, svg)
    return svg


def cancellation_chart(monthly: pd.DataFrame, overall_rate: float, output: str | Path) -> str:
    width, height = 700, 380
    chart_id = "cancel"
    if monthly.empty:
        svg = empty_chart(width, height, title="取消/退货", message="没有可用数据", chart_id=chart_id)
        write_svg(output, svg)
        return svg

    # The final partial month has disproportionate cancellation records
    # (refunds arrive after the sales window), so keep it out of the trend.
    complete = monthly.loc[~monthly["is_partial"]].reset_index(drop=True)
    if complete.empty:
        complete = monthly.copy()

    left, right, top, bottom_margin = 54, 26, 80, 58
    bottom = height - bottom_margin
    plot_w, plot_h = width - left - right, bottom - top
    values = complete["cancellation_rate"].to_numpy(dtype=float) * 100
    max_pct, step = _nice_scale(float(values.max()) if len(values) else 10, 3)
    ticks = _ticks(max_pct, step)
    n = len(complete)
    slot = plot_w / n
    bar_w = min(34.0, slot * 0.58)

    body = _header(
        "取消 / 退货金额占比",
        "取消发票金额 ÷ 当月有效销售额；已排除不完整的 12 月",
        width,
        right_note=f"全期 {format_pct(overall_rate)}",
    )
    for tick in ticks:
        y = bottom - tick / max_pct * plot_h
        body += line(left, y, width - right, y, stroke=GRID)
        body += text(left - 8, y + 4, f"{tick:.0f}%", size=9, fill=MUTED, anchor="end")

    for i, row in enumerate(complete.itertuples(index=False)):
        cx = left + slot * (i + 0.5)
        value = float(row.cancellation_rate) * 100
        y = bottom - value / max_pct * plot_h
        body += rect(cx - bar_w / 2, y, bar_w, bottom - y, fill=ACCENT, rx=2, opacity=0.78)
        body += text(
            cx,
            height - 34,
            format_month(row.invoice_month),
            size=8.8,
            fill=MUTED,
            anchor="middle",
        )

    overall_y = bottom - overall_rate * 100 / max_pct * plot_h
    body += line(left, overall_y, width - right, overall_y, stroke=INK, stroke_width=1, dash="3 3", opacity=0.65)
    body += text(width - 26, height - 8, "12 月仅 9 天，且有跨期退款，不纳入趋势", size=8, fill=MUTED, anchor="end")

    svg = svg_document(
        width,
        height,
        body,
        title="取消/退货金额占比",
        description="按月展示取消发票金额占销售额的比例，帮助识别退款与运营异常。",
        chart_id=chart_id,
    )
    write_svg(output, svg)
    return svg
