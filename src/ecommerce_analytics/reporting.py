"""Static HTML report renderer.

The report is intentionally dependency-free: charts are inline SVG and the
whole page is a single file that can be hosted on GitHub Pages or opened
locally without a server.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Sequence

import pandas as pd

from .config import SEGMENT_DESCRIPTIONS, SEGMENT_LABELS_ZH
from .svg import format_int, format_money, format_pct

if TYPE_CHECKING:
    from .pipeline import AnalysisContext

REPO_URL = "https://github.com/dwz72978-stack/ecommerce-growth-analytics"
PROFILE_URL = "https://github.com/dwz72978-stack"
DATA_URL = "https://archive.ics.uci.edu/dataset/352/online+retail"
DOI_URL = "https://doi.org/10.24432/C5BW33"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def money(value: float, decimals: int | None = None) -> str:
    return format_money(float(value), decimals=decimals)


def money0(value: float) -> str:
    return f"£{float(value):,.0f}"


def pct(value: float | None, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return format_pct(float(value), decimals)


def num(value: float | int) -> str:
    return format_int(value)


def _table(
    headers: Sequence[str],
    rows: Iterable[Sequence[str]],
    *,
    aligns: Sequence[str] | None = None,
    compact: bool = False,
) -> str:
    aligns = aligns or ["left"] * len(headers)
    head = "".join(
        f'<th class="{aligns[i]}" scope="col">{esc(header)}</th>'
        for i, header in enumerate(headers)
    )
    body_rows = []
    for row in rows:
        cells = "".join(
            f'<td class="{aligns[i]}">{cell}</td>' for i, cell in enumerate(row)
        )
        body_rows.append(f"<tr>{cells}</tr>")
    table_class = "data-table compact" if compact else "data-table"
    return f'<div class="table-wrap"><table class="{table_class}"><thead><tr>{head}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>'


def _pill(text: str, tone: str = "neutral") -> str:
    return f'<span class="pill {tone}">{esc(text)}</span>'


def _figure(ctx: "AnalysisContext", key: str, number: int, caption: str) -> str:
    svg = ctx.figures.get(key, "")
    return (
        f'<figure class="chart-card">{svg}'
        f'<figcaption><span class="fig-no">图 {number}</span> {esc(caption)}</figcaption></figure>'
    )


def _kpi(label: str, value: str, note: str) -> str:
    return (
        f'<div class="kpi"><div class="kpi-label">{esc(label)}</div>'
        f'<div class="kpi-value">{esc(value)}</div>'
        f'<div class="kpi-note">{esc(note)}</div></div>'
    )


def _insight(number: str, metric: str, title: str, body: str) -> str:
    return (
        f'<article class="insight"><div class="insight-num">{esc(number)}</div>'
        f'<div><div class="insight-metric">{esc(metric)}</div>'
        f"<h3>{esc(title)}</h3><p>{body}</p></div></article>"
    )


def _section(
    section_id: str,
    number: str,
    kicker: str,
    title: str,
    lede: str,
    content: str,
) -> str:
    return (
        f'<section class="section" id="{section_id}">'
        f'<div class="section-head"><div class="section-num">{esc(number)}</div>'
        f'<div class="section-title"><div class="kicker">{esc(kicker)}</div>'
        f"<h2>{esc(title)}</h2></div></div>"
        f'<p class="section-lede">{lede}</p>{content}</section>'
    )


def _month_row(ctx: "AnalysisContext", month: str) -> pd.Series | None:
    monthly = ctx.bundle.monthly
    if monthly.empty:
        return None
    match = monthly.loc[monthly["invoice_month"] == month]
    return match.iloc[0] if not match.empty else None


def _segment(ctx: "AnalysisContext", name: str) -> pd.Series | None:
    if ctx.segments.empty:
        return None
    match = ctx.segments.loc[ctx.segments["segment"] == name]
    return match.iloc[0] if not match.empty else None


def _top_country(ctx: "AnalysisContext", name: str) -> pd.Series | None:
    if ctx.bundle.countries.empty:
        return None
    match = ctx.bundle.countries.loc[ctx.bundle.countries["country"] == name]
    return match.iloc[0] if not match.empty else None


def _build_hero(ctx: "AnalysisContext") -> str:
    k = ctx.kpis.values
    q = ctx.bundle.quality
    date_min = pd.Timestamp(k["date_min"]).strftime("%Y.%m")
    date_max = pd.Timestamp(k["date_max"]).strftime("%Y.%m")
    return f"""
<header class="hero">
  <div class="hero-grid">
    <div class="hero-copy">
      <div class="eyebrow">E-commerce analytics · Case study 01</div>
      <h1>一家英国礼品电商的<br><em>12 个月增长体检</em></h1>
      <p class="hero-sub">
        从 {num(q['source_rows'])} 行原始交易出发，拆解收入、商品、客户与留存：
        哪些月份真正赚钱，哪些客户撑起大盘，首购之后又漏在了哪里。
        所有图表由 Python 与手写 SVG 生成，结果可复现。
      </p>
      <div class="hero-meta">
        <span class="chip">2010.12 — 2011.12</span>
        <span class="chip">{num(q['clean_rows'])} 行去重交易</span>
        <span class="chip">{num(q['countries'])} 个国家 / 地区</span>
        <span class="chip">GBP · 有效销售口径</span>
      </div>
      <div class="cta-row">
        <a class="btn primary" href="#insights">阅读结论 <span aria-hidden="true">↓</span></a>
        <a class="btn ghost" href="{REPO_URL}" target="_blank" rel="noreferrer">GitHub 仓库 <span aria-hidden="true">↗</span></a>
      </div>
    </div>
    <aside class="snapshot" aria-label="数据快照">
      <div class="snap-top"><span>DATA SNAPSHOT</span><span>UCI / 352</span></div>
      <div class="snap-big">{money(k['total_revenue'])}</div>
      <div class="snap-caption">有效销售额 · {date_min} – {date_max}</div>
      <div class="snap-grid">
        <div><strong>{num(k['total_orders'])}</strong><span>订单</span></div>
        <div><strong>{num(k['total_customers'])}</strong><span>有 ID 客户</span></div>
        <div><strong>{pct(k['repeat_rate'], 1)}</strong><span>复购率</span></div>
        <div><strong>{pct(k['cancellation_rate'], 1)}</strong><span>取消金额占比</span></div>
      </div>
      <div class="snap-foot">CC BY 4.0 · 已匿名化 · 无个人信息</div>
    </aside>
  </div>
