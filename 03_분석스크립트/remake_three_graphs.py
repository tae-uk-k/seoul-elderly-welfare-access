"""
그래프 3종 재생성 스크립트 (한글 폰트 수정 버전)
- 그래프_복지시설_거리분포_히스토그램.png
- 그래프_지표간_상관관계_히트맵.png
- 그래프_시설_불균형_현황.png
"""

import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path

# ── 한글 폰트 등록 ────────────────────────────────────────────────
FONT_PATH = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
fm.fontManager.addfont(FONT_PATH)
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

BASE = Path("/mnt/c/Users/xodnr/Desktop/서울시 복지 데드존 분석")
OUT  = BASE / "04_분석결과"

SEOUL_25 = [
    "강남구","강동구","강북구","강서구","관악구","광진구","구로구","금천구",
    "노원구","도봉구","동대문구","동작구","마포구","서대문구","서초구","성동구",
    "성북구","송파구","양천구","영등포구","용산구","은평구","종로구","중구","중랑구",
]

# ── 데이터 로드 ───────────────────────────────────────────────────
df_facility = pd.read_excel(BASE / "02_가공데이터/서울_노인복지시설_정제.xlsx")

df_pop_raw = pd.read_csv(BASE / "02_가공데이터/행정동별_65세이상인구.csv")
df_pop_raw["자치구"] = (
    df_pop_raw["행정구역"]
    .str.extract(r"서울특별시\s+(\S+구)")[0]
)
df_pop_gu = (
    df_pop_raw.groupby("자치구")["65세이상인구"]
    .sum()
    .reset_index()
    .rename(columns={"65세이상인구": "pop_65plus"})
)

df_alone_raw = pd.read_csv(BASE / "02_가공데이터/독거노인_행정동코드포함.csv")
df_alone_raw["행정동코드"] = df_alone_raw["행정동코드"].astype(str).str.replace(r"\.0$", "", regex=True).str[:8]
df_alone_raw["구코드"] = df_alone_raw["행정동코드"].str[:5]

GU_CODE5 = {
    "11110":"종로구","11140":"중구","11170":"용산구","11200":"성동구",
    "11215":"광진구","11230":"동대문구","11260":"중랑구","11290":"성북구",
    "11305":"강북구","11320":"도봉구","11350":"노원구","11380":"은평구",
    "11410":"서대문구","11440":"마포구","11470":"양천구","11500":"강서구",
    "11530":"구로구","11545":"금천구","11560":"영등포구","11590":"동작구",
    "11620":"관악구","11650":"서초구","11680":"강남구","11710":"송파구","11740":"강동구",
}
df_alone_raw["자치구"] = df_alone_raw["구코드"].map(GU_CODE5)
df_alone_gu = (
    df_alone_raw.groupby("자치구")["독거노인_합계"]
    .sum()
    .reset_index()
    .rename(columns={"독거노인_합계": "alone_elder"})
)

# 복지시설 유형별 자치구 집계
is_bokjigwan = df_facility["시설유형"].str.contains("복지관", na=False)
is_yoyang    = df_facility["시설유형"].str.contains("요양", na=False)
df_bokjigwan_gu = (
    df_facility[is_bokjigwan].groupby("자치구").size()
    .reset_index(name="n_bokjigwan")
)
df_yoyang_gu = (
    df_facility[is_yoyang].groupby("자치구").size()
    .reset_index(name="n_yoyang")
)

# 통합 데이터프레임
df = pd.DataFrame({"자치구": SEOUL_25})
df = df.merge(df_pop_gu, on="자치구", how="left")
df = df.merge(df_bokjigwan_gu, on="자치구", how="left")
df = df.merge(df_yoyang_gu, on="자치구", how="left")
df = df.merge(df_alone_gu, on="자치구", how="left")
df = df.fillna(0)

df["복지관_만명당"]  = (df["n_bokjigwan"] / (df["pop_65plus"] / 10_000)).round(3)
df["요양_만명당"]    = (df["n_yoyang"]    / (df["pop_65plus"] / 10_000)).round(3)
df["접근성_부족지수"] = (1 / df["복지관_만명당"].replace(0, np.nan)).round(4)


# ══════════════════════════════════════════════════════════════════
# 그래프 1 — 복지시설 거리분포 (접근성 부족 지수 막대)
# ══════════════════════════════════════════════════════════════════
df1 = df.sort_values("접근성_부족지수", ascending=True)

