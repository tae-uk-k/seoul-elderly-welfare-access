"""
그래프 재생성 v2
① 04_주요변수_분포_히스토그램_가로.png  — 히스토그램 x↔y 전환 (가로 막대)
② 05_행정동별_65세이상인구.png           — 행정동 × 65세이상 등록인구
③ 06_행정동별_생활인구.png              — 행정동 × 65세이상 생활인구
④ 07_지하철역_분포.png                  — 노선별 역 수 + 자치구별 분포
⑤ 08_이상치_탐지_박스플롯_개선.png     — 로그 스케일 바이올린+박스 콤보
"""

import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path

# ── 폰트 ──────────────────────────────────────────────────────────
fm.fontManager.addfont("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
plt.rcParams.update({
    "font.family":         "NanumGothic",
    "axes.unicode_minus":  False,
    "figure.facecolor":    "white",
    "axes.facecolor":      "#f8f9fa",
    "axes.grid":           True,
    "grid.color":          "white",
    "grid.linewidth":      1.0,
    "axes.spines.top":     False,
    "axes.spines.right":   False,
})

BASE = Path("/mnt/c/Users/xodnr/Desktop/서울시 복지 데드존 분석")
OUT  = BASE / "04_분석결과" / "변수관계_분석_시각화"

PALETTE = {
    "blue":   "#4C72B0",
    "red":    "#C44E52",
    "green":  "#55A868",
    "orange": "#DD8452",
    "gray":   "#8172B2",
    "teal":   "#64B5CD",
}

# ── 데이터 로드 ───────────────────────────────────────────────────
df_pop = pd.read_csv(BASE / "02_가공데이터/행정동별_65세이상인구.csv")
df_pop["자치구"] = df_pop["행정구역"].str.extract(r"서울특별시\s+(\S+구)")

df_live_raw = pd.read_csv(BASE / "02_가공데이터/격자별_생활인구_65세이상.csv")
df_live = (
    df_live_raw.groupby("행정동코드")["65세이상"]
    .mean()
    .reset_index()
    .rename(columns={"65세이상": "생활인구_65세이상"})
)
df_live["행정동코드"] = df_live["행정동코드"].astype(str).str[:8]
df_pop["행정동코드"] = df_pop["행정동코드"].astype(str).str[:8]
df_merged = df_pop.merge(df_live, on="행정동코드", how="left")

df_alone = pd.read_csv(BASE / "02_가공데이터/독거노인_행정동코드포함.csv")
df_alone["행정동코드"] = df_alone["행정동코드"].astype(str).str.replace(r"\.0$","",regex=True).str[:8]

df_metro = pd.read_csv(BASE / "02_가공데이터/서울_지하철역_좌표.csv")

df_analysis = pd.read_csv(
    BASE / "04_분석결과/analysis_100m_20260523/100m_격자_분석데이터.csv"
)

GU_CODE5 = {
    "11110":"종로구","11140":"중구","11170":"용산구","11200":"성동구",
    "11215":"광진구","11230":"동대문구","11260":"중랑구","11290":"성북구",
    "11305":"강북구","11320":"도봉구","11350":"노원구","11380":"은평구",
    "11410":"서대문구","11440":"마포구","11470":"양천구","11500":"강서구",
    "11530":"구로구","11545":"금천구","11560":"영등포구","11590":"동작구",
    "11620":"관악구","11650":"서초구","11680":"강남구","11710":"송파구","11740":"강동구",
}
df_metro["자치구"] = df_metro["역경도"].apply(lambda _: None)  # 좌표로 매핑은 아래에서
# 주소에서 자치구 추출
df_metro["자치구"] = df_metro["역사도로명주소"].str.extract(r"서울특별시\s+(\S+구)")


# ════════════════════════════════════════════════════════════════
# ① 주요변수 가로 히스토그램
# ════════════════════════════════════════════════════════════════
print("① 가로 히스토그램 생성 중...")

vars_info = [
    ("65세이상인구",    df_pop["65세이상인구"],       PALETTE["blue"],   "65세이상 등록인구 (명)",   "행정동 수"),
    ("독거노인",        df_alone["독거노인_합계"],     PALETTE["red"],    "독거노인 수 (명)",         "행정동 수"),
    ("생활인구_65",     df_merged["생활인구_65세이상"].dropna(), PALETTE["green"], "생활인구 65세이상 (명)", "행정동 수"),
    ("복지관거리",      df_analysis["dist_welfare"],   PALETTE["orange"], "복지관까지 거리 (m)",      "격자 수"),
    ("버스정류소",      df_analysis["bus_count_500m"], PALETTE["gray"],   "반경 500m 버스정류소 수",  "격자 수"),
    ("지하철거리",      df_analysis["dist_subway"],    PALETTE["teal"],   "지하철역까지 거리 (m)",    "격자 수"),
]

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
axes = axes.flatten()

for ax, (key, series, color, xlabel, ylabel) in zip(axes, vars_info):
    s = series.dropna()
    q99 = s.quantile(0.99)
    s_clip = s[s <= q99]

    counts, edges = np.histogram(s_clip, bins=20)
    mid = (edges[:-1] + edges[1:]) / 2

    ax.barh(mid, counts, height=(edges[1]-edges[0])*0.85,
            color=color, alpha=0.85, edgecolor="white", linewidth=0.5)

    mean_v, med_v = s.mean(), s.median()
    if mean_v <= q99:
        ax.axhline(mean_v, color="black", linestyle="--", linewidth=1.4,
                   label=f"평균 {mean_v:,.0f}")
    if med_v <= q99:
        ax.axhline(med_v, color="gold", linestyle=":", linewidth=1.6,
                   label=f"중앙값 {med_v:,.0f}")

    skew = s.skew()
    ax.text(0.97, 0.04, f"왜도: {skew:.2f}", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=9, color="#555555")
    ax.set_xlabel(ylabel, fontsize=10)
    ax.set_ylabel(xlabel, fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.xaxis.grid(True, linestyle=":", alpha=0.6)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)

fig.suptitle("주요 변수 분포 — 가로 히스토그램 (행정동/격자 단위)",
             fontsize=16, fontweight="bold", y=1.01)
plt.tight_layout()
p = OUT / "04_주요변수_분포_히스토그램_가로.png"
plt.savefig(p, dpi=150, bbox_inches="tight")
plt.close()
print(f"   저장: {p.name}")


# ════════════════════════════════════════════════════════════════
# ② 행정동별 65세이상 등록인구 Top 40
# ════════════════════════════════════════════════════════════════
print("② 행정동별 65세이상 등록인구 생성 중...")

df_top = df_pop.dropna(subset=["행정동명"]).sort_values("65세이상인구", ascending=False).head(40).copy()
df_top = df_top.sort_values("65세이상인구", ascending=True)
colors_bar = [
    "#1a5276" if v >= df_top["65세이상인구"].quantile(0.75) else
    "#2980b9" if v >= df_top["65세이상인구"].median() else
    "#7fb3d3"
    for v in df_top["65세이상인구"]
]

fig, ax = plt.subplots(figsize=(12, 14))
bars = ax.barh(df_top["행정동명"], df_top["65세이상인구"],
               color=colors_bar, alpha=0.9, edgecolor="white", linewidth=0.5)
for bar, gu in zip(bars, df_top["자치구"]):
    ax.text(bar.get_width() + 80, bar.get_y() + bar.get_height()/2,
            f"({gu})", va="center", fontsize=7.5, color="#777777")

mean_pop = df_pop["65세이상인구"].mean()
ax.axvline(mean_pop, color="red", linestyle="--", linewidth=1.5,
           label=f"전체 행정동 평균 {mean_pop:,.0f}명")

ax.set_xlabel("65세이상 등록인구 (명)", fontsize=12)
ax.set_title("행정동별 65세이상 등록인구 Top 40\n(2026년 4월 기준, 짙은 색 = 상위권)",
             fontsize=14, fontweight="bold", pad=12)
ax.legend(fontsize=10)
ax.xaxis.grid(True, linestyle=":", alpha=0.5)
ax.yaxis.grid(False)
ax.set_axisbelow(True)
ax.tick_params(axis="y", labelsize=9)

patch_high = mpatches.Patch(color="#1a5276", alpha=0.9, label="상위 25%")
patch_mid  = mpatches.Patch(color="#2980b9", alpha=0.9, label="25~50%")
patch_low  = mpatches.Patch(color="#7fb3d3", alpha=0.9, label="50~75%")
ax.legend(handles=[patch_high, patch_mid, patch_low,
                   mpatches.Patch(color="red", linestyle="--", fill=False,
                                  label=f"전체 평균 {mean_pop:,.0f}명")],
          fontsize=9, loc="lower right")

plt.tight_layout()
p = OUT / "05_행정동별_65세이상인구.png"
plt.savefig(p, dpi=150, bbox_inches="tight")
plt.close()
print(f"   저장: {p.name}")


# ════════════════════════════════════════════════════════════════
# ③ 행정동별 65세이상 생활인구 Top 40
# ════════════════════════════════════════════════════════════════
print("③ 행정동별 생활인구 생성 중...")

df_live2 = df_merged.dropna(subset=["생활인구_65세이상", "행정동명"])
df_live_top = df_live2.sort_values("생활인구_65세이상", ascending=False).head(40).copy()
df_live_top = df_live_top.sort_values("생활인구_65세이상", ascending=True)
colors_live = [
    "#1b5e20" if v >= df_live_top["생활인구_65세이상"].quantile(0.75) else
    "#388e3c" if v >= df_live_top["생활인구_65세이상"].median() else
    "#81c784"
    for v in df_live_top["생활인구_65세이상"]
]

fig, ax = plt.subplots(figsize=(12, 14))
bars = ax.barh(df_live_top["행정동명"], df_live_top["생활인구_65세이상"],
               color=colors_live, alpha=0.9, edgecolor="white", linewidth=0.5)
for bar, gu in zip(bars, df_live_top["자치구"]):
    ax.text(bar.get_width() + 15, bar.get_y() + bar.get_height()/2,
            f"({gu})", va="center", fontsize=7.5, color="#777777")

mean_live = df_live2["생활인구_65세이상"].mean()
ax.axvline(mean_live, color="red", linestyle="--", linewidth=1.5,
           label=f"전체 평균 {mean_live:,.0f}명")

ax.set_xlabel("65세이상 생활인구 — 시간대 평균 (명)", fontsize=12)
ax.set_title("행정동별 65세이상 생활인구 Top 40\n(2026년 4월 시간대별 평균, 짙은 색 = 상위권)",
             fontsize=14, fontweight="bold", pad=12)

patch_high = mpatches.Patch(color="#1b5e20", alpha=0.9, label="상위 25%")
patch_mid  = mpatches.Patch(color="#388e3c", alpha=0.9, label="25~50%")
patch_low  = mpatches.Patch(color="#81c784", alpha=0.9, label="50~75%")
ax.legend(handles=[patch_high, patch_mid, patch_low,
                   mpatches.Patch(color="red", linestyle="--", fill=False,
                                  label=f"전체 평균 {mean_live:,.0f}명")],
          fontsize=9, loc="lower right")
ax.xaxis.grid(True, linestyle=":", alpha=0.5)
ax.yaxis.grid(False)
ax.set_axisbelow(True)
ax.tick_params(axis="y", labelsize=9)

plt.tight_layout()
p = OUT / "06_행정동별_생활인구.png"
plt.savefig(p, dpi=150, bbox_inches="tight")
plt.close()
print(f"   저장: {p.name}")


# ════════════════════════════════════════════════════════════════
# ④ 지하철역 분포 — 노선별 역 수 + 자치구별 역 수
# ════════════════════════════════════════════════════════════════
print("④ 지하철역 분포 생성 중...")

LINE_COLOR = {
    "1호선":"#0052A4","2호선":"#009246","3호선":"#EF7C1C","4호선":"#00A2D1",
    "5호선":"#8B50A4","6호선":"#C55C1D","7호선":"#54640D","8호선":"#EA545D",
    "9호선":"#BDB092","경의중앙선":"#77C4A3","분당선":"#F5A200","경춘선":"#0C8E72",
    "우이신설선":"#B0CE18","신림선":"#6789CA","공항철도":"#4272B7",
}
def normalize_line(name):
    n = str(name).strip()
    for key in LINE_COLOR:
        if key in n:
            return key
    if "9호선" in n or "도시철도 9" in n:
        return "9호선"
    return "기타"

df_metro["노선_정규"] = df_metro["노선명"].apply(normalize_line)
# 주요 노선만
top_lines = df_metro["노선_정규"].value_counts()
top_lines = top_lines[top_lines >= 5].index.tolist()
df_metro_top = df_metro[df_metro["노선_정규"].isin(top_lines)].copy()

line_cnt = df_metro_top["노선_정규"].value_counts().sort_values(ascending=True)
gu_cnt   = df_metro["자치구"].dropna().value_counts().sort_values(ascending=False)

fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# 왼쪽: 노선별 역 수
colors_line = [LINE_COLOR.get(l, "#aaaaaa") for l in line_cnt.index]
bars = axes[0].barh(line_cnt.index, line_cnt.values,
                    color=colors_line, alpha=0.92, edgecolor="white", linewidth=0.5)
for bar, v in zip(bars, line_cnt.values):
    axes[0].text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                 str(v), va="center", fontsize=9, fontweight="bold")