</header>
<div class="kpi-strip">
  {_kpi("有效销售额", money(k['total_revenue']), "剔除取消、负数量与零价")}
  {_kpi("订单数", num(k['total_orders']), f"客单价中位数 {money0(k['median_order_value'])}")}
  {_kpi("客户数", num(k['total_customers']), "仅统计有 CustomerID")}
  {_kpi("平均客单价", money(k['aov'], 0), f"P90 订单 {money0(k['p90_order_value'])}")}
  {_kpi("复购率", pct(k['repeat_rate'], 1), f"{num(k['repeat_customers'])} 位客户复购")}
  {_kpi("取消 / 退货", pct(k['cancellation_rate'], 1), f"{money0(k['cancellation_value'])} 取消金额")}
</div>
"""


def _build_insights(ctx: "AnalysisContext") -> str:
    k = ctx.kpis.values
    champion = _segment(ctx, "Champions")
    at_risk = _segment(ctx, "At Risk")
    hv = ctx.high_value
    peak = money(k["peak_revenue"])
    insight_1 = _insight(
        "01",
        f"{k['peak_multiple']:.2f}×",
        "Q4 是全年发动机，但不是均匀放量",
        f"11 月销售额 {peak}，相当于 12 个完整月份均值的 {k['peak_multiple']:.2f} 倍；"
        "9 月环比 +39.4%、10 月 +9.0%、11 月 +30.6%。增长在 9 月已经启动，"
        "备货、内容和投放预算都应前移，而不是等到 11 月才加码。",
    )
    insight_2 = _insight(
        "02",
        pct(k["top10_customer_share"], 1),
        "收入高度集中，头部客户需要被“经营”",
        f"最高价值 10% 客户贡献 {pct(k['top10_customer_share'])} 的有效销售额，"
        f"Gini 系数 {k['customer_gini']:.2f}。冠军客户 {num(int(champion['customers'])) if champion is not None else '—'} 人，"
        f"占客户数 {pct(float(champion['customer_share'])) if champion is not None else '—'}，"
        f"却贡献 {pct(float(champion['revenue_share'])) if champion is not None else '—'} 的收入。"
        "这更像批发型客户结构，普惠式折扣的边际收益有限。",
    )
    insight_3 = _insight(
        "03",
        pct(ctx.cohorts.summary.get("m1") or 0, 1),
        "复购率不低，但首购后的第一个月是漏点",
        f"整体复购率 {pct(k['repeat_rate'])}，复购客户贡献了 {pct(k['repeat_revenue_share'])} 的已识别客户收入；"
        f"但 cohort 的 M1 加权留存只有 {pct(ctx.cohorts.summary.get('m1') or 0, 1)}，"
        f"M3 为 {pct(ctx.cohorts.summary.get('m3') or 0, 1)}，M6 为 {pct(ctx.cohorts.summary.get('m6') or 0, 1)}。"
        "首购后 30 天的欢迎旅程，比年底一次性大促更值得投入。",
    )
    insight_4 = _insight(
        "04",
        pct(k["top20_sku_share"], 1),
        "商品是“中等头部 + 很长长尾”",
        f"Top 20% 的 SKU 贡献 {pct(k['top20_sku_share'])} 销售额，但 80% 收入需要 {num(k['sku_for_80'])} 个 SKU"
        f"（{pct(k['sku_for_80_share'])}）才能覆盖；Top 10 SKU 只占 {pct(k['top10_product_share'])}。"
        "选品不应只盯爆款，组合装和关联推荐更适合消化长尾。",
    )
    insight_5 = _insight(
        "05",
        pct(k["guest_revenue_share"], 1),
        "数据缺口本身就是增长空间",
        f"{pct(ctx.bundle.quality['missing_customer_share'])} 的交易行没有 CustomerID，"
        f"却贡献了 {pct(k['guest_revenue_share'])} 的收入。若把游客收入中的一部分变成可识别客户，"
        "复购、召回和 CLV 分析才有完整的分母。",
    )
    return f"""
<section class="section" id="insights">
  <div class="section-head">
    <div class="section-num">01</div>
    <div class="section-title"><div class="kicker">Executive summary</div><h2>先看五个结论</h2></div>
  </div>
  <p class="section-lede">
    这不是一份“把图表堆在一起”的报告。每个结论都对应一个可执行动作，
    并标注了它背后的口径与限制。
  </p>
  <div class="insight-grid">
    {insight_1}{insight_2}{insight_3}{insight_4}{insight_5}
  </div>
</section>
"""


def _build_data(ctx: "AnalysisContext") -> str:
    q = ctx.bundle.quality
    quality_rows = [
        ("原始交易行", num(q["source_rows"]), "UCI 原始记录数"),
        ("完全重复行", num(q["duplicate_rows"]), f"占原始 {pct(q['duplicate_rows'] / max(q['source_rows'], 1), 2)}"),
        ("去重后交易", num(q["clean_rows"]), "进入分析的主表"),
        ("有效销售行", num(q["sales_rows"]), "正数量、正单价、非取消"),
        ("取消 / 退货发票", f"{num(q['cancellation_invoices'])} 张 / {num(q['cancellation_rows'])} 行", "以 C 开头发票"),
        ("缺失 CustomerID", f"{num(q['missing_customer_rows'])} 行", pct(q["missing_customer_share"])),
        ("负数量行", num(q["negative_quantity_rows"]), pct(q["negative_quantity_rows"] / max(q["clean_rows"], 1))),
        ("零 / 负单价行", num(q["zero_price_rows"]), pct(q["zero_price_rows"] / max(q["clean_rows"], 1))),
        ("取消金额", money0(q["cancellation_value"]), f"占有效销售 {pct(q['cancellation_rate'])}"),
    ]
    quality_table = _table(
        ["检查项", "数量", "说明"],
        [(esc(a), f'<span class="mono">{esc(b)}</span>', esc(c)) for a, b, c in quality_rows],
        aligns=["left", "right", "left"],
    )
    return _section(
        "data",
        "02",
        "Data & method",
        "先把数据说清楚",
        "所有结论都建立在同一套清洗规则上：取消与销售分开、游客收入保留在总额、"
        "RFM 只对有 CustomerID 的客户计算。",
        f"""
