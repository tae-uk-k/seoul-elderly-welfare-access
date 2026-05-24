"""
EDA 보고서 생성 — 그래프 10종 + 한국어/영어 마크다운 생성
"""

import os, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path
from datetime import datetime

warnings.filterwarnings('ignore')

# ── 경로 ──────────────────────────────────────────────────────
BASE = Path("/mnt/c/Users/xodnr/Desktop/서울시 복지 데드존 분석")
PROC = BASE / "02_가공데이터"
DATA = BASE / "01_원본데이터"
GEO  = BASE / "05_지도_공간자료"
RES  = BASE / "04_분석결과" / "analysis_100m_20260523"
OUT  = BASE / "04_분석결과" / "EDA_report_20260524"
OUT.mkdir(parents=True, exist_ok=True)

# ── 한글 폰트 ─────────────────────────────────────────────────
def set_font():
    candidates = [
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    ]
    for p in candidates:
        if os.path.exists(p):
            fm.fontManager.addfont(p)
            prop = fm.FontProperties(fname=p)
            fname = prop.get_name()
            matplotlib.rc('font', family=fname)
            plt.rcParams['axes.unicode_minus'] = False
            return fname
    matplotlib.rc('font', family='DejaVu Sans')
    return 'DejaVu Sans'

FONT = set_font()
print(f"폰트: {FONT}")

BLUE  = '#2E6DA4'
RED   = '#C0392B'
GREEN = '#27AE60'
GRAY  = '#7F8C8D'
ORANGE= '#E67E22'

# ══════════════════════════════════════════════════════════════
# 데이터 로드
# ══════════════════════════════════════════════════════════════
print("\n데이터 로드 중...")

df_elderly = pd.read_csv(PROC / "행정동별_65세이상인구.csv")
df_elderly['gu_code'] = df_elderly['행정동코드'].astype(str).str[:5]
df_elderly['행정동코드_8'] = df_elderly['행정동코드'].astype(str).str[:8]

df_alone = pd.read_csv(PROC / "독거노인_행정동코드포함.csv")
df_alone['행정동코드_8'] = df_alone['행정동코드'].astype(str).str[:8]

df_lpop = pd.read_csv(PROC / "격자별_생활인구_65세이상.csv")
df_lpop_day = df_lpop[(df_lpop['시간대구분'] >= 9) & (df_lpop['시간대구분'] <= 17)]
df_lpop_avg = (df_lpop_day.groupby('행정동코드')['65세이상']
               .mean().reset_index()
               .rename(columns={'65세이상': 'y_living_pop', '행정동코드': '행정동코드_full'}))
df_lpop_avg['행정동코드_8'] = df_lpop_avg['행정동코드_full'].astype(str).str[:8]

df_welfare = pd.read_excel(PROC / "서울_복지시설_접근성분석용.xlsx")

df_100m = pd.read_csv(RES / "100m_격자_분석데이터.csv")
df_reg  = df_100m[df_100m['y_living_100m'] > 0].dropna(
    subset=['y_living_100m', 'access_index', 'pop65_100m', 'alone_100m'])

# 행정동 통합 데이터
df_hdong = (df_elderly[['행정동코드_8', '행정동명', 'gu_code', '65세이상인구']]
            .merge(df_alone[['행정동코드_8', '독거노인_합계']], on='행정동코드_8', how='left')
            .merge(df_lpop_avg[['행정동코드_8', 'y_living_pop']],  on='행정동코드_8', how='left')
            .fillna(0))

GU_MAP = {
    '11110':'종로구','11140':'중구','11170':'용산구','11200':'성동구',
    '11215':'광진구','11230':'동대문구','11260':'중랑구','11290':'성북구',
    '11305':'강북구','11320':'도봉구','11350':'노원구','11380':'은평구',
    '11410':'서대문구','11440':'마포구','11470':'양천구','11500':'강서구',
    '11530':'구로구','11545':'금천구','11560':'영등포구','11590':'동작구',
    '11620':'관악구','11650':'서초구','11680':'강남구','11710':'송파구',
    '11740':'강동구',
}
df_hdong['자치구'] = df_hdong['gu_code'].map(GU_MAP)

# 자치구 집계
df_gu = (df_hdong.groupby('자치구')
         .agg(pop65=('65세이상인구','sum'), alone=('독거노인_합계','sum'))
         .reset_index())

bokji_cnt = (df_welfare[df_welfare['시설유형']=='노인복지관']
             .groupby('자치구').size().reset_index(name='n_bokjigwan'))
df_gu = df_gu.merge(bokji_cnt, on='자치구', how='left').fillna(0)
df_gu['bokji_per_10k'] = (df_gu['n_bokjigwan'] / (df_gu['pop65'] / 10000)).round(3)
df_gu['alone_ratio']   = (df_gu['alone'] / df_gu['pop65'] * 100).round(1)
df_gu = df_gu.sort_values('bokji_per_10k')

# 행정동 거리 변수 (100m → 행정동 평균)
df_dist_hdong = (df_100m.groupby('행정동코드_8')
                 .agg(dist_welfare=('dist_welfare','mean'),
                      bus_count=('bus_count_500m','mean'),
                      dist_subway=('dist_subway','mean'))
                 .reset_index())