axes[0].set_xlabel("역 수 (개)", fontsize=11)
axes[0].set_title("노선별 역 수 (서울 내 5역 이상 노선)", fontsize=13, fontweight="bold", pad=10)
axes[0].xaxis.grid(True, linestyle=":", alpha=0.5)
axes[0].yaxis.grid(False)
axes[0].set_axisbelow(True)

# 오른쪽: 자치구별 역 수
gu_colors = plt.cm.YlOrRd(np.linspace(0.3, 0.9, len(gu_cnt)))
bars2 = axes[1].bar(gu_cnt.index, gu_cnt.values,
                    color=gu_colors, alpha=0.9, edgecolor="white", linewidth=0.5)
mean_gu = gu_cnt.mean()
axes[1].axhline(mean_gu, color="red", linestyle="--", linewidth=1.5,
                label=f"평균 {mean_gu:.1f}개")
for bar, v in zip(bars2, gu_cnt.values):
    axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                 str(v), ha="center", va="bottom", fontsize=8.5)
axes[1].set_ylabel("역 수 (개)", fontsize=11)
axes[1].set_title("자치구별 지하철역 수", fontsize=13, fontweight="bold", pad=10)
axes[1].tick_params(axis="x", rotation=45, labelsize=9)
axes[1].legend(fontsize=10)
axes[1].yaxis.grid(True, linestyle=":", alpha=0.5)
axes[1].xaxis.grid(False)
axes[1].set_axisbelow(True)