<div class="pipeline" aria-label="分析流程">
  <div class="pipe-step"><span>01</span><strong>加载</strong><em>{num(q['source_rows'])} 行</em></div>
  <div class="pipe-arrow">→</div>
  <div class="pipe-step"><span>02</span><strong>清洗</strong><em>{num(q['clean_rows'])} 行</em></div>
  <div class="pipe-arrow">→</div>
  <div class="pipe-step"><span>03</span><strong>分析</strong><em>5 个模块</em></div>
  <div class="pipe-arrow">→</div>
  <div class="pipe-step"><span>04</span><strong>发布</strong><em>SVG + HTML</em></div>
</div>
<div class="grid-2 method-grid">
  <div>
    <h3 class="subhead">质量检查</h3>
    {quality_table}
  </div>
  <div class="method-notes">
    <h3 class="subhead">口径与处理</h3>
    <ul class="clean-list">
      <li><strong>有效销售</strong>：<span class="mono">quantity &gt; 0 &amp; unit_price &gt; 0</span>，且发票号不以 C 开头；金额 = 数量 × 单价。</li>
      <li><strong>取消 / 退货</strong>：以 C 开头的发票单独汇总，不从销售额中净额扣减，避免把退款月份和销售月份混在一起。</li>
      <li><strong>客户口径</strong>：RFM、复购率、cohort 只使用有 CustomerID 的交易；游客收入仍计入整体销售额。</li>
      <li><strong>商品口径</strong>：核心 SKU 使用 5 位数字 + 可选字母后缀，排除邮费、人工调整、银行费用与礼品券。</li>
      <li><strong>时间口径</strong>：数据止于 2011-12-09，12 月标记为部分月；cohort 与月度取消率只使用完整月份。</li>
      <li><strong>去重</strong>：完全重复的 {num(q['duplicate_rows'])} 行只保留一次；金额与订单数均基于去重后的交易。</li>
    </ul>
    <div class="mini-note">
      <span class="mini-label">为什么不做预测？</span>
      这份数据没有成本、流量、投放和退货原因字段。相比强行拟合一个“未来销售预测”，
      先把描述性分析与可执行分层做扎实，更诚实，也更有复用价值。
    </div>
  </div>