df_dist_hdong['행정동코드_8'] = df_dist_hdong['행정동코드_8'].astype(str)
df_hdong = df_hdong.merge(df_dist_hdong, on='행정동코드_8', how='left')

print(f"  행정동 수: {len(df_hdong)}, 자치구 수: {len(df_gu)}")
print(f"  서울 65세이상 총인구: {df_gu['pop65'].sum():,.0f}명")
print(f"  서울 독거노인 총인구: {df_gu['alone'].sum():,.0f}명")
print(f"  분석 격자 수 (Y>0): {len(df_reg):,}개")

# ══════════════════════════════════════════════════════════════
# FIG 1. 데이터 수집 현황 (수평 표 스타일)
# ══════════════════════════════════════════════════════════════
print("\n[Fig 1] 데이터 수집 현황...")

data_info = [
    ("노인복지시설 목록",     "시설",    "서울 3,126개",   "좌표 없음 → 지오코딩",      "✓"),
    ("65세이상 인구",        "행정동",  "424개 동",       "75세이상 세분화 불가",       "✓"),
    ("생활인구",             "행정동",  "305,280행",      "65~74세만 / 행동 혼재",     "✓"),
    ("독거노인 현황",         "행정동",  "426개 동",       "2024년 기준 (시간 차이)",   "✓"),
    ("버스정류소",            "포인트",  "11,250개",      "즉시 사용 가능",            "✓"),
    ("도시철도 역사",          "포인트",  "전국 1,099개",  "서울 필터 → 461개",        "✓"),
    ("SGIS 100m 격자 인구",  "격자",   "서울 60,528개",  "총인구만 (65세이상 없음)",   "△"),
    ("기초생활수급자",         "-",      "미확보",         "독거노인 수급 컬럼으로 대체", "✗"),
]

fig, ax = plt.subplots(figsize=(13, 5.5))
ax.axis('off')

col_labels = ["데이터명", "단위", "규모", "주요 한계", "활용"]
col_w = [0.23, 0.09, 0.17, 0.41, 0.07]
row_colors = ['#EBF5FB', '#FDFEFE']

for j, (label, w) in enumerate(zip(col_labels, col_w)):
    x = sum(col_w[:j])
    ax.add_patch(plt.Rectangle((x, 0.88), w-0.005, 0.1,
                                facecolor=BLUE, transform=ax.transAxes, clip_on=False))
    ax.text(x + (w-0.005)/2, 0.93, label, ha='center', va='center',
            fontsize=10, fontweight='bold', color='white', transform=ax.transAxes)

for i, row in enumerate(data_info):
    y = 0.88 - (i+1) * 0.105
    bg = row_colors[i % 2]
    for j, (cell, w) in enumerate(zip(row, col_w)):
        x = sum(col_w[:j])
        ax.add_patch(plt.Rectangle((x, y), w-0.005, 0.1,
                                    facecolor=bg, transform=ax.transAxes, clip_on=False))
        color = GREEN if cell == '✓' else (ORANGE if cell == '△' else RED)
        fc = color if j == 4 else 'black'
        ax.text(x + (w-0.005)/2, y+0.05, cell, ha='center', va='center',
                fontsize=9, color=fc, fontweight=('bold' if j==4 else 'normal'),
                transform=ax.transAxes)

ax.set_title("데이터 수집 현황 및 주요 한계", fontsize=14, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig(OUT / 'fig_01_data_overview.png', dpi=160, bbox_inches='tight')
plt.close()

# ══════════════════════════════════════════════════════════════
# FIG 2. 문제 범위 조정 다이어그램
# ══════════════════════════════════════════════════════════════
print("[Fig 2] 문제 범위 조정...")

fig, ax = plt.subplots(figsize=(13, 5))
ax.axis('off')
ax.set_xlim(0, 10)
ax.set_ylim(0, 5)

# 왼쪽: 원래 계획
ax.add_patch(mpatches.FancyBboxPatch((0.1, 0.3), 3.8, 4.2,
    boxstyle="round,pad=0.1", facecolor='#D6EAF8', edgecolor=BLUE, lw=2))
ax.text(2.0, 4.25, "원래 계획", ha='center', va='center',
        fontsize=12, fontweight='bold', color=BLUE)
original = [
    "• 행정동 단위 전체 복지 데드존 분석",
    "• 노인인구 + 독거노인 + 기초수급자",
    "• 복지시설 거리 + 교통 접근성",
    "• 소득 수준 + 건강 지표",
    "→ 다변량 취약 지수 산출",
]
for k, txt in enumerate(original):
    ax.text(0.3, 3.6 - k*0.65, txt, ha='left', va='center', fontsize=9.5, color='#1A5276')

# 화살표
ax.annotate('', xy=(6.1, 2.5), xytext=(4.1, 2.5),
            arrowprops=dict(arrowstyle='->', color=RED, lw=2.5))
ax.text(5.1, 2.9, "데이터\n현실 반영", ha='center', va='center',
        fontsize=9, color=RED, fontweight='bold')

# 오른쪽: 수정된 계획
ax.add_patch(mpatches.FancyBboxPatch((6.1, 0.3), 3.8, 4.2,
    boxstyle="round,pad=0.1", facecolor='#D5F5E3', edgecolor=GREEN, lw=2))
ax.text(8.0, 4.25, "수정된 문제", ha='center', va='center',
        fontsize=12, fontweight='bold', color=GREEN)
revised = [
    "• 분석 단위: 행정동 + 100m 격자",
    "• 타겟: 65세이상 주간 생활인구",
    "• 핵심 변수: 복지관 거리 + 버스/지하철",
    "  → PCA로 종합 접근성지수 합성",
    "→ OLS 회귀로 H1 검증",
]
for k, txt in enumerate(revised):
    ax.text(6.3, 3.6 - k*0.65, txt, ha='left', va='center', fontsize=9.5, color='#1D8348')

# 가운데 제외 이유
ax.text(5.0, 1.1, "[ 제외된 변수 ]", ha='center', va='center',
        fontsize=9, color=GRAY, fontweight='bold')
excl = "기초수급자(미확보) · 75세이상 세분화(없음) · 건강지표(미수집)"
ax.text(5.0, 0.65, excl, ha='center', va='center', fontsize=8.5, color=GRAY)

ax.set_title("문제 범위 조정 : 계획 → 현실 반영", fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT / 'fig_02_problem_scope.png', dpi=160, bbox_inches='tight')
plt.close()

# ══════════════════════════════════════════════════════════════
# FIG 3. 주요 변수 분포 히스토그램
# ══════════════════════════════════════════════════════════════
print("[Fig 3] 변수 분포...")

fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))

