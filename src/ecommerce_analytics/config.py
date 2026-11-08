"""Project-wide constants and presentation settings."""

from __future__ import annotations

from typing import Final

PALETTE: Final[dict[str, str]] = {
    "paper": "#FBF9F5",
    "card": "#FFFFFF",
    "ink": "#1F2933",
    "muted": "#667085",
    "line": "#E4E0D8",
    "grid": "#ECE8E1",
    "accent": "#C2410C",
    "accent_soft": "#F4C7B5",
    "teal": "#0F766E",
    "teal_soft": "#A7D9D3",
    "gold": "#B7791F",
    "blue": "#1D4ED8",
    "rose": "#BE123C",
    "slate": "#475467",
}

FONT_STACK: Final[str] = (
    'Inter, "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", '
    "PingFang SC, Arial, sans-serif"
)

MONTH_LABELS_ZH: Final[list[str]] = [
    "1月",
    "2月",
    "3月",
    "4月",
    "5月",
    "6月",
    "7月",
    "8月",
    "9月",
    "10月",
    "11月",
    "12月",
]

WEEKDAY_LABELS_ZH: Final[dict[int, str]] = {
    0: "周一",
    1: "周二",
    2: "周三",
    3: "周四",
    4: "周五",
    5: "周六",
    6: "周日",
}

SEGMENT_ORDER: Final[list[str]] = [
    "Champions",
    "Loyal",
    "Potential",
    "New",
    "Need Attention",
    "At Risk",
    "Hibernating",
    "Lost",
]

SEGMENT_LABELS_ZH: Final[dict[str, str]] = {
    "Champions": "冠军客户",
    "Loyal": "忠诚客户",
    "Potential": "潜力客户",
    "New": "新客户",
    "Need Attention": "需要关注",
    "At Risk": "流失预警",
    "Hibernating": "沉睡客户",
    "Lost": "已流失",
}

SEGMENT_DESCRIPTIONS: Final[dict[str, str]] = {
    "Champions": "最近购买、频次高、金额高；优先做复购与转介绍。",
    "Loyal": "近期仍有购买且频次稳定；用会员权益维持。",
    "Potential": "近期购买 2–3 次；用第二单券推动形成习惯。",
    "New": "近期首次或仅购买一次；首购 90 天是激活窗口。",
    "Need Attention": "最近一次购买在 3 个月前，频次偏低；定向唤醒。",
    "At Risk": "高价值但已较久未购买；需要人工回访。",
    "Hibernating": "低频且久未购买；低成本触达即可。",
    "Lost": "最久未购买且仅买过一次；控制营销成本。",
}

SEGMENT_COLORS: Final[dict[str, str]] = {
    "Champions": "#0F766E",
    "Loyal": "#2A9D8F",
    "Potential": "#4F9D69",
    "New": "#1D4ED8",
    "Need Attention": "#B7791F",
    "At Risk": "#C2410C",
    "Hibernating": "#9A6B4F",
    "Lost": "#8D99AE",
}

# Core merchandise uses a 5-digit SKU with an optional letter suffix.
# This deliberately excludes postage, manual adjustments, bank charges and
# gift-voucher codes so that the product Pareto is not distorted.
CORE_SKU_PATTERN: Final[str] = r"^\d{5}[A-Z]?$"

# Files that are shipped with the project.
DEFAULT_RAW_PATH: Final[str] = "data/raw/online_retail.csv.gz"
DEFAULT_SAMPLE_PATH: Final[str] = "data/sample/online_retail_sample.csv"