</div>
""",
    )


def _build_overview(ctx: "AnalysisContext") -> str:
    k = ctx.kpis.values
    countries = ctx.bundle.countries
    top_countries = countries.head(4) if not countries.empty else pd.DataFrame()
    country_rows = [
        (
            esc(row.country),
            f'<span class="mono">{money0(float(row.revenue))}</span>',
            pct(float(row.share)),
        )
        for row in top_countries.itertuples(index=False)
    ]
    country_table = _table(
        ["市场", "销售额", "份额"],
        country_rows,
        aligns=["left", "right", "right"],
        compact=True,
    )
    peak = _month_row(ctx, "2011-11")
    dec = _month_row(ctx, "2011-12")
    peak_text = (
        f"{money0(float(peak['revenue']))}，为完整月均值的 {k['peak_multiple']:.2f} 倍"
        if peak is not None
        else "—"
    )
    dec_text = (
        f"{money0(float(dec['revenue']))}（仅 9 天）"
        if dec is not None
        else "—"
    )
    return _section(
        "overview",
        "03",
        "Business pulse",
        "生意的形状：强季节、单市场、批发客",
        "先看总量，再看结构。月度曲线告诉我们钱在什么时候进来，国家结构告诉我们钱从哪里来。",
        f"""
{_figure(ctx, "monthly", 1, "月度销售额与订单数；12 月为部分月份，用斜线标记。")}
<div class="grid-2 overview-grid">
  <div>
    {_figure(ctx, "country", 2, "Top 8 国家/地区与其他市场的销售额份额。")}
  </div>
  <div class="side-notes">
    <h3 class="subhead">三个不能忽略的事实</h3>
    <div class="fact"><span class="fact-index">A</span><div><strong>11 月峰值 {peak_text}</strong><p>9–11 月连续加速，说明 Q4 需求在 9 月就已启动；如果 11 月才备货，会错过最陡的曲线。</p></div></div>
    <div class="fact"><span class="fact-index">B</span><div><strong>英国占 {pct(k['uk_share'])}，其他市场是长尾</strong><p>荷兰、EIRE、德国合计约 7.5%。跨境增长存在，但当前运营重心仍应放在英国本土的履约与复购。</p></div></div>
    <div class="fact"><span class="fact-index">C</span><div><strong>12 月 1–9 日已做到 {dec_text}</strong><p>不能把这条柱子当作“12 月同比”，但它提示圣诞前的最后一段需求仍然强劲。</p></div></div>
    {country_table}
    <p class="table-note">完整国家表与月度表见 <span class="mono">reports/*.csv</span>。</p>
  </div>
</div>
""",
    )


def _build_product(ctx: "AnalysisContext") -> str:
    products = ctx.bundle.products
    top = products.head(10) if not products.empty else pd.DataFrame()
    rows = []
    for row in top.itertuples(index=False):
        rows.append(
            (
                str(int(row.rank)),
                f'<span class="mono">{esc(row.stock_code)}</span>',
                esc(row.description),
                f'<span class="mono">{money0(float(row.revenue))}</span>',
                num(int(row.orders)),
                num(int(row.units)),
            )
        )
    product_table = _table(
        ["#", "SKU", "商品", "销售额", "订单", "件数"],
        rows,
        aligns=["right", "left", "left", "right", "right", "right"],
        compact=True,
    )
    basket = ctx.basket
    rule_rows = []
    for row in basket.rules.head(5).itertuples(index=False):
        rule_rows.append(
            (
                f"{esc(row.antecedent)} <span class='arrow'>→</span> {esc(row.consequent)}",
                f'<span class="mono">{float(row.lift):.1f}×</span>',
                pct(float(row.confidence)),
                pct(float(row.support)),
                num(int(row.pair_orders)),
            )
        )
    rule_table = _table(
        ["商品组合（A → B）", "Lift", "置信度", "支持度", "共现订单"],
        rule_rows,
        aligns=["left", "right", "right", "right", "right"],
        compact=True,
    )
    top_rule = basket.rules.iloc[0] if not basket.rules.empty else None
    return _section(
        "product",
        "04",
        "Assortment & basket",
        "商品：中等头部，很长长尾",
        "头部 SKU 能打，但撑不起全部大盘；真正可复用的动作，是用关联规则把长尾打包进购物篮。",
        f"""
<div class="grid-2 product-grid">
  <div>{_figure(ctx, "pareto", 3, "SKU 按销售额降序的累计收入曲线；虚线为 80% 收入参考线。")}</div>
  <div>
    <h3 class="subhead">Top 10 商品</h3>
    {product_table}
    <p class="table-note">
      23843 为单笔 80,995 件的批发订单（仅 1 张订单），在解读“常规动销”时应单独看待；
      22423 Regency Cake Stand 覆盖 1,988 张订单，是更稳定的头部单品。
    </p>
  </div>
</div>
{_figure(ctx, "basket", 4, "Top 60 SKU 中提升度最高的交叉销售组合；气泡/条形长度表示 lift。")}
<div class="grid-2 basket-grid">
  <div>
    <h3 class="subhead">规则表：可直接做组合装</h3>
    {rule_table}
    <p class="table-note">
      购物篮口径：{num(basket.orders_considered)} 个包含至少 2 个核心 SKU 的多商品订单，
      {num(basket.pair_count)} 组商品对通过 lift ≥ 1.2、置信度 ≥ 10% 的筛选。
    </p>
  </div>
  <div class="callout">
    <div class="callout-label">可执行解读</div>
    <p>
      这些组合不是“随机一起买”，而是共同出现概率显著高于各自独立出现概率。
      优先把 Top 3 组合做成“搭配购”或两张一组的小套装，用现有流量提升客单，
      比再开一个新 SKU 更便宜。
    </p>
    {f'<p class="callout-strong">最强组合：{esc(top_rule.antecedent)} → {esc(top_rule.consequent)}，lift {float(top_rule.lift):.1f}×，置信度 {pct(float(top_rule.confidence))}</p>' if top_rule is not None else ''}
  </div>
</div>
""",
    )


def _build_customer(ctx: "AnalysisContext") -> str:
    k = ctx.kpis.values
    rows = []
    actions = {
        "Champions": "专属顾问、early access、转介绍",
        "Loyal": "会员等级、复购礼、品类扩展",
        "Potential": "第二单券、搭配推荐",
        "New": "30 天欢迎旅程、首单后第 14 天触达",
        "Need Attention": "内容再触达、限时券",
        "At Risk": "人工回访、大客户方案",
        "Hibernating": "低成本邮件、品类召回",
        "Lost": "最后唤醒、控制触达成本",
    }
    for row in ctx.segments.itertuples(index=False):
        rows.append(
            (
                f'<span class="seg-dot" style="background:{row.color}"></span>{esc(row.segment_label)}',
                num(int(row.customers)),
                pct(float(row.customer_share)),
                pct(float(row.revenue_share)),
                f'<span class="mono">{money0(float(row.avg_monetary))}</span>',
                esc(actions.get(row.segment, "")),
            )
        )
    segment_table = _table(
        ["客群", "人数", "人数占比", "收入占比", "平均历史消费", "建议动作"],
        rows,
        aligns=["left", "right", "right", "right", "right", "left"],
        compact=True,
    )
    hv = ctx.high_value
    return _section(
        "customer",
        "05",
        "Customer value",
        "客户：少数人撑起大盘",
        "RFM 的价值不在于把客户贴上标签，而在于把有限的人力放到最值得被经营的那一小群人身上。",
        f"""
{_figure(ctx, "rfm", 5, "RFM 客群的人数占比与收入贡献；左侧为客户数，右侧为收入。")}
<div class="grid-2 customer-grid">
  <div>
    {_figure(ctx, "lorenz", 6, "客户价值 Lorenz 曲线；虚线为完全平等线。")}
  </div>
  <div>
    <h3 class="subhead">分层后的动作优先级</h3>
    {segment_table}
    <div class="dark-callout">
      <div class="dark-label">最值得马上联系的一群人</div>
      <div class="dark-big">{num(hv['customers'])} 人</div>
      <p>
        高价值且已较久未购买（M ≥ 4、R ≤ 2），合计历史消费 {money0(hv['revenue'])}，
        占已识别客户收入的 {pct(hv['revenue_share'])}。
        这是一份可以今天就导出、分配给销售或客服的名单。
      </p>
    </div>
  </div>
</div>
""",
    )


def _build_retention(ctx: "AnalysisContext") -> str:
    co = ctx.cohorts.summary
    has_cohort = int(co.get("cohorts", 0)) > 0
    m1 = pct(co.get("m1") or 0, 1) if has_cohort else "样本不足"
    m3 = pct(co.get("m3") or 0, 1) if has_cohort else "样本不足"
    m6 = pct(co.get("m6") or 0, 1) if has_cohort else "样本不足"
    m10 = pct(co.get("m10") or 0, 1) if co.get("m10") is not None else "—"
    return _section(
        "retention",
        "06",
        "Retention",
        "留存：首购后的 30 天，比第 6 个月更重要",
        "Cohort 不是一张“好看的热力图”，它回答的是一个很具体的问题：新客第一次买完之后，还会不会回来。",
        f"""
{_figure(ctx, "cohort", 7, "首购月 cohort 在后续月份的留存率；M0 恒为 100%，已省略。")}
<div class="metric-row">
  <div class="metric-card"><span>M1 加权留存</span><strong>{m1}</strong><em>首购后第 1 个月</em></div>
  <div class="metric-card"><span>M3 加权留存</span><strong>{m3}</strong><em>首购后第 3 个月</em></div>
  <div class="metric-card"><span>M6 加权留存</span><strong>{m6}</strong><em>首购后第 6 个月</em></div>
  <div class="metric-card accent"><span>M10 加权留存</span><strong>{m10}</strong><em>受 Q4 旺季召回影响</em></div>
</div>
<div class="grid-2 retention-grid">
  <div class="callout">
    <div class="callout-label">读图方式</div>
    <p>
      每一行是一个首购月，列是首购后的第 N 个月。M1 只有约 {m1}，说明“买过一次”远不等于“成为客户”；
      而 M9–M10 回升到 30% 以上，主要是 9–11 月旺季把老客重新拉回来了。
      这不是留存改善，而是季节性召回的证据。
    </p>
  </div>
  <div class="callout subtle">
    <div class="callout-label">口径说明</div>
    <p>
      首购月为 2010-12 的 cohort 被排除：数据从 2010-12-01 开始，无法判断这些客户是不是在更早之前就已存在
      （左截断）。当前展示 {num(co.get('cohorts', 0))} 个 cohort、{num(co.get('customers', 0))} 位客户，
      数据截至 {esc(str(co.get('last_complete_month', '—')))}。
    </p>
  </div>
</div>
""",
    )


def _build_operations(ctx: "AnalysisContext") -> str:
    k = ctx.kpis.values
    jan = _month_row(ctx, "2011-01")
    jan_cancel = pct(float(jan["cancellation_rate"])) if jan is not None else "—"
    return _section(
        "operations",
        "07",
        "Operations & risk",
        "运营节奏：周二上午最忙，1 月退款最多",
        "把交易时间还原成“星期 × 小时”的节奏，再叠加取消/退货率，能看到运营排班与售后风险的真实形状。",
        f"""
{_figure(ctx, "rhythm", 8, "按星期与小时汇总的销售额；颜色越深销售越集中。")}
<div class="grid-2 ops-grid">
  <div>{_figure(ctx, "cancellation", 9, "完整月份的取消/退货金额占比；12 月部分月不纳入趋势。")}</div>
  <div class="side-notes">
    <h3 class="subhead">两条运营结论</h3>
    <div class="fact"><span class="fact-index">A</span><div><strong>销售峰值集中在工作日 9–12 点</strong><p>周二 10 点单小时销售额最高（£338k），周四 9 点次之。邮件、短信和站内推送更适合放在周一晚间到周二上午；客服排班也应对齐这个窗口。</p></div></div>
    <div class="fact"><span class="fact-index">B</span><div><strong>1 月取消率达到 {jan_cancel}</strong><p>全期取消金额占比 {pct(k['cancellation_rate'])}。1 月的异常高点与节后退款、跨期取消有关，建议从 1 月起记录取消原因码，并把退款原因反馈给选品与详情页。</p></div></div>
    <div class="mini-note">
      <span class="mini-label">数据限制</span>
      数据集没有流量、广告花费、履约时效和退货原因。取消率是“金额口径”，不能直接等同于“退货率”或“客户流失率”。
    </div>
  </div>
</div>
""",
    )


def _build_actions(ctx: "AnalysisContext") -> str:
    k = ctx.kpis.values
    hv = ctx.high_value
    actions = [
        (
            "P0",
            "30 / 60 / 90 新客激活",
            f"首购人群 M1 仅 {pct(ctx.cohorts.summary.get('m1') or 0)}；复购客户贡献 {pct(k['repeat_revenue_share'])} 的已识别收入",
            "第 14 天第二单券 + 第 30 天品类推荐 + 第 60 天召回",
            "M1 留存 20% → 25%",
            "低",
        ),
        (
            "P0",
            "高价值流失预警名单",
            f"{num(hv['customers'])} 人、{money0(hv['revenue'])} 历史消费、{pct(hv['revenue_share'])} 收入",
            "销售/客服人工回访，附大客户专属补货方案",
            "30 天回访率、复购率",
            "中",
        ),
        (
            "P1",
            "Q4 备货与投放前移",
            f"11 月为完整月均值的 {k['peak_multiple']:.2f} 倍；9 月环比 +39.4%",
            "9 月完成圣诞核心 SKU 备货，10 月前锁定投放素材",
            "11 月缺货率、售罄时间",
            "中",
        ),
        (
            "P1",
            "组合装与搭配购",
            f"Top 60 SKU 中 {num(ctx.basket.pair_count)} 组正向关联；最强 lift 8.1×",
            "Top 3 规则做套装/加购，不新增 SKU",
            "客单价、组合转化率",
            "低",
        ),
        (
            "P2",
            "结账时捕获 CustomerID",
            f"{pct(k['guest_revenue_share'])} 收入来自游客；{pct(ctx.bundle.quality['missing_customer_share'])} 行缺 ID",
            "登录/注册激励、游客订单后绑定、线下批发客户建档",
            "可识别收入占比",
            "中",
        ),
        (
            "P2",
            "取消原因码与退款分析",
            f"取消金额占比 {pct(k['cancellation_rate'])}；1 月达 {pct(float(_month_row(ctx, '2011-01')['cancellation_rate'])) if _month_row(ctx, '2011-01') is not None else '—'}",
            "在客服系统强制记录原因码，按 SKU/国家复盘",
            "取消率 < 7%",
            "低",
        ),
    ]
    rows = []
    for priority, name, evidence, action, metric, cost in actions:
        tone = "p0" if priority == "P0" else ("p1" if priority == "P1" else "p2")
        rows.append(
            (
                _pill(priority, tone),
                f"<strong>{esc(name)}</strong>",
                esc(evidence),
                esc(action),
                esc(metric),
                esc(cost),
            )
        )
    action_table = _table(
        ["优先级", "动作", "证据", "具体做法", "衡量指标", "成本"],
        rows,
        aligns=["left", "left", "left", "left", "left", "right"],
    )
    return _section(
        "actions",
        "08",
        "Action plan",
        "如果只做六件事",
        "按“证据强度 × 执行成本”排序。P0 是本周就能启动的，不需要新的数据基础设施。",
        f"""
{action_table}
<div class="roadmap">
  <div class="roadmap-card"><span>0–30 天</span><strong>名单与触发</strong><p>导出高价值流失名单；上线首购第 14 天第二单券；建立取消原因码。</p></div>
  <div class="roadmap-card"><span>31–60 天</span><strong>组合与内容</strong><p>Top 3 组合做搭配购；用 RFM 分层替换全量群发；补齐游客绑定路径。</p></div>
  <div class="roadmap-card"><span>61–90 天</span><strong>Q4 前置</strong><p>9 月前完成圣诞核心 SKU 备货；投放素材与客服排班按“周二上午峰值”重排。</p></div>
</div>
""",
    )


def _build_reproduce(ctx: "AnalysisContext") -> str:
    q = ctx.bundle.quality
    return _section(
        "reproduce",
        "09",
        "Reproduce & limits",
        "可复现，也知道自己不知道什么",
        "代码、数据、图表和报告都在同一个仓库里。换一份同结构数据，运行一条命令即可复现全部分析。",
        f"""
<div class="grid-2 repro-grid">
  <div>
    <h3 class="subhead">从零复现</h3>
    <pre class="code"><code>git clone {REPO_URL}.git
cd ecommerce-growth-analytics
python -m venv .venv
.venv\\Scripts\\activate
pip install -e ".[dev]"
python run_analysis.py
start docs/index.html</code></pre>
    <p class="table-note">
      输出：<span class="mono">docs/index.html</span>（本报告）、<span class="mono">docs/figures/*.svg</span>、
      <span class="mono">reports/*.csv</span> 与 <span class="mono">reports/metrics.json</span>。
      运行 <span class="mono">pytest</span> 可执行单元测试。
    </p>
    <h3 class="subhead">目录</h3>
    <pre class="tree"><code>src/ecommerce_analytics/
  data.py      清洗与聚合
  metrics.py   KPI 与集中度
  rfm.py       RFM 分层
  cohort.py    留存矩阵
  basket.py    关联规则
  charts.py    手写 SVG
  reporting.py 静态报告
data/          原始与样例数据
docs/          可发布的 GitHub Pages
reports/       CSV / JSON 结果</code></pre>
  </div>
  <div>
    <h3 class="subhead">局限性</h3>
    <ul class="limit-list">
      <li><strong>样本单一</strong>：一家英国礼品批发/零售商的 2010–2011 年交易，不能直接外推到所有电商。</li>
      <li><strong>没有利润</strong>：只有销售额与数量，没有成本、毛利、履约和广告数据，因此不做 ROI 或 CLV 的绝对值判断。</li>
      <li><strong>没有退货原因</strong>：取消金额占比 {pct(q['cancellation_rate'])} 是金额口径，不能等同于退货率。</li>
      <li><strong>左截断</strong>：2010-12 的首购 cohort 被排除；更早的客户历史不可见。</li>
      <li><strong>部分月份</strong>：2011-12 只有 9 天，月度趋势与取消率中单独处理。</li>
      <li><strong>相关不等于因果</strong>：RFM 分层、购物篮规则都是描述性发现，行动效果需要 A/B 测试验证。</li>
    </ul>
    <div class="source-box">
      <div class="source-label">数据来源</div>
      <p>Chen, D. (2015). <em>Online Retail</em> [Dataset]. UCI Machine Learning Repository.
      DOI: <a href="{DOI_URL}" target="_blank" rel="noreferrer">10.24432/C5BW33</a>.
      数据许可：CC BY 4.0；代码许可：MIT。</p>
      <p class="source-meta">清洗后 {num(q['clean_rows'])} 行 · 原始 {num(q['source_rows'])} 行 · 去重 {num(q['duplicate_rows'])} 行 · 生成于 {esc(ctx.generated_at[:10])}</p>
    </div>
  </div>
</div>
""",
    )


CSS = """
:root{
  --paper:#FBF9F5;--card:#FFFFFF;--ink:#1F2933;--muted:#667085;--line:#E4E0D8;
  --accent:#C2410C;--teal:#0F766E;--gold:#B7791F;--soft:#F5EFE7;--soft-2:#EEF6F4;
  --shadow:0 1px 2px rgba(31,41,51,.04),0 10px 30px rgba(31,41,51,.035);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;color:var(--ink);
  overflow-x:hidden;
  font-family:Inter,"Noto Sans SC","Source Han Sans SC","Microsoft YaHei","PingFang SC",Arial,sans-serif;
  background:
    radial-gradient(1100px 520px at 92% -8%, #F4E2D6 0%, rgba(244,226,214,0) 60%),
    radial-gradient(900px 520px at -8% 28%, #E7F2EF 0%, rgba(231,242,239,0) 55%),
    var(--paper);
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;
}
::selection{background:#F2C7B5}
a{color:inherit;text-decoration:none}
.wrap{max-width:1180px;margin:0 auto;padding:0 28px}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:20px 0;border-bottom:1px solid rgba(31,41,51,.10)}
.brand{display:flex;align-items:center;gap:10px;font-size:12px;font-weight:750;letter-spacing:.08em}
.brand-mark{width:29px;height:29px;display:grid;place-items:center;border-radius:8px;background:var(--ink);color:#fff;font-size:9px;letter-spacing:.04em}
.nav{display:flex;align-items:center;gap:24px;font-size:12px;color:var(--muted)}
.nav a:hover{color:var(--ink)}
.nav .github{border:1px solid var(--line);padding:8px 12px;border-radius:999px;color:var(--ink);background:rgba(255,255,255,.55)}
.hero{padding:66px 0 34px}
.hero-grid{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(298px,.72fr);gap:54px;align-items:end}
.hero-grid > *{min-width:0}
.eyebrow{font-size:10.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);font-weight:750;margin-bottom:18px}
h1{font-size:clamp(42px,5.4vw,70px);line-height:1.035;letter-spacing:-.046em;margin:0;font-weight:820}
h1 em{font-style:normal;color:var(--accent)}
.hero-sub{max-width:700px;font-size:15.5px;line-height:1.9;color:#4B5563;margin:24px 0 0;overflow-wrap:break-word}
.hero-meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}
.chip{font-size:10.5px;letter-spacing:.02em;border:1px solid rgba(31,41,51,.13);background:rgba(255,255,255,.52);padding:7px 10px;border-radius:999px;color:#475467}
.cta-row{display:flex;gap:10px;margin-top:28px}
.btn{display:inline-flex;align-items:center;gap:8px;font-size:12px;font-weight:650;padding:12px 16px;border-radius:999px;border:1px solid var(--line);transition:.15s ease}
.btn.primary{background:var(--ink);color:#fff;border-color:var(--ink)}
.btn.primary:hover{transform:translateY(-1px);background:#111827}
.btn.ghost{background:rgba(255,255,255,.55)}
.btn.ghost:hover{border-color:var(--ink)}
.snapshot{position:relative;overflow:hidden;background:linear-gradient(155deg,#1F2933 0%,#111827 100%);color:#fff;border-radius:22px;padding:24px 24px 20px;box-shadow:0 24px 60px rgba(17,24,39,.16);width:100%;max-width:430px;min-width:0}
.snapshot:after{content:"";position:absolute;width:220px;height:220px;border-radius:50%;right:-90px;top:-100px;background:radial-gradient(circle,rgba(194,65,12,.55),transparent 66%)}
.snap-top{display:flex;justify-content:space-between;font-size:8.5px;letter-spacing:.15em;color:rgba(255,255,255,.55)}
.snap-big{font-size:44px;letter-spacing:-.04em;font-weight:780;margin-top:22px;line-height:1}
.snap-caption{font-size:10px;color:rgba(255,255,255,.55);margin-top:8px}
.snap-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px 18px;margin-top:24px;padding-top:18px;border-top:1px solid rgba(255,255,255,.14)}
.snap-grid strong{display:block;font-size:17px;font-weight:700;letter-spacing:-.02em}
.snap-grid span{display:block;font-size:9px;color:rgba(255,255,255,.52);margin-top:4px}
.snap-foot{margin-top:20px;font-size:8.5px;color:rgba(255,255,255,.42);letter-spacing:.03em}
.kpi-strip{display:grid;grid-template-columns:repeat(6,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-top:12px}
.kpi{padding:18px 16px 20px;border-right:1px solid var(--line)}
.kpi:last-child{border-right:0}
.kpi-label{font-size:9.5px;letter-spacing:.06em;color:var(--muted);text-transform:uppercase}
.kpi-value{font-size:25px;font-weight:760;letter-spacing:-.035em;margin-top:8px}
.kpi-note{font-size:9px;line-height:1.55;color:var(--muted);margin-top:5px}
.section{padding:62px 0}
.section + .section{border-top:1px solid var(--line)}
.section-head{display:flex;align-items:flex-start;gap:18px}
.section-num{font-size:10px;letter-spacing:.12em;color:var(--accent);font-weight:750;padding-top:7px;min-width:24px}
.kicker{font-size:9.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin-bottom:7px}
h2{font-size:clamp(26px,3vw,36px);line-height:1.15;letter-spacing:-.035em;margin:0;font-weight:760}
.section-lede{max-width:820px;margin:14px 0 28px 42px;color:#4B5563;font-size:14px;line-height:1.85}
.insight-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 46px;margin-left:42px}
.insight{display:grid;grid-template-columns:34px 1fr;gap:14px;padding:22px 0;border-top:1px solid var(--line)}
.insight:nth-child(5){grid-column:1/-1}
.insight-num{font-size:9.5px;color:var(--muted);letter-spacing:.07em;padding-top:3px}
.insight-metric{font-size:24px;font-weight:780;letter-spacing:-.03em;color:var(--accent);line-height:1}
.insight h3{font-size:15.5px;margin:9px 0 7px;letter-spacing:-.015em}
.insight p{margin:0;font-size:12px;line-height:1.8;color:#4B5563}
.chart-card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:12px 14px 0;box-shadow:var(--shadow);overflow:hidden;margin:0}
.chart-card svg{display:block;width:100%;height:auto}
figcaption{font-size:9.5px;line-height:1.6;color:var(--muted);border-top:1px solid #F0ECE5;padding:10px 4px 12px;margin-top:8px}
.fig-no{color:var(--accent);font-weight:700;margin-right:4px}
.grid-2{display:grid;grid-template-columns:1.2fr .8fr;gap:22px;align-items:start}
.grid-2 > *{min-width:0}
.chart-card,.table-wrap,.side-notes{min-width:0}
.method-grid,.overview-grid,.product-grid,.customer-grid,.ops-grid,.repro-grid{margin-top:22px}
.customer-grid{grid-template-columns:1.08fr .92fr}
.subhead{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:4px 0 12px;font-weight:700}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:14px;background:rgba(255,255,255,.7);margin:10px 0}
.data-table{width:100%;border-collapse:collapse;font-size:10.5px}
.data-table th{text-align:left;font-size:8.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:650;padding:10px 11px;border-bottom:1px solid var(--line);white-space:nowrap;background:rgba(251,249,245,.65)}
.data-table td{padding:10px 11px;border-bottom:1px solid #F0ECE5;vertical-align:top;line-height:1.55}
.data-table tr:last-child td{border-bottom:0}
.data-table .right{text-align:right}
.data-table .num,.mono{font-variant-numeric:tabular-nums;font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace;font-size:9.5px}
.data-table.compact th{padding:8px}
.table-note{font-size:9.5px;line-height:1.7;color:var(--muted);margin:9px 0 0}
.clean-list,.limit-list{margin:0;padding-left:16px;font-size:11.5px;line-height:1.8;color:#4B5563}
.clean-list li,.limit-list li{margin-bottom:8px}
.clean-list strong,.limit-list strong{color:var(--ink)}
.mini-note{border:1px solid var(--line);background:rgba(255,255,255,.55);border-radius:14px;padding:14px 16px;font-size:11px;line-height:1.75;color:#4B5563;margin-top:16px}
.mini-label{display:block;font-size:8.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:6px}
.pipeline{display:flex;align-items:stretch;gap:8px;border:1px solid var(--line);background:rgba(255,255,255,.65);border-radius:16px;padding:12px;margin:6px 0 22px}
.pipe-step{flex:1;padding:12px 14px;border-radius:11px;background:var(--paper);display:grid;grid-template-columns:24px 1fr;grid-template-rows:auto auto;gap:2px 8px;align-items:center}
.pipe-step span{font-size:8.5px;color:var(--accent);font-weight:700;grid-row:1/3}
.pipe-step strong{font-size:11px}
.pipe-step em{font-style:normal;font-size:9px;color:var(--muted)}
.pipe-arrow{display:grid;place-items:center;color:var(--muted);font-size:13px}
.side-notes{padding-top:2px}
.fact{display:grid;grid-template-columns:24px 1fr;gap:10px;padding:14px 0;border-top:1px solid var(--line)}
.fact:first-of-type{border-top:0}
.fact-index{font-size:9px;color:var(--accent);font-weight:750;border:1px solid #E9C7B7;width:21px;height:21px;display:grid;place-items:center;border-radius:50%;margin-top:2px}
.fact strong{font-size:12px;line-height:1.5}
.fact p{margin:5px 0 0;font-size:10.8px;line-height:1.75;color:#4B5563}
.callout{background:var(--soft);border-left:3px solid var(--accent);border-radius:0 14px 14px 0;padding:18px 20px;font-size:11.5px;line-height:1.85;color:#3F3A34}
.callout.subtle{background:var(--soft-2);border-left-color:var(--teal)}
.callout p{margin:0}
.callout-label{font-size:8.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:8px}
.callout.subtle .callout-label{color:var(--teal)}
.callout-strong{font-weight:700;color:var(--ink);margin-top:12px}
.dark-callout{background:var(--ink);color:#fff;border-radius:16px;padding:20px;margin-top:16px}
.dark-label{font-size:8.5px;letter-spacing:.13em;text-transform:uppercase;color:#F3B59D;font-weight:700}
.dark-big{font-size:38px;font-weight:780;letter-spacing:-.04em;margin-top:8px;line-height:1}
.dark-callout p{font-size:10.5px;line-height:1.8;color:rgba(255,255,255,.72);margin:10px 0 0}
.seg-dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:6px;vertical-align:1px}
.metric-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px}
.metric-card{border:1px solid var(--line);background:rgba(255,255,255,.66);border-radius:14px;padding:14px 16px}
.metric-card span{font-size:8.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.metric-card strong{display:block;font-size:25px;font-weight:760;letter-spacing:-.035em;margin-top:5px}
.metric-card em{font-style:normal;font-size:9px;color:var(--muted);display:block;margin-top:3px}
.metric-card.accent{background:#FBF0EA;border-color:#EBC5B2}
.retention-grid{margin-top:18px}
.roadmap{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:18px}
.roadmap-card{border:1px solid var(--line);border-radius:14px;padding:16px;background:rgba(255,255,255,.58)}
.roadmap-card span{font-size:8.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);font-weight:700}
.roadmap-card strong{display:block;font-size:12.5px;margin-top:8px}
.roadmap-card p{font-size:10.5px;line-height:1.75;color:#4B5563;margin:6px 0 0}
.pill{display:inline-block;font-size:8.5px;font-weight:750;letter-spacing:.05em;padding:4px 7px;border-radius:999px;background:#F0ECE5;color:#57534E}
.pill.p0{background:#FBE4D9;color:#9A3412}
.pill.p1{background:#F8EEDB;color:#92400E}
.pill.p2{background:#E8F3F1;color:#0F766E}
.flag{font-size:7.5px;letter-spacing:.04em;color:var(--accent);border:1px solid #EBC5B2;padding:2px 4px;border-radius:4px;white-space:nowrap}
.arrow{color:var(--accent);padding:0 2px}
.code,.tree{background:#1F2933;color:#F2EEE8;border-radius:14px;padding:16px 18px;font-size:10px;line-height:1.8;overflow-x:auto;font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace;border:1px solid #111827}
.tree{margin-top:10px}
.code code,.tree code{font-family:inherit}
.source-box{border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-top:20px;background:rgba(255,255,255,.55);font-size:10px;line-height:1.8;color:#4B5563}
.source-label{font-size:8.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:5px}
.source-box p{margin:0 0 5px}
.source-box a{border-bottom:1px solid #D6CFC5}
.source-meta{color:var(--muted);font-size:8.5px}
.footer{padding:34px 0 46px;border-top:1px solid var(--line);margin-top:8px}
.footer-grid{display:flex;justify-content:space-between;gap:24px;align-items:flex-end}
.footer-brand{font-size:12px;font-weight:750;letter-spacing:.06em}
.footer p{font-size:9.5px;line-height:1.8;color:var(--muted);margin:6px 0 0;max-width:680px}
.footer .mono{font-size:8.5px}
@media (max-width:980px){
  .hero-grid{grid-template-columns:1fr;gap:30px}
  .snapshot{max-width:430px}
  .kpi-strip{grid-template-columns:repeat(3,1fr)}
  .kpi:nth-child(3){border-right:0}
  .kpi:nth-child(n+4){border-top:1px solid var(--line)}
  .grid-2{grid-template-columns:1fr}
  .insight-grid{grid-template-columns:1fr;margin-left:0}
  .insight:nth-child(5){grid-column:auto}
  .section-lede{margin-left:0}
  .metric-row{grid-template-columns:repeat(2,1fr)}
  .roadmap{grid-template-columns:1fr}
  .nav a:not(.github){display:none}
}
@media (max-width:620px){
  .wrap{padding:0 18px}
  .hero{padding:42px 0 24px}
  h1{font-size:40px}
  .kpi-strip{grid-template-columns:1fr 1fr}
  .kpi:nth-child(2n){border-right:0}
  .kpi:nth-child(n+3){border-top:1px solid var(--line)}
  .pipeline{flex-wrap:wrap}
  .pipe-arrow{display:none}
  .pipe-step{flex:1 1 44%}
  .snapshot{max-width:100%}
  .footer-grid{display:block}
  .plot{max-width:100%}
}
@media print{
  body{background:#fff}
  .topbar,.cta-row,.nav{display:none}
  .hero{padding-top:20px}
  .chart-card,.dark-callout,.snapshot{box-shadow:none}
  .section{break-inside:avoid;padding:34px 0}
  .chart-card{break-inside:avoid}
}
"""


def render_report(context: "AnalysisContext", path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    k = context.kpis.values
    q = context.bundle.quality
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="基于 UCI Online Retail 的电商数据分析：收入、商品、RFM、cohort、购物篮与运营建议。">
<meta name="author" content="dwz72978-stack">
<meta property="og:title" content="一家英国礼品电商的 12 个月增长体检">
<meta property="og:description" content="从 53.7 万行交易到 RFM、cohort 与购物篮：一份可复现的电商数据分析。">
<meta property="og:type" content="article">
<title>一家英国礼品电商的 12 个月增长体检 · E-commerce Growth Analytics</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <a class="brand" href="{REPO_URL}" target="_blank" rel="noreferrer">
      <span class="brand-mark">EA</span><span>RETAIL / GROWTH LAB</span>
    </a>
    <nav class="nav" aria-label="页面导航">
      <a href="#insights">结论</a>
      <a href="#product">商品</a>
      <a href="#customer">客户</a>
      <a href="#retention">留存</a>
      <a href="#actions">行动</a>
      <a class="github" href="{REPO_URL}" target="_blank" rel="noreferrer">GitHub ↗</a>
    </nav>
  </div>
  {_build_hero(context)}
  {_build_insights(context)}
  {_build_data(context)}
  {_build_overview(context)}
  {_build_product(context)}
  {_build_customer(context)}
  {_build_retention(context)}
  {_build_operations(context)}
  {_build_actions(context)}
  {_build_reproduce(context)}
  <footer class="footer">
    <div class="footer-grid">
      <div>
        <div class="footer-brand">E-COMMERCE GROWTH ANALYTICS</div>
        <p>一个可复现的电商数据分析作品集：Python + pandas + 手写 SVG，没有 BI 工具，也没有图表库。
        数据来自 UCI Machine Learning Repository，按 CC BY 4.0 使用；代码以 MIT 许可发布。</p>
        <p class="mono">DOI 10.24432/C5BW33 · {num(q['clean_rows'])} rows · generated {esc(context.generated_at)}</p>
      </div>
      <div>
        <p><a href="{PROFILE_URL}" target="_blank" rel="noreferrer">GitHub / dwz72978-stack</a> ·
        <a href="{REPO_URL}" target="_blank" rel="noreferrer">Source</a> ·
        <a href="{DATA_URL}" target="_blank" rel="noreferrer">Dataset</a></p>
        <p class="mono">© 2026 · MIT (code) / CC BY 4.0 (data)</p>
      </div>
    </div>
  </footer>
</div>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