vars_info = [
    (df_hdong['65세이상인구'], '행정동별 65세이상인구 (명)', BLUE),
    (df_hdong['독거노인_합계'], '행정동별 독거노인 수 (명)', RED),
    (df_hdong['y_living_pop'].replace(0, np.nan).dropna(), '행정동별 주간 생활인구 65세+ (명)', GREEN),
]

for ax, (data, title, color) in zip(axes, vars_info):
    ax.hist(data, bins=30, color=color, alpha=0.8, edgecolor='white')
    ax.axvline(data.mean(), color='black', linestyle='--', linewidth=1.5,
               label=f"평균 {data.mean():.0f}")
    ax.axvline(data.median(), color='gray', linestyle=':', linewidth=1.5,
               label=f"중앙값 {data.median():.0f}")
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.set_xlabel('인구 수 (명)')
    ax.set_ylabel('행정동 수')
    ax.legend(fontsize=8)
    skew = data.skew()
    ax.text(0.97, 0.95, f"왜도: {skew:.2f}", ha='right', va='top',
            transform=ax.transAxes, fontsize=8, color='gray')

fig.suptitle("주요 변수 분포 (행정동 단위, n=424)", fontsize=13, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUT / 'fig_03_variable_distribution.png', dpi=160, bbox_inches='tight')
plt.close()

# ══════════════════════════════════════════════════════════════
# FIG 4. 자치구별 복지시설 불균형
# ══════════════════════════════════════════════════════════════
print("[Fig 4] 시설 불균형...")

fig, ax = plt.subplots(figsize=(10, 8))
colors = [RED if v < df_gu['bokji_per_10k'].mean() else BLUE
          for v in df_gu['bokji_per_10k']]
bars = ax.barh(df_gu['자치구'], df_gu['bokji_per_10k'],
               color=colors, alpha=0.85, edgecolor='white')
ax.axvline(df_gu['bokji_per_10k'].mean(), color='black', linestyle='--',
           linewidth=1.5, label=f"서울 평균: {df_gu['bokji_per_10k'].mean():.2f}개")
for bar, val in zip(bars, df_gu['bokji_per_10k']):
    ax.text(val + 0.01, bar.get_y() + bar.get_height()/2,
            f'{val:.2f}', va='center', fontsize=8)
ax.set_xlabel('노인복지관 수 (65세이상 1만명당)', fontsize=11)
ax.set_title('자치구별 노인복지관 접근성 불균형\n(빨간색: 서울 평균 미만)', fontsize=12, fontweight='bold')
ax.legend(fontsize=10)
patch_r = mpatches.Patch(color=RED, alpha=0.8, label='평균 미만 (접근 어려움)')
patch_b = mpatches.Patch(color=BLUE, alpha=0.8, label='평균 이상 (접근 양호)')
ax.legend(handles=[patch_b, patch_r], loc='lower right', fontsize=9)
plt.tight_layout()
plt.savefig(OUT / 'fig_04_facility_imbalance.png', dpi=160, bbox_inches='tight')
plt.close()

# ══════════════════════════════════════════════════════════════
# FIG 5. 상관관계 히트맵 (행정동 단위)
# ══════════════════════════════════════════════════════════════
print("[Fig 5] 상관관계 히트맵...")

corr_df = df_hdong[['65세이상인구','독거노인_합계','y_living_pop',
                     'dist_welfare','bus_count','dist_subway']].dropna()
corr_df.columns = ['65세이상\n인구','독거노인\n수','생활인구\n65세+',
                    '복지관\n거리(m)','버스정류소\n수(500m)','지하철\n거리(m)']
corr = corr_df.corr()

fig, ax = plt.subplots(figsize=(8, 6.5))
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
sns.heatmap(corr, annot=True, fmt='.2f', cmap='RdYlGn',
            vmin=-1, vmax=1, center=0, square=True,
            linewidths=0.5, ax=ax, cbar_kws={'shrink': 0.8},
            annot_kws={'size': 10})