fig.suptitle("서울시 지하철역 분포 현황 (2026년 2월 기준)",
             fontsize=15, fontweight="bold", y=1.01)
plt.tight_layout()
p = OUT / "07_지하철역_분포.png"
plt.savefig(p, dpi=150, bbox_inches="tight")
plt.close()
print(f"   저장: {p.name}")


# ════════════════════════════════════════════════════════════════
# ⑤ 이상치 탐지 — 바이올린 + 박스플롯 (로그 스케일)
# ════════════════════════════════════════════════════════════════
print("⑤ 이상치 탐지 박스플롯 개선 생성 중...")

vars_box = [
    ("65세이상 등록인구\n(명)",  df_pop["65세이상인구"].dropna(),          PALETTE["blue"]),
    ("독거노인 수\n(명)",        df_alone["독거노인_합계"].dropna(),         PALETTE["red"]),
    ("생활인구 65세+\n(명)",     df_merged["생활인구_65세이상"].dropna(),    PALETTE["green"]),
]

fig, axes = plt.subplots(1, 3, figsize=(16, 8))
fig.patch.set_facecolor("white")

for ax, (label, series, color) in zip(axes, vars_box):
    s = series.dropna().values

    # 바이올린
    parts = ax.violinplot([s], positions=[0], widths=0.6,
                          showmeans=False, showmedians=False, showextrema=False)
    for pc in parts["bodies"]:
        pc.set_facecolor(color)
        pc.set_alpha(0.35)
        pc.set_edgecolor("none")

    # 박스플롯 오버레이
    q1, med, q3 = np.percentile(s, [25, 50, 75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5*iqr, q3 + 1.5*iqr

    box = ax.boxplot([s], positions=[0], widths=0.25,
                     patch_artist=True, notch=False,
                     flierprops=dict(marker="o", markersize=3,
                                     markerfacecolor=color, alpha=0.4,
                                     markeredgewidth=0),
                     medianprops=dict(color="white", linewidth=2.5),
                     boxprops=dict(facecolor=color, alpha=0.75, linewidth=1),
                     whiskerprops=dict(color=color, linewidth=1.5),
                     capprops=dict(color=color, linewidth=2))

    # 이상치 개수
    n_out = int(((s < lo) | (s > hi)).sum())
    pct_out = n_out / len(s) * 100

    # 주요 통계 텍스트 박스
    stats_text = (
        f"n = {len(s):,}\n"
        f"중앙값: {med:,.0f}\n"
        f"Q1: {q1:,.0f}\n"
        f"Q3: {q3:,.0f}\n"
        f"최댓값: {s.max():,.0f}\n"
        f"이상치: {n_out}개 ({pct_out:.1f}%)"
    )
    ax.text(0.97, 0.97, stats_text, transform=ax.transAxes,
            va="top", ha="right", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor=color, alpha=0.9, linewidth=1.2))

    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"{int(x):,}" if x >= 1 else f"{x:.1f}"))
    ax.set_xticks([])
    ax.set_title(label, fontsize=12, fontweight="bold", pad=8)
    ax.set_ylabel("값 (로그 스케일)", fontsize=10)
    ax.set_facecolor("#f8f9fa")
    ax.yaxis.grid(True, which="both", linestyle=":", alpha=0.5, color="white")
    ax.set_axisbelow(True)
    for spine in ["top","right","bottom"]:
        ax.spines[spine].set_visible(False)

fig.suptitle("주요 변수 이상치 탐지 — 바이올린 + 박스플롯 (로그 스케일, 행정동 단위)",
             fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout(w_pad=2.5)
p = OUT / "08_이상치_탐지_박스플롯_개선.png"
plt.savefig(p, dpi=150, bbox_inches="tight")
plt.close()
print(f"   저장: {p.name}")

print("\n모두 완료!")
