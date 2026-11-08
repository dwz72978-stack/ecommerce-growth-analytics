"""Small dependency-free SVG toolkit used by the report charts."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Iterable, Sequence

from .config import FONT_STACK, PALETTE


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _attrs(**kwargs: object) -> str:
    parts: list[str] = []
    for key, value in kwargs.items():
        if value is None:
            continue
        name = key.rstrip("_").replace("_", "-")
        if isinstance(value, bool):
            if value:
                parts.append(name)
            continue
        parts.append(f'{name}="{esc(value)}"')
    return (" " + " ".join(parts)) if parts else ""


def text(
    x: float,
    y: float,
    content: object,
    *,
    size: float = 12,
    fill: str = PALETTE["ink"],
    anchor: str = "start",
    weight: int | str = 400,
    opacity: float = 1,
    letter_spacing: float | None = None,
    **kwargs: object,
) -> str:
    attrs = _attrs(
        x=round(x, 2),
        y=round(y, 2),
        font_size=size,
        fill=fill,
        text_anchor=anchor,
        font_weight=weight,
        opacity=opacity,
        letter_spacing=letter_spacing,
        **kwargs,
    )
    return f"<text{attrs}>{esc(content)}</text>"


def multiline_text(
    x: float,
    y: float,
    lines: Sequence[str],
    *,
    size: float = 12,
    fill: str = PALETTE["ink"],
    anchor: str = "start",
    weight: int = 400,
    line_height: float = 16,
    **kwargs: object,
) -> str:
    spans = "".join(
        f'<tspan x="{x}" dy="{0 if i == 0 else line_height}">{esc(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    attrs = _attrs(
        y=y,
        font_size=size,
        fill=fill,
        text_anchor=anchor,
        font_weight=weight,
        **kwargs,
    )
    return f"<text{attrs}>{spans}</text>"


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: str = "none",
    stroke: str | None = None,
    stroke_width: float = 1,
    rx: float = 0,
    opacity: float = 1,
    **kwargs: object,
) -> str:
    attrs = _attrs(
        x=round(x, 2),
        y=round(y, 2),
        width=round(max(width, 0), 2),
        height=round(max(height, 0), 2),
        rx=rx,
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
        opacity=opacity,
        **kwargs,
    )
    return f"<rect{attrs}/>"


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    stroke: str = PALETTE["line"],
    stroke_width: float = 1,
    dash: str | None = None,
    opacity: float = 1,
    **kwargs: object,
) -> str:
    attrs = _attrs(
        x1=round(x1, 2),
        y1=round(y1, 2),
        x2=round(x2, 2),
        y2=round(y2, 2),
        stroke=stroke,
        stroke_width=stroke_width,
        stroke_dasharray=dash,
        opacity=opacity,
        **kwargs,
    )
    return f"<line{attrs}/>"


def path(
    d: str,
    *,
    fill: str = "none",
    stroke: str | None = None,
    stroke_width: float = 1,
    opacity: float = 1,
    dash: str | None = None,
    **kwargs: object,
) -> str:
    attrs = _attrs(
        d=d,
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
        opacity=opacity,
        stroke_dasharray=dash,
        **kwargs,
    )
    return f"<path{attrs}/>"


def circle(
    cx: float,
    cy: float,
    r: float,
    *,
    fill: str = PALETTE["accent"],
    stroke: str | None = None,
    stroke_width: float = 1,
    opacity: float = 1,
    **kwargs: object,
) -> str:
    attrs = _attrs(
        cx=round(cx, 2),
        cy=round(cy, 2),
        r=r,
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
        opacity=opacity,
        **kwargs,
    )
    return f"<circle{attrs}/>"


def polyline(
    points: Iterable[tuple[float, float]],
    *,
    fill: str = "none",
    stroke: str = PALETTE["accent"],
    stroke_width: float = 2,
    **kwargs: object,
) -> str:
    pts = " ".join(f"{round(x, 2)},{round(y, 2)}" for x, y in points)
    attrs = _attrs(points=pts, fill=fill, stroke=stroke, stroke_width=stroke_width, **kwargs)
    return f"<polyline{attrs}/>"


def svg_document(
    width: int,
    height: int,
    body: str,
    *,
    title: str,
    description: str,
    defs: str = "",
    chart_id: str,
) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" role="img" aria-labelledby="{chart_id}-title {chart_id}-desc" '
        f'class="chart-svg" preserveAspectRatio="xMidYMid meet">'
        f'<title id="{chart_id}-title">{esc(title)}</title>'
        f'<desc id="{chart_id}-desc">{esc(description)}</desc>'
        f"<defs>{defs}</defs>"
        f'<rect width="{width}" height="{height}" fill="{PALETTE["card"]}"/>'
        f"{body}</svg>"
    )


def linear_gradient(gradient_id: str, stops: Sequence[tuple[float, str, float]]) -> str:
    stop_tags = "".join(
        f'<stop offset="{offset}" stop-color="{color}" stop-opacity="{opacity}"/>'
        for offset, color, opacity in stops
    )
    return (
        f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1">{stop_tags}</linearGradient>'
    )


def hatch_pattern(pattern_id: str, color: str, background: str = "#FFFFFF") -> str:
    return (
        f'<pattern id="{pattern_id}" width="7" height="7" patternUnits="userSpaceOnUse" '
        f'patternTransform="rotate(45)">'
        f'<rect width="7" height="7" fill="{background}"/>'
        f'<line x1="0" y1="0" x2="0" y2="7" stroke="{color}" stroke-width="3" opacity="0.55"/>'
        f"</pattern>"
    )


def write_svg(path: str | Path, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def format_money(value: float, *, decimals: int | None = None) -> str:
    value = float(value)
    if decimals is not None:
        return f"£{value:,.{decimals}f}"
    if abs(value) >= 1_000_000:
        return f"£{value / 1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"£{value / 1_000:,.1f}k"
    if abs(value) >= 10:
        return f"£{value:,.0f}"
    return f"£{value:,.2f}"


def format_money_axis(value: float) -> str:
    if value == 0:
        return "£0"
    if abs(value) >= 1_000_000:
        return f"£{value / 1_000_000:g}M"
    if abs(value) >= 1_000:
        return f"£{value / 1_000:g}k"
    return f"£{value:g}"


def format_pct(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


def format_int(value: float | int) -> str:
    return f"{int(round(value)):,}"


def format_month(value: str) -> str:
    year, month = value.split("-")
    return f"{int(month)}月"


def truncate(value: object, limit: int) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def empty_chart(
    width: int,
    height: int,
    *,
    title: str,
    message: str,
    chart_id: str,
) -> str:
    body = (
        text(width / 2, height / 2 - 8, "暂无可视化数据", size=16, anchor="middle", fill=PALETTE["muted"], weight=600)
        + text(width / 2, height / 2 + 18, message, size=12, anchor="middle", fill=PALETTE["muted"])
    )
    return svg_document(
        width,
        height,
        body,
        title=title,
        description=message,
        chart_id=chart_id,
    )