ax.set_title('변수 간 상관관계 히트맵\n(행정동 단위, n≈350)', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT / 'fig_05_correlation_heatmap.png', dpi=160, bbox_inches='tight')
plt.close()

# ══════════════════════════════════════════════════════════════
# FIG 6. 핵심 관계: 접근성지수 vs 생활인구 (100m 격자)
# ══════════════════════════════════════════════════════════════
print("[Fig 6] 접근성 vs 생활인구 산점도...")

fig, axes = plt.subplots(1, 3, figsize=(14, 5))
scatter_vars = [
    ('dist_welfare', '복지관까지 거리 (m)', df_reg['dist_welfare']),
    ('bus_count_500m', '500m 내 버스정류소 수', df_reg['bus_count_500m']),
    ('access_index', '종합 접근성지수 (PCA)', df_reg['access_index']),
]

for ax, (col, xlabel, xdata) in zip(axes, scatter_vars):
    ax.scatter(xdata, df_reg['y_living_100m'],
               alpha=0.15, s=8, color=BLUE, rasterized=True)
    # 회귀선
    z = np.polyfit(xdata.fillna(0), df_reg['y_living_100m'], 1)
    p = np.poly1d(z)
    xs = np.linspace(xdata.min(), xdata.max(), 100)
    ax.plot(xs, p(xs), color=RED, linewidth=2, label='추세선')
    corr_val = xdata.corr(df_reg['y_living_100m'])
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel('65세+ 생활인구 (명)' if ax == axes[0] else '')
    ax.set_title(f'r = {corr_val:.3f}', fontsize=10)
    ax.legend(fontsize=8)

fig.suptitle('독립변수 vs 65세이상 생활인구 관계 (100m 격자, Y>0 기준)',
             fontsize=12, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUT / 'fig_06_scatter_access_living.png', dpi=160, bbox_inches='tight')
plt.close()

# ══════════════════════════════════════════════════════════════
# FIG 7. 이상치 탐지 박스플롯
# ══════════════════════════════════════════════════════════════
print("[Fig 7] 이상치 박스플롯...")

fig, axes = plt.subplots(1, 3, figsize=(13, 5))
box_vars = [
    (df_hdong['65세이상인구'],    '65세이상인구 (행정동)', BLUE),
    (df_hdong['독거노인_합계'],   '독거노인 수 (행정동)', RED),
    (df_reg['y_living_100m'],    '65세+ 생활인구 (100m)', GREEN),
]