fig, ax = plt.subplots(figsize=(9, 7))
bars = ax.barh(df1["자치구"], df1["접근성_부족지수"], color="steelblue", alpha=0.85)
mean_val = df1["접근성_부족지수"].mean()
ax.axvline(mean_val, color="red", linestyle="--", linewidth=1.5,
           label=f"서울 평균 {mean_val:.2f}")
ax.set_xlabel("접근성 부족 지수 (1 / 복지관 밀도, 값 클수록 접근 어려움)", fontsize=11)
ax.set_title("자치구별 노인복지관 접근성 부족 지수", fontsize=14, fontweight="bold", pad=12)
ax.legend(fontsize=10)
ax.xaxis.grid(True, linestyle=":", alpha=0.5)
ax.set_axisbelow(True)
plt.tight_layout()
save1 = OUT / "그래프_복지시설_거리분포_히스토그램.png"
plt.savefig(save1, dpi=150, bbox_inches="tight")
plt.close()
print(f"저장: {save1.name}")


# ══════════════════════════════════════════════════════════════════
# 그래프 2 — 지표간 상관관계 히트맵
# ══════════════════════════════════════════════════════════════════
corr_df = df[["pop_65plus", "alone_elder", "n_bokjigwan", "n_yoyang", "접근성_부족지수"]].copy()
corr_df.columns = [
    "65세+\n등록인구", "독거노인\n합계",
    "복지관\n개수", "요양시설\n개수", "접근성\n부족지수",
]
corr_mat = corr_df.corr()

fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(
    corr_mat, annot=True, fmt=".2f", cmap="RdYlGn",
    vmin=-1, vmax=1, center=0, square=True,
    linewidths=0.5, linecolor="#cccccc",
    ax=ax, cbar_kws={"shrink": 0.8},
    annot_kws={"size": 11},
)
ax.set_title("주요 지표 간 상관관계\n(자치구 단위, n=25)", fontsize=13, fontweight="bold", pad=12)
plt.tight_layout()
save2 = OUT / "그래프_지표간_상관관계_히트맵.png"
plt.savefig(save2, dpi=150, bbox_inches="tight")
plt.close()
print(f"저장: {save2.name}")


# ══════════════════════════════════════════════════════════════════
# 그래프 3 — 시설 불균형 현황
# ══════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 1, figsize=(13, 11))

# 상단: 복지관
df3a = df.sort_values("복지관_만명당", ascending=False)
axes[0].bar(df3a["자치구"], df3a["복지관_만명당"], color="steelblue", alpha=0.85)
mean_a = df3a["복지관_만명당"].mean()
axes[0].axhline(mean_a, color="red", linestyle="--", linewidth=1.5,
                label=f"서울 평균 {mean_a:.2f}개")
axes[0].set_title("자치구별 65세+ 1만 명당 노인복지관 수", fontsize=12, fontweight="bold")
axes[0].set_ylabel("개수 (1만 명당)", fontsize=10)
axes[0].tick_params(axis="x", rotation=45, labelsize=9)
axes[0].legend(fontsize=10)
axes[0].yaxis.grid(True, linestyle=":", alpha=0.5)
axes[0].set_axisbelow(True)

# 하단: 요양시설
df3b = df.sort_values("요양_만명당", ascending=False)
axes[1].bar(df3b["자치구"], df3b["요양_만명당"], color="coral", alpha=0.85)
mean_b = df3b["요양_만명당"].mean()
axes[1].axhline(mean_b, color="red", linestyle="--", linewidth=1.5,
                label=f"서울 평균 {mean_b:.2f}개")
axes[1].set_title("자치구별 65세+ 1만 명당 노인요양시설 수", fontsize=12, fontweight="bold")
axes[1].set_ylabel("개수 (1만 명당)", fontsize=10)
axes[1].tick_params(axis="x", rotation=45, labelsize=9)
axes[1].legend(fontsize=10)
axes[1].yaxis.grid(True, linestyle=":", alpha=0.5)
axes[1].set_axisbelow(True)

fig.suptitle("서울시 노인복지시설 집중도 불균형", fontsize=14, fontweight="bold", y=1.01)
plt.tight_layout()
save3 = OUT / "그래프_시설_불균형_현황.png"
plt.savefig(save3, dpi=150, bbox_inches="tight")
plt.close()
print(f"저장: {save3.name}")

print("\n완료.")