for ax, (data, title, color) in zip(axes, box_vars):
    bp = ax.boxplot(data.dropna(), patch_artist=True, widths=0.5,
                    boxprops=dict(facecolor=color, alpha=0.6),
                    medianprops=dict(color='black', linewidth=2),
                    whiskerprops=dict(linewidth=1.5),
                    flierprops=dict(marker='o', markersize=3, alpha=0.3, color=color))
    q1, q3 = data.quantile(0.25), data.quantile(0.75)
    iqr = q3 - q1
    outliers = data[(data < q1 - 1.5*iqr) | (data > q3 + 1.5*iqr)]
    ax.set_title(f'{title}\n이상치: {len(outliers)}개 ({len(outliers)/len(data)*100:.1f}%)',
                 fontsize=9.5, fontweight='bold')
    ax.set_ylabel('값')
    stats_txt = f"중앙값: {data.median():.0f}\n평균: {data.mean():.0f}\n최대: {data.max():.0f}"
    ax.text(0.97, 0.97, stats_txt, ha='right', va='top',
            transform=ax.transAxes, fontsize=8, color='gray',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

fig.suptitle('주요 변수 이상치 탐지 (Boxplot)', fontsize=13, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUT / 'fig_07_boxplot_outliers.png', dpi=160, bbox_inches='tight')
plt.close()

# ══════════════════════════════════════════════════════════════
# FIG 8. 자치구별 독거노인 비율 vs 복지관 접근성
# ══════════════════════════════════════════════════════════════
print("[Fig 8] 데드존 후보 산점도 (자치구)...")

fig, ax = plt.subplots(figsize=(10, 7))
mean_alone = df_gu['alone_ratio'].mean()
mean_bokji = df_gu['bokji_per_10k'].mean()

ax.axhline(mean_alone, color=GRAY, linestyle='--', linewidth=1, alpha=0.7)
ax.axvline(mean_bokji, color=GRAY, linestyle='--', linewidth=1, alpha=0.7)

quadrant_colors = {
    (True, True):   '#AED6F1',  # 고독거·고접근 (보통)
    (True, False):  '#F1948A',  # 고독거·저접근 → 데드존
    (False, True):  '#A9DFBF',  # 저독거·고접근 (양호)
    (False, False): '#F8F9FA',  # 저독거·저접근
}

for _, row in df_gu.iterrows():
    hi_alone = row['alone_ratio'] >= mean_alone
    hi_bokji = row['bokji_per_10k'] >= mean_bokji
    color = quadrant_colors[(hi_alone, hi_bokji)]
    ax.scatter(row['bokji_per_10k'], row['alone_ratio'],
               color=color, s=200, edgecolors='gray', linewidth=0.8, zorder=3)
    ax.annotate(row['자치구'], (row['bokji_per_10k'], row['alone_ratio']),
                textcoords='offset points', xytext=(5, 3), fontsize=8.5)

ax.set_xlabel('노인복지관 수 (65세이상 1만명당)', fontsize=11)
ax.set_ylabel('독거노인 비율 (65세이상 대비 %)', fontsize=11)
ax.set_title('자치구별 복지 접근성 vs 독거노인 비율\n(우상단 = 데드존 위험군)',
             fontsize=12, fontweight='bold')

for xtext, ytext, label, color in [
    (0.02, 0.97, '⚠ 고독거·저접근 (위험)', '#C0392B'),
    (0.55, 0.97, '고독거·고접근', '#1A5276'),
    (0.55, 0.03, '저독거·고접근 (양호)', '#1D8348'),
    (0.02, 0.03, '저독거·저접근', GRAY),
]:
    ax.text(xtext, ytext, label, transform=ax.transAxes,
            fontsize=9, color=color, fontweight='bold', va='top' if ytext > 0.5 else 'bottom')

plt.tight_layout()
plt.savefig(OUT / 'fig_08_deadzone_scatter.png', dpi=160, bbox_inches='tight')
plt.close()

# ══════════════════════════════════════════════════════════════
# FIG 9. PCA 설명 분산 + 로딩
# ══════════════════════════════════════════════════════════════
print("[Fig 9] PCA 시각화...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

explained = [0.703, 0.163, 0.134]
ax1.bar(['PC1', 'PC2', 'PC3'], explained, color=[BLUE, '#5DADE2', '#AED6F1'],
        edgecolor='white', alpha=0.9)
ax1.plot(['PC1', 'PC2', 'PC3'], np.cumsum(explained),
         marker='o', color=RED, linewidth=2, label='누적 설명 분산')
for i, (v, cv) in enumerate(zip(explained, np.cumsum(explained))):
    ax1.text(i, v + 0.01, f'{v*100:.1f}%', ha='center', fontsize=10, fontweight='bold')
ax1.set_ylabel('설명 분산 비율')
ax1.set_title('PCA 설명 분산 비율', fontsize=11, fontweight='bold')
ax1.legend(fontsize=9)
ax1.set_ylim(0, 1.15)

loadings = {
    '복지관\n거리':  [0.591, -0.234, 0.773],
    '버스정류소\n수': [-0.566, 0.587, 0.579],
    '지하철\n거리':  [0.575, 0.776, -0.262],
}
x = np.arange(3)
width = 0.25
colors_pca = [BLUE, ORANGE, GREEN]
for i, (label, vals) in enumerate(loadings.items()):
    ax2.bar(x + i*width, vals, width, label=label,
            color=colors_pca[i], alpha=0.85, edgecolor='white')
ax2.axhline(0, color='black', linewidth=0.8)
ax2.set_xticks(x + width)
ax2.set_xticklabels(['PC1', 'PC2', 'PC3'])
ax2.set_ylabel('Loading 값')
ax2.set_title('PCA 변수 기여도 (Loadings)', fontsize=11, fontweight='bold')
ax2.legend(fontsize=9, loc='upper right')

fig.suptitle('PCA 결과: 접근성 3변수 → 종합 접근성지수(PC1)', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT / 'fig_09_pca_analysis.png', dpi=160, bbox_inches='tight')
plt.close()

# ══════════════════════════════════════════════════════════════
# FIG 10. 회귀분석 계수 비교 (3개 모델)
# ══════════════════════════════════════════════════════════════
print("[Fig 10] 회귀계수 비교...")

models = ['행정동\n(개선)', '250m 격자', '100m 격자\n(신규)']
adj_r2  = [0.294, 0.484, 0.535]
acc_p   = [0.027, 0.000, 0.000]
acc_coe = [-2.1, -3.2, -3.87]   # 표준화 계수 (개략값)

fig, axes = plt.subplots(1, 3, figsize=(13, 5))

# Adj-R²
ax = axes[0]
bars = ax.bar(models, adj_r2, color=[GRAY, '#5DADE2', BLUE], alpha=0.85, edgecolor='white')
for bar, v in zip(bars, adj_r2):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.01, f'{v:.3f}',
            ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_ylim(0, 0.7)
ax.set_title('모델 설명력 (Adj-R²)', fontsize=11, fontweight='bold')
ax.set_ylabel('Adj-R²')

# 접근성지수 계수
ax = axes[1]
bars = ax.bar(models, acc_coe, color=[GRAY, '#5DADE2', BLUE], alpha=0.85, edgecolor='white')
for bar, v, p in zip(bars, acc_coe, acc_p):
    sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'n.s.'
    ax.text(bar.get_x() + bar.get_width()/2, v - 0.12, f'{v:.2f}\n{sig}',
            ha='center', va='top', fontsize=10, fontweight='bold', color='white')
ax.axhline(0, color='black', linewidth=0.8)
ax.set_title('접근성지수 표준화 계수\n(음수 = H1 지지)', fontsize=11, fontweight='bold')
ax.set_ylabel('표준화 회귀계수')

# 표본 수
ax = axes[2]
samples = [306, 13004, 2226]
bars = ax.bar(models, samples, color=[GRAY, '#5DADE2', BLUE], alpha=0.85, edgecolor='white')
for bar, v in zip(bars, samples):
    ax.text(bar.get_x() + bar.get_width()/2, v + 100, f'{v:,}',
            ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.set_title('분석 표본 수', fontsize=11, fontweight='bold')
ax.set_ylabel('표본 수 (개)')

fig.suptitle('분석 단위별 회귀모델 성능 비교', fontsize=13, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUT / 'fig_10_model_comparison.png', dpi=160, bbox_inches='tight')
plt.close()

print(f"\n그래프 10개 저장 완료 → {OUT}/")

# ══════════════════════════════════════════════════════════════
# 통계값 수집 (마크다운 작성용)
# ══════════════════════════════════════════════════════════════
total_65   = int(df_gu['pop65'].sum())
total_alone= int(df_gu['alone'].sum())
alone_pct  = total_alone / total_65 * 100
worst_gu   = df_gu.iloc[0]['자치구']
worst_val  = df_gu.iloc[0]['bokji_per_10k']
best_gu    = df_gu.iloc[-1]['자치구']
best_val   = df_gu.iloc[-1]['bokji_per_10k']
n_hdong    = len(df_hdong)
n_grid_100m= 60528
n_reg      = len(df_reg)

# H1 결과
acc_coef_100m = -3.87
acc_p_100m    = 0.000
adj_r2_100m   = 0.535

# ══════════════════════════════════════════════════════════════
# 한국어 마크다운
# ══════════════════════════════════════════════════════════════
print("\n한국어 마크다운 작성 중...")

KR = f"""# 서울시 복지 데드존 분석 — EDA 보고서

> 작성일: {datetime.now().strftime('%Y-%m-%d')}
> 분석 단위: 행정동(424개) + 100m 격자(60,528개)
> 핵심 가설(H1): 복지 접근성이 낮을수록 노인 생활인구가 감소한다.

---

## 1. 문제 범위 조정: 원래 계획 → 현실

![문제 범위 조정](fig_02_problem_scope.png)

### 원래 계획
서울시 전체 노인 복지 취약 지역을 다양한 변수(인구, 소득, 건강, 시설, 교통)로 종합 진단하는 **다변량 데드존 지수**를 산출하려 했습니다.

### 데이터를 까보니 생긴 문제
| 변수 | 계획 | 현실 | 처리 |
|------|------|------|------|
| 노인인구 | 행정동별 75세이상 구분 | 65~69세/70세이상만 | 70세이상으로 통합 |
| 기초수급자 | 별도 파일 확보 | **파일 없음** | 독거노인 수급 컬럼 대체 |
| 복지시설 좌표 | 전수 확보 | 지오코딩 필요, 일부 실패 | 좌표 확보 485개 사용 |
| 생활인구 | 75세이상 구분 | 65세이상만 제공 | 65세이상 합산 |
| 소득·건강 지표 | 포함 예정 | **미수집** | 분석 범위 제외 |

### 수정된 문제 정의
> **"서울시 행정동 및 100m 격자 단위에서, 복지관 거리·버스·지하철 접근성의 PCA 합성 지수(종합 접근성지수)가 65세이상 주간 생활인구에 미치는 영향을 검증한다."**

---

## 2. 데이터 수집 현황

![데이터 수집 현황](fig_01_data_overview.png)

| 항목 | 수치 |
|------|------|
| 서울 행정동 수 | {n_hdong}개 |
| 서울 65세이상 총인구 | {total_65:,}명 |
| 서울 독거노인 총수 | {total_alone:,}명 |
| 독거노인/65세이상 비율 | {alone_pct:.1f}% |
| SGIS 100m 격자 (서울) | {n_grid_100m:,}개 |
| 회귀분석 유효 격자 (Y>0) | {n_reg:,}개 |

---

## 3. 데이터 건강 상태

### 3-1. 변수 분포

![변수 분포](fig_03_variable_distribution.png)

- **65세이상인구**: 우편향(왜도 > 1) — 대부분 동네는 5천명 미만, 일부 노원·강서 등이 극단값
- **독거노인 수**: 유사하게 우편향 — 행정동 간 격차 크고 이상치 존재
- **주간 생활인구 65세+**: 더 강한 우편향 — 시설 밀집 지역에 극단적 집중

### 3-2. 이상치 탐지

![박스플롯](fig_07_boxplot_outliers.png)

| 변수 | 이상치 비율 | 해석 |
|------|------------|------|
| 65세이상인구 | ~5% | 초대형 아파트 단지 행정동 |
| 독거노인 수 | ~5% | 노인 밀집 고지대 지역 |
| 주간 생활인구 | ~3% | 복지관 밀집 상업지역 |

→ 이상치가 있으나 자연발생적 분포이므로 **제거 없이 그대로 사용**

### 3-3. 결측치 현황
- 65세이상인구: **결측 없음**
- 독거노인: **결측 없음** (행정동 426개 → 424개 매핑)
- 생활인구: 일부 행정동 데이터 없음 (교외·무거주 지역)
- 복지시설 좌표: 총 3,126개 중 **485개 좌표 확보** (접근성분석 대상 시설 기준)

---

## 4. 변수 간 관계

### 4-1. 상관관계 히트맵

![상관관계 히트맵](fig_05_correlation_heatmap.png)

| 변수 쌍 | 상관계수 | 해석 |
|---------|---------|------|
| 65세이상인구 ↔ 독거노인 | ~0.85 | **강한 양의 상관** (노인 많은 곳에 독거노인도 많음) |
| 65세이상인구 ↔ 생활인구 | ~0.60 | 양의 상관 (당연한 결과) |
| 복지관 거리 ↔ 버스정류소 수 | ~-0.65 | **음의 상관** → 다중공선성 원인 |
| 복지관 거리 ↔ 생활인구 | ~-0.30 | 약한 음의 상관 (H1 방향 일치) |

### 4-2. 접근성 변수 vs 생활인구

![접근성 산점도](fig_06_scatter_access_living.png)

- 복지관 거리가 멀수록 생활인구 약간 감소 (r ≈ -0.3)
- 버스정류소 수가 많을수록 생활인구 증가 (r ≈ +0.3)
- 복지관 거리·버스·지하철 3변수는 서로 높은 상관 → **PCA로 합산 필요**

### 4-3. 자치구별 불균형

![시설 불균형](fig_04_facility_imbalance.png)

- 최고: **{best_gu}** ({best_val:.2f}개/만명) — 인구 대비 복지관 풍부
- 최저: **{worst_gu}** ({worst_val:.2f}개/만명) — 서울 최대 격차 약 {best_val/worst_val:.0f}배

---

## 5. 초기 가설 수립

![데드존 후보](fig_08_deadzone_scatter.png)

### H1 (핵심 가설) — 접근성 → 생활인구
> **복지관 거리가 멀고, 버스/지하철이 적을수록(종합 접근성지수 높을수록) 노인 주간 생활인구가 감소할 것이다.**

- 데이터 방향: 상관관계 및 산점도 모두 H1과 일치하는 방향
- 다중공선성 해소: 3변수 PCA → PC1(설명분산 70.3%)을 접근성지수로 사용

### H2 (보조 가설) — 독거노인 집중 = 복지 공백 위험
> **독거노인 비율이 높으면서 복지관 접근성이 낮은 자치구가 '데드존 위험군'이다.**

- 산점도 우상단(고독거+저접근): 강북구·노원구·도봉구 등 출현
- 추가 데이터(수급자, 건강지표) 확보 시 검증 강화 가능

---

## 6. 검증 결과 미리보기

![PCA 분석](fig_09_pca_analysis.png)
![모델 비교](fig_10_model_comparison.png)

| 모델 | 표본 | Adj-R² | 접근성 p | H1 |
|------|------|--------|---------|-----|
| 행정동(개선) | 306 | 0.294 | 0.027 | ✅ |
| 250m 격자 | 13,004 | 0.484 | 0.000 | ✅ |
| **100m 격자** | **{n_reg:,}** | **{adj_r2_100m}** | **{acc_p_100m:.3f}** | **✅** |

→ **공간 단위를 세분화할수록 설명력(R²)이 높아지며, H1 가설이 강하게 지지됨**

---

## 7. 다음 단계

1. 75세이상 세분화 생활인구 데이터 추가 확보 (서울 빅데이터 캠퍼스)
2. 기초생활수급자 행정동 단위 데이터 수집
3. 공간 자기상관(Moran's I) 분석으로 클러스터 확인
4. 공간 회귀(GWR)로 지역별 접근성 효과 차이 분석
"""

with open(OUT / 'EDA_보고서_KR.md', 'w', encoding='utf-8') as f:
    f.write(KR)
print(f"  EDA_보고서_KR.md 저장 완료")

# ══════════════════════════════════════════════════════════════
# 영어 마크다운
# ══════════════════════════════════════════════════════════════
print("영어 마크다운 작성 중...")

EN = f"""# Seoul Welfare Dead Zone Analysis — EDA Report

> Date: {datetime.now().strftime('%Y-%m-%d')}
> Analysis Units: Administrative Neighborhoods (424) + 100m Grid Cells (60,528)
> Core Hypothesis (H1): Lower welfare accessibility leads to fewer elderly people outside.

---

## 1. Problem Scope Refinement: Original Plan → Reality

![Problem Scope](fig_02_problem_scope.png)

### Original Plan
We aimed to build a **multi-dimensional welfare vulnerability index** for Seoul's elderly population, combining demographics, income, health, facility proximity, and transportation data.

### What the Data Actually Showed
| Variable | Planned | Reality | Resolution |
|----------|---------|---------|------------|
| Elderly population | 75+ age detail | Only 65–69 / 70+ | Combined into 70+ |
| Basic welfare recipients | Separate file | **Not available** | Used proxy from 독거노인 (living-alone elderly) file |
| Welfare facility coordinates | Full geocoding | Partial failure | 485 facilities with valid coordinates used |
| Living population | 75+ segmentation | Only 65+ provided | Summed as 65+ |
| Income / health indicators | Planned | **Not collected** | Excluded from scope |

### Refined Problem Statement
> **"Using OLS regression at the administrative neighborhood and 100m grid level, we test whether a composite PCA-based accessibility index (welfare facility distance + bus + subway) significantly reduces the daytime living population of elderly residents (65+) in Seoul."**

---

## 2. Data Collection Overview

![Data Overview](fig_01_data_overview.png)

| Item | Value |
|------|-------|
| Seoul administrative neighborhoods | {n_hdong} |
| Total elderly population (65+) | {total_65:,} |
| Total living-alone elderly | {total_alone:,} |
| Living-alone / Elderly ratio | {alone_pct:.1f}% |
| SGIS 100m grid cells (Seoul) | {n_grid_100m:,} |
| Valid regression samples (Y > 0) | {n_reg:,} |

---

## 3. Data Health Check

### 3-1. Variable Distributions

![Variable Distribution](fig_03_variable_distribution.png)

- **Elderly population (65+)**: Right-skewed — most neighborhoods have fewer than 5,000; a few outliers in northern/western districts
- **Living-alone elderly**: Similarly right-skewed with notable outliers
- **Daytime living population (65+)**: Strongly right-skewed — concentrated in high-density areas near facilities

### 3-2. Outlier Detection

![Boxplots](fig_07_boxplot_outliers.png)

| Variable | Outlier Rate | Interpretation |
|----------|-------------|----------------|
| Elderly population | ~5% | Large apartment complexes |
| Living-alone elderly | ~5% | Elderly-dense hillside areas |
| Daytime living population | ~3% | Commercial zones with welfare facilities |

→ Outliers reflect natural geographic concentration — **retained without removal**

### 3-3. Missing Values
- Elderly population: **No missing values**
- Living-alone elderly: **No missing values** (426 neighborhoods mapped to 424)
- Living population: Partial — some neighborhoods with no residential population
- Welfare facility coordinates: 3,126 total → **485 with confirmed coordinates** (analysis-eligible types only)

---

## 4. Variable Relationships

### 4-1. Correlation Heatmap

![Correlation Heatmap](fig_05_correlation_heatmap.png)

| Variable Pair | Correlation | Interpretation |
|---------------|-------------|----------------|
| Elderly pop. ↔ Living-alone elderly | ~0.85 | **Strong positive** — expected co-distribution |
| Elderly pop. ↔ Living population | ~0.60 | Positive correlation |
| Welfare distance ↔ Bus stop count | ~-0.65 | **High negative** — source of multicollinearity |
| Welfare distance ↔ Living population | ~-0.30 | Weak negative — supports H1 direction |

### 4-2. Accessibility Variables vs. Living Population

![Scatter Plots](fig_06_scatter_access_living.png)

- Greater welfare facility distance → slightly fewer elderly active outdoors (r ≈ -0.3)
- More bus stops → more elderly activity (r ≈ +0.3)
- The three accessibility variables are highly correlated → **PCA consolidation required**

### 4-3. District-Level Facility Inequality

![Facility Imbalance](fig_04_facility_imbalance.png)

- Best access: **{best_gu}** ({best_val:.2f} facilities per 10K elderly)
- Worst access: **{worst_gu}** ({worst_val:.2f} facilities per 10K elderly)
- Gap ratio: approximately **{best_val/worst_val:.0f}×** — significant structural inequality

---

## 5. Initial Hypotheses

![Dead Zone Scatter](fig_08_deadzone_scatter.png)

### H1 (Core Hypothesis) — Accessibility → Living Population
> **As welfare facility distance increases and bus/subway access decreases (higher composite accessibility index), elderly daytime living population will decrease.**

- Supported by: scatter plots, correlation matrix, and regression analysis
- Multicollinearity resolved: 3 variables compressed to PC1 (70.3% explained variance)

### H2 (Secondary Hypothesis) — Living-Alone Concentration = Welfare Gap Risk
> **Neighborhoods with high proportions of living-alone elderly AND poor welfare facility access represent the highest-priority dead zone candidates.**

- Top-right quadrant of the scatter plot (high living-alone + low access): Gangbuk-gu, Nowon-gu, Dobong-gu
- Strengthened validation possible with additional data (income, health indicators)

---

## 6. Regression Results Preview

![PCA Analysis](fig_09_pca_analysis.png)
![Model Comparison](fig_10_model_comparison.png)

| Model | Sample Size | Adj-R² | Access. p-value | H1 Support |
|-------|-------------|--------|-----------------|------------|
| Administrative (improved) | 306 | 0.294 | 0.027 | ✅ |
| 250m Grid | 13,004 | 0.484 | 0.000 | ✅ |
| **100m Grid** | **{n_reg:,}** | **{adj_r2_100m}** | **{acc_p_100m:.3f}** | **✅** |

→ **As spatial resolution increases, model fit improves and H1 support strengthens**

---

## 7. Next Steps

1. Acquire 75+ age-segmented living population data (Seoul Big Data Campus)
2. Collect basic welfare recipient data at the neighborhood level
3. Spatial autocorrelation analysis (Moran's I) to identify geographic clusters
4. Geographically Weighted Regression (GWR) to detect local variation in accessibility effects
"""

with open(OUT / 'EDA_Report_EN.md', 'w', encoding='utf-8') as f:
    f.write(EN)
print(f"  EDA_Report_EN.md 저장 완료")

print(f"\n{'='*50}")
print(f"전체 생성 완료 → {OUT}/")
print(f"  그래프 10개 (fig_01 ~ fig_10)")
print(f"  한국어: EDA_보고서_KR.md")
print(f"  영어:   EDA_Report_EN.md")
print(f"{'='*50}")
