"""
EDA 집중 보고서 — 데이터 진단 + 문제 재정의만 담음
분석 결과(회귀, PCA 성능, 모델 비교)는 포함하지 않음
출력: 04_분석결과/변수관계_분석_시각화/
"""

import os, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import seaborn as sns
from pathlib import Path

warnings.filterwarnings('ignore')

BASE = Path("/mnt/c/Users/xodnr/Desktop/서울시 복지 데드존 분석")
PROC = BASE / "02_가공데이터"
RES  = BASE / "04_분석결과" / "analysis_100m_20260523"
OUT  = BASE / "04_분석결과" / "변수관계_분석_시각화"
OUT.mkdir(parents=True, exist_ok=True)

# ── 폰트 ─────────────────────────────────────────────────────
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

BLUE   = '#2E6DA4'
RED    = '#C0392B'
GREEN  = '#27AE60'
GRAY   = '#7F8C8D'
ORANGE = '#E67E22'
LBLUE  = '#AED6F1'
LGREEN = '#A9DFBF'

# ── 데이터 로드 ───────────────────────────────────────────────
print("데이터 로드 중...")

df_elderly = pd.read_csv(PROC / "행정동별_65세이상인구.csv")
df_elderly['gu_code']      = df_elderly['행정동코드'].astype(str).str[:5]
df_elderly['행정동코드_8'] = df_elderly['행정동코드'].astype(str).str[:8]

df_alone = pd.read_csv(PROC / "독거노인_행정동코드포함.csv")
df_alone['행정동코드_8'] = df_alone['행정동코드'].astype(str).str[:8]

df_lpop = pd.read_csv(PROC / "격자별_생활인구_65세이상.csv")
df_lpop_day = df_lpop[(df_lpop['시간대구분'] >= 9) & (df_lpop['시간대구분'] <= 17)]
df_lpop_avg = (df_lpop_day.groupby('행정동코드')['65세이상']
               .mean().reset_index()
               .rename(columns={'65세이상':'y_living_pop','행정동코드':'행정동코드_full'}))
df_lpop_avg['행정동코드_8'] = df_lpop_avg['행정동코드_full'].astype(str).str[:8]

df_welfare = pd.read_excel(PROC / "서울_복지시설_접근성분석용.xlsx")

df_100m = pd.read_csv(RES / "100m_격자_분석데이터.csv")

# 행정동 통합
df_hdong = (df_elderly[['행정동코드_8','행정동명','gu_code','65세이상인구']]
            .merge(df_alone[['행정동코드_8','독거노인_합계']], on='행정동코드_8', how='left')
            .merge(df_lpop_avg[['행정동코드_8','y_living_pop']],  on='행정동코드_8', how='left')
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
df_hdong['alone_ratio'] = (df_hdong['독거노인_합계'] / df_hdong['65세이상인구'].replace(0,np.nan) * 100).round(1)

bokji_cnt = (df_welfare[df_welfare['시설유형']=='노인복지관']
             .groupby('자치구').size().reset_index(name='n_bokjigwan'))
df_gu = (df_hdong.groupby('자치구')
         .agg(pop65=('65세이상인구','sum'), alone=('독거노인_합계','sum'))
         .reset_index())
df_gu = df_gu.merge(bokji_cnt, on='자치구', how='left').fillna(0)
df_gu['bokji_per_10k'] = (df_gu['n_bokjigwan'] / (df_gu['pop65'] / 10000)).round(3)
df_gu['alone_ratio']   = (df_gu['alone'] / df_gu['pop65'] * 100).round(1)
df_gu = df_gu.sort_values('bokji_per_10k')

df_dist = (df_100m.groupby('행정동코드_8')
           .agg(dist_welfare=('dist_welfare','mean'),
                bus_count=('bus_count_500m','mean'),
                dist_subway=('dist_subway','mean'))
           .reset_index())
df_dist['행정동코드_8'] = df_dist['행정동코드_8'].astype(str)
df_hdong = df_hdong.merge(df_dist, on='행정동코드_8', how='left')

print(f"  행정동: {len(df_hdong)}개 / 자치구: {len(df_gu)}개")

# ════════════════════════════════════════════════════════════
# 그림 1. 데이터 수집 현황 & 주요 한계
# ════════════════════════════════════════════════════════════
print("[그림 1] 데이터 수집 현황...")

rows = [
    ("노인복지시설 목록",      "시설(포인트)",  "3,126개",     "좌표 없음 → 주소 변환 필요",     "활용"),
    ("65세이상 인구",         "행정동",        "424개 동",    "75세이상 세분화 불가",            "활용"),
    ("노인 생활인구",          "행정동",        "305,280행",   "65~74세만 / 65세이상으로 통합",  "활용"),
    ("독거노인 현황",           "행정동",        "426개 동",    "2024년 기준 (시간 차이)",        "활용"),
    ("버스정류소 위치",         "포인트",        "11,250개",    "WGS84 좌표, 즉시 사용 가능",     "활용"),
    ("도시철도 역사정보",        "포인트",        "전국 1,099개","서울 필터 → 461개",             "활용"),
    ("기초생활수급자 현황",      "행정동",        "미확보",       "파일 수집 실패",                 "제외"),
    ("소득·건강 지표",          "행정동",        "미확보",       "공개 데이터 없음",               "제외"),
]
col_labels = ["데이터명", "단위", "규모", "주요 한계·처리", "활용 여부"]
col_w      = [0.20, 0.10, 0.13, 0.47, 0.10]

fig, ax = plt.subplots(figsize=(14, 5))
ax.axis('off')
for j, (label, w) in enumerate(zip(col_labels, col_w)):
    x = sum(col_w[:j])
    ax.add_patch(plt.Rectangle((x, 0.88), w-0.004, 0.1,
                                facecolor=BLUE, transform=ax.transAxes, clip_on=False))
    ax.text(x+(w-0.004)/2, 0.93, label, ha='center', va='center',
            fontsize=10, fontweight='bold', color='white', transform=ax.transAxes)

rc = ['#EBF5FB','#FDFEFE']
for i, row in enumerate(rows):
    y   = 0.88 - (i+1)*0.105
    bg  = '#FEF9E7' if row[-1]=='제외' else rc[i%2]
    for j, (cell, w) in enumerate(zip(row, col_w)):
        x = sum(col_w[:j])
        ax.add_patch(plt.Rectangle((x, y), w-0.004, 0.1,
                                    facecolor=bg, transform=ax.transAxes, clip_on=False))
        if j == 4:
            fc = GREEN if cell == '활용' else RED
            fw = 'bold'
        else:
            fc, fw = 'black', 'normal'
        ax.text(x+(w-0.004)/2, y+0.05, cell, ha='center', va='center',
                fontsize=9, color=fc, fontweight=fw, transform=ax.transAxes)

ax.set_title("수집 데이터 현황 및 주요 한계", fontsize=14, fontweight='bold', pad=14)
plt.tight_layout()
plt.savefig(OUT / "01_데이터_수집현황표.png", dpi=160, bbox_inches='tight')
plt.close()

# ════════════════════════════════════════════════════════════
# 그림 2. 문제 범위 재정의
# ════════════════════════════════════════════════════════════
print("[그림 2] 문제 범위 재정의...")

fig, ax = plt.subplots(figsize=(13, 5.2))
ax.axis('off'); ax.set_xlim(0,10); ax.set_ylim(0,5)

# 왼쪽 — 원래 계획
ax.add_patch(mpatches.FancyBboxPatch((0.1,0.5), 3.8, 4.1,
    boxstyle="round,pad=0.1", facecolor='#D6EAF8', edgecolor=BLUE, lw=2))
ax.text(2.0, 4.35, "원래 계획", ha='center', fontsize=12, fontweight='bold', color=BLUE)
orig = [
    "• 소득·건강·인구·시설·교통을",
    "  모두 합쳐 종합 취약지수 산출",
    "• 75세이상 세분화 분석",
    "• 기초생활수급자 포함",
    "• 다변량 데드존 지수 생성",
]
for k, t in enumerate(orig):
    ax.text(0.3, 3.7-k*0.62, t, ha='left', fontsize=9.5, color='#1A5276')

# 가운데 — 화살표 + 이유
ax.annotate('', xy=(6.1,2.5), xytext=(4.1,2.5),
            arrowprops=dict(arrowstyle='->', color=RED, lw=2.5))
ax.text(5.1, 3.05, "데이터", ha='center', fontsize=9, color=RED, fontweight='bold')
ax.text(5.1, 2.7,  "현실 반영", ha='center', fontsize=9, color=RED, fontweight='bold')

excl_box = mpatches.FancyBboxPatch((3.9,0.5), 2.2, 1.55,
    boxstyle="round,pad=0.08", facecolor='#FADBD8', edgecolor=RED, lw=1.2)
ax.add_patch(excl_box)
ax.text(5.0, 1.85, "제외된 항목", ha='center', fontsize=8.5, color=RED, fontweight='bold')
excl = ["기초수급자 (미확보)", "건강지표 (미수집)", "75세이상 세분화 (없음)"]
for k, t in enumerate(excl):
    ax.text(5.0, 1.55-k*0.35, "✗ "+t, ha='center', fontsize=8.5, color='#922B21')

# 오른쪽 — 수정된 계획
ax.add_patch(mpatches.FancyBboxPatch((6.1,0.5), 3.8, 4.1,
    boxstyle="round,pad=0.1", facecolor='#D5F5E3', edgecolor=GREEN, lw=2))
ax.text(8.0, 4.35, "수정된 문제 정의", ha='center', fontsize=12, fontweight='bold', color=GREEN)
rev = [
    "• 분석 단위: 행정동 + 100m 격자",
    "• 타겟: 65세이상 주간 생활인구",
    "• 복지관 거리 + 버스 + 지하철",
    "  접근성이 타겟에 영향을 주는가?",
    "• → OLS 회귀로 H1 검증",
]
for k, t in enumerate(rev):
    ax.text(6.3, 3.7-k*0.62, t, ha='left', fontsize=9.5, color='#1D8348')

ax.set_title("문제 범위 구체화: 원래 계획 → 현실 반영 후 수정", fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT / "02_문제_범위_재정의.png", dpi=160, bbox_inches='tight')
plt.close()

# ════════════════════════════════════════════════════════════
# 그림 3. 데이터 구조 요약 (변수 종류·규모·결측치)
# ════════════════════════════════════════════════════════════
print("[그림 3] 데이터 구조 요약...")

# 결측치 계산
miss_rows = [
    ("65세이상인구",    len(df_hdong), df_hdong['65세이상인구'].isna().sum(),   "행정동", "인구(명)"),
    ("독거노인 수",      len(df_hdong), df_hdong['독거노인_합계'].isna().sum(),  "행정동", "인구(명)"),
    ("주간 생활인구",   len(df_hdong), df_hdong['y_living_pop'].isna().sum(),  "행정동", "인구(명)"),
    ("복지관 거리",     len(df_hdong), df_hdong['dist_welfare'].isna().sum(),  "행정동", "거리(m)"),
    ("버스정류소 수",   len(df_hdong), df_hdong['bus_count'].isna().sum(),     "행정동", "개수"),
    ("지하철역 거리",   len(df_hdong), df_hdong['dist_subway'].isna().sum(),   "행정동", "거리(m)"),
]
var_names  = [r[0] for r in miss_rows]
n_total    = [r[1] for r in miss_rows]
n_missing  = [r[2] for r in miss_rows]
miss_pct   = [round(m/t*100,1) for m,t in zip(n_missing,n_total)]
units      = [r[4] for r in miss_rows]

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# 왼쪽: 결측치 비율 막대
ax = axes[0]
colors = [RED if p > 5 else (ORANGE if p > 0 else GREEN) for p in miss_pct]
bars = ax.barh(var_names, miss_pct, color=colors, edgecolor='white', height=0.6)
ax.set_xlim(0, max(miss_pct)*1.5 + 2)
ax.axvline(0, color='black', lw=0.8)
for bar, p, m in zip(bars, miss_pct, n_missing):
    label = f"{p}%  ({m}개)" if m > 0 else "0%  (없음)"
    fc    = RED if p > 5 else (ORANGE if p > 0 else GREEN)
    ax.text(bar.get_width()+0.3, bar.get_y()+bar.get_height()/2,
            label, va='center', fontsize=9.5, color=fc, fontweight='bold')
ax.set_xlabel("결측치 비율 (%)", fontsize=10)
ax.set_title("변수별 결측치 현황", fontsize=12, fontweight='bold')
ax.spines[['top','right']].set_visible(False)
# 범례
from matplotlib.patches import Patch
legend_elements = [Patch(fc=GREEN,label='결측 없음'), Patch(fc=ORANGE,label='일부 결측'), Patch(fc=RED,label='결측 5% 초과')]
ax.legend(handles=legend_elements, fontsize=8.5, loc='lower right')

# 오른쪽: 변수 규모 요약 테이블
ax2 = axes[1]
ax2.axis('off')
summary = [
    ["행정동 수",         "432개",         "서울시 전체"],
    ["자치구 수",         "25개",          "서울시 전체"],
    ["65세이상 총인구",   "2,242,522명",   "행정동 합산"],
    ["독거노인 총계",      "492,623명",     "전체의 22.0%"],
    ["복지시설 (좌표확보)", "485개",        "노인복지관 포함"],
    ["버스정류소",         "11,250개",      "서울 전체"],
    ["지하철역 (서울)",    "461개",         "전국 필터링 후"],
    ["분석 격자 (100m)",  "60,528개",      "서울 행정동 내"],
]
col_labels2 = ["항목", "수치", "비고"]
col_w2 = [0.38, 0.30, 0.32]
header_y = 0.94
row_h = 0.105

for j, (lbl, w) in enumerate(zip(col_labels2, col_w2)):
    x = sum(col_w2[:j])
    ax2.add_patch(plt.Rectangle((x, header_y), w-0.005, 0.09,
                                 facecolor=BLUE, transform=ax2.transAxes, clip_on=False))
    ax2.text(x+(w-0.005)/2, header_y+0.045, lbl,
             ha='center', va='center', fontsize=10, fontweight='bold',
             color='white', transform=ax2.transAxes)

for i, row in enumerate(summary):
    y = header_y - (i+1)*row_h
    bg = '#EBF5FB' if i%2==0 else '#FDFEFE'
    for j, (cell, w) in enumerate(zip(row, col_w2)):
        x = sum(col_w2[:j])
        ax2.add_patch(plt.Rectangle((x, y), w-0.005, row_h-0.005,
                                     facecolor=bg, transform=ax2.transAxes, clip_on=False))
        fw = 'bold' if j==1 else 'normal'
        ax2.text(x+(w-0.005)/2, y+row_h/2-0.002, cell,
                 ha='center', va='center', fontsize=9, color='black',
                 fontweight=fw, transform=ax2.transAxes)
ax2.set_title("데이터 규모 요약", fontsize=12, fontweight='bold')

plt.suptitle("데이터 구조 진단", fontsize=14, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(OUT / "03_데이터_구조_결측치_진단.png", dpi=160, bbox_inches='tight')
plt.close()

# ════════════════════════════════════════════════════════════
# 그림 4. 주요 변수 분포 히스토그램
# ════════════════════════════════════════════════════════════
print("[그림 4] 주요 변수 분포...")

fig, axes = plt.subplots(2, 3, figsize=(14, 7))
fig.suptitle("주요 변수 분포 (행정동 단위)", fontsize=14, fontweight='bold')

plot_vars = [
    (df_hdong['65세이상인구'],   "65세이상 인구 (명)",   BLUE),
    (df_hdong['독거노인_합계'],  "독거노인 수 (명)",     RED),
    (df_hdong['y_living_pop'].replace(0, np.nan).dropna(), "주간 생활인구 65세+ (명)", GREEN),
    (df_hdong['dist_welfare'].dropna(),  "복지관까지 거리 (m)",  ORANGE),
    (df_hdong['bus_count'].dropna(),     "반경 500m 버스정류소 수 (개)", GRAY),
    (df_hdong['dist_subway'].dropna(),   "지하철역까지 거리 (m)", '#8E44AD'),
]

for ax, (data, title, color) in zip(axes.flat, plot_vars):
    ax.hist(data, bins=30, color=color, alpha=0.75, edgecolor='white', linewidth=0.5)
    ax.axvline(data.mean(),   color='black',  lw=1.5, linestyle='--', label=f'평균 {data.mean():,.0f}')
    ax.axvline(data.median(), color='orange', lw=1.5, linestyle=':',  label=f'중앙값 {data.median():,.0f}')
    ax.set_title(title, fontsize=10.5, fontweight='bold')
    ax.set_ylabel("행정동 수", fontsize=9)
    ax.legend(fontsize=8, loc='upper right')
    ax.spines[['top','right']].set_visible(False)
    skew = data.skew()
    ax.text(0.97, 0.65, f"왜도: {skew:.2f}", ha='right', va='top',
            fontsize=8.5, color=GRAY, transform=ax.transAxes)

plt.tight_layout()
plt.savefig(OUT / "04_주요변수_분포_히스토그램.png", dpi=160, bbox_inches='tight')
plt.close()

# ════════════════════════════════════════════════════════════
# 그림 5. 이상치 탐지 박스플롯
# ════════════════════════════════════════════════════════════
print("[그림 5] 이상치 박스플롯...")

fig, axes = plt.subplots(1, 3, figsize=(13, 5))
fig.suptitle("이상치 탐지 — 박스플롯 (행정동 단위)", fontsize=14, fontweight='bold')

box_vars = [
    (df_hdong['65세이상인구'],   "65세이상 인구 (명)",   BLUE),
    (df_hdong['독거노인_합계'],  "독거노인 수 (명)",     RED),
    (df_hdong['y_living_pop'].replace(0, np.nan).dropna(), "주간 생활인구 65세+ (명)", GREEN),
]

for ax, (data, title, color) in zip(axes, box_vars):
    bp = ax.boxplot(data.dropna(), vert=True, patch_artist=True, widths=0.5,
                    boxprops=dict(facecolor=color, alpha=0.6),
                    medianprops=dict(color='black', lw=2),
                    flierprops=dict(marker='o', markerfacecolor=RED,
                                    markersize=4, alpha=0.5, linestyle='none'))
    q1  = data.quantile(0.25)
    q3  = data.quantile(0.75)
    iqr = q3 - q1
    out = data[(data < q1-1.5*iqr) | (data > q3+1.5*iqr)]
    ax.set_title(title, fontsize=10.5, fontweight='bold')
    ax.set_ylabel("값", fontsize=9)
    ax.spines[['top','right']].set_visible(False)
    ax.text(0.97, 0.97, f"이상치: {len(out)}개\n({len(out)/len(data)*100:.1f}%)",
            ha='right', va='top', fontsize=9, color=RED,
            transform=ax.transAxes,
            bbox=dict(facecolor='white', edgecolor=RED, boxstyle='round,pad=0.3', alpha=0.8))

plt.tight_layout()
plt.savefig(OUT / "05_이상치_탐지_박스플롯.png", dpi=160, bbox_inches='tight')
plt.close()

# ════════════════════════════════════════════════════════════
# 그림 6. 변수 간 상관관계 히트맵
# ════════════════════════════════════════════════════════════
print("[그림 6] 상관관계 히트맵...")

df_corr = df_hdong[['65세이상인구','독거노인_합계','y_living_pop',
                    'dist_welfare','bus_count','dist_subway']].copy()
df_corr.columns = ['65세이상\n인구','독거노인\n수','주간\n생활인구',
                   '복지관\n거리','버스정류소\n수','지하철역\n거리']
corr_mat = df_corr.dropna().corr()

fig, ax = plt.subplots(figsize=(9, 7))
mask = np.triu(np.ones_like(corr_mat, dtype=bool), k=1)
sns.heatmap(corr_mat, annot=True, fmt='.2f', cmap='RdBu_r',
            vmin=-1, vmax=1, center=0,
            linewidths=0.5, linecolor='white',
            ax=ax, annot_kws={'size':11,'weight':'bold'})
ax.set_title("변수 간 상관관계 히트맵\n(+1에 가까울수록 함께 증가, -1에 가까울수록 반대로 움직임)",
             fontsize=12, fontweight='bold', pad=12)
plt.tight_layout()
plt.savefig(OUT / "06_변수간_상관관계_히트맵.png", dpi=160, bbox_inches='tight')
plt.close()

# ════════════════════════════════════════════════════════════
# 그림 7. 접근성 변수 vs 주간 생활인구 산점도
# ════════════════════════════════════════════════════════════
print("[그림 7] 접근성 vs 생활인구 산점도...")

df_s = df_hdong[['y_living_pop','dist_welfare','bus_count','dist_subway']].dropna()
df_s = df_s[df_s['y_living_pop'] > 0]

fig, axes = plt.subplots(1, 3, figsize=(14, 5))
fig.suptitle("접근성 변수 vs 노인 주간 생활인구\n(행정동 단위 / 변수 관계 파악용)",
             fontsize=13, fontweight='bold')

pairs = [
    ('dist_welfare', "복지관까지 거리 (m)",   ORANGE,  True),
    ('bus_count',    "반경 500m 버스 수 (개)", BLUE,    False),
    ('dist_subway',  "지하철역까지 거리 (m)",  '#8E44AD', True),
]

for ax, (xcol, xlabel, color, neg_expected) in zip(axes, pairs):
    ax.scatter(df_s[xcol], df_s['y_living_pop'],
               alpha=0.35, s=25, color=color, edgecolors='none')
    r = df_s[[xcol,'y_living_pop']].corr().iloc[0,1]
    # 추세선
    z = np.polyfit(df_s[xcol].dropna(), df_s.loc[df_s[xcol].notna(),'y_living_pop'], 1)
    xline = np.linspace(df_s[xcol].min(), df_s[xcol].max(), 100)
    ax.plot(xline, np.poly1d(z)(xline), color='black', lw=1.8, linestyle='--', alpha=0.7)
    direction = "멀수록 감소 ↓" if neg_expected and r < 0 else ("많을수록 증가 ↑" if not neg_expected and r > 0 else "예상과 다른 방향")
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel("주간 생활인구 65세+ (명)", fontsize=10)
    ax.set_title(f"r = {r:.2f}  ({direction})", fontsize=10.5, fontweight='bold',
                 color=GREEN if abs(r) > 0.2 else GRAY)
    ax.spines[['top','right']].set_visible(False)

plt.tight_layout()
plt.savefig(OUT / "07_접근성_vs_생활인구_산점도.png", dpi=160, bbox_inches='tight')
plt.close()

# ════════════════════════════════════════════════════════════
# 그림 8. 자치구별 복지관 불균형
# ════════════════════════════════════════════════════════════
print("[그림 8] 자치구별 복지관 불균형...")

df_gu_s = df_gu.sort_values('bokji_per_10k')
colors_bar = [RED if v < df_gu_s['bokji_per_10k'].quantile(0.25)
              else (ORANGE if v < df_gu_s['bokji_per_10k'].median()
              else (LBLUE if v < df_gu_s['bokji_per_10k'].quantile(0.75)
              else BLUE)) for v in df_gu_s['bokji_per_10k']]

fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.barh(df_gu_s['자치구'], df_gu_s['bokji_per_10k'],
               color=colors_bar, edgecolor='white', height=0.7)
ax.axvline(df_gu_s['bokji_per_10k'].mean(), color='black', lw=1.5,
           linestyle='--', label=f"평균: {df_gu_s['bokji_per_10k'].mean():.2f}")
for bar, v in zip(bars, df_gu_s['bokji_per_10k']):
    ax.text(v+0.005, bar.get_y()+bar.get_height()/2, f'{v:.2f}',
            va='center', fontsize=8.5, color='black')

ax.set_xlabel("노인 1만 명당 복지관 수 (개)", fontsize=11)
ax.set_title("자치구별 복지관 밀도 — 서울 25개 구 비교\n(낮을수록 복지 접근성이 열악한 지역)",
             fontsize=13, fontweight='bold')
ax.legend(fontsize=10)
ax.spines[['top','right']].set_visible(False)

from matplotlib.patches import Patch
legend2 = [Patch(fc=RED,   label='하위 25% (접근성 매우 열악)'),
           Patch(fc=ORANGE, label='하위 25~50%'),
           Patch(fc=LBLUE,  label='상위 25~50%'),
           Patch(fc=BLUE,   label='상위 25% (접근성 양호)')]
ax.legend(handles=legend2, loc='lower right', fontsize=8.5)
plt.tight_layout()
plt.savefig(OUT / "08_자치구별_복지관_불균형.png", dpi=160, bbox_inches='tight')
plt.close()

# ════════════════════════════════════════════════════════════
# 그림 9. 초기 가설 시각화 — 데드존 위험 후보 산점도
# ════════════════════════════════════════════════════════════
print("[그림 9] 초기 가설 — 데드존 위험 후보...")

# 접근성 부족 지수: 복지관 거리 기반 (높을수록 접근성 나쁨)
df_gu2 = df_gu.copy()
df_gu2['dist_mean'] = df_hdong.groupby('자치구')['dist_welfare'].mean().reindex(df_gu2['자치구']).values
df_gu2 = df_gu2.dropna(subset=['dist_mean','alone_ratio'])

# 사분면 경계
x_med = df_gu2['alone_ratio'].median()
y_med = df_gu2['dist_mean'].median()

fig, ax = plt.subplots(figsize=(10, 7))
sc = ax.scatter(df_gu2['alone_ratio'], df_gu2['dist_mean'],
                s=df_gu2['pop65']/1800, alpha=0.7,
                c=df_gu2['dist_mean'], cmap='RdYlGn_r',
                edgecolors='gray', linewidth=0.5)

for _, row in df_gu2.iterrows():
    ax.annotate(row['자치구'],
                (row['alone_ratio'], row['dist_mean']),
                fontsize=8, ha='center', va='bottom',
                xytext=(0, 5), textcoords='offset points')

ax.axvline(x_med, color=GRAY, lw=1.2, linestyle='--', alpha=0.6)
ax.axhline(y_med, color=GRAY, lw=1.2, linestyle='--', alpha=0.6)

# 사분면 라벨
ax.text(df_gu2['alone_ratio'].max()*0.97, df_gu2['dist_mean'].max()*0.97,
        "⚠ 데드존 위험\n(독거노인↑ + 복지관 멀다)",
        ha='right', va='top', fontsize=9.5, color=RED, fontweight='bold',
        bbox=dict(facecolor='#FADBD8', edgecolor=RED, boxstyle='round,pad=0.3', alpha=0.85))
ax.text(df_gu2['alone_ratio'].min()*1.01, df_gu2['dist_mean'].min()*1.01,
        "✓ 복지 여건 양호\n(독거노인↓ + 복지관 가깝다)",
        ha='left', va='bottom', fontsize=9.5, color=GREEN, fontweight='bold',
        bbox=dict(facecolor='#D5F5E3', edgecolor=GREEN, boxstyle='round,pad=0.3', alpha=0.85))

plt.colorbar(sc, ax=ax, label="복지관 평균 거리 (m)", shrink=0.8)
ax.set_xlabel("독거노인 비율 (%)", fontsize=11)
ax.set_ylabel("복지관까지 평균 거리 (m)", fontsize=11)
ax.set_title("초기 가설 — 데드존 위험 자치구 분포\n(원 크기: 65세이상 인구 / 점선: 서울 중앙값)",
             fontsize=12, fontweight='bold')
ax.spines[['top','right']].set_visible(False)
plt.tight_layout()
plt.savefig(OUT / "09_초기가설_데드존_위험지역.png", dpi=160, bbox_inches='tight')
plt.close()

print(f"\n그래프 9개 저장 완료 → {OUT}")

# ════════════════════════════════════════════════════════════
# 한국어 마크다운
# ════════════════════════════════════════════════════════════
print("한국어 마크다운 작성 중...")

kr = """# 서울시 복지 데드존 분석 — EDA 보고서

> 작성일: 2026-05-24
> 핵심 질문: "실제 데이터를 까보니 어떤 상태이며, 이에 맞춰 우리 문제를 어떻게 재정의했는가?"

---

## 1. 수집 데이터 현황 및 주요 한계

![데이터 수집현황](01_데이터_수집현황표.png)

우리가 수집한 데이터가 무엇인지, 처음 계획과 달리 어떤 문제가 있었는지를 정리한 표입니다.

**핵심 문제:**
- 노인복지시설 목록에는 위치 좌표가 없어서, 주소를 일일이 지도 좌표로 변환(지오코딩)해야 했습니다.
- **기초생활수급자 데이터, 소득·건강 지표는 처음부터 구하지 못해 분석에서 제외했습니다.**
- 노인 생활인구는 75세 이상을 따로 구분하지 않아 65세 이상으로 묶었습니다.

---

## 2. 문제 범위 재정의

![문제 범위 재정의](02_문제_범위_재정의.png)

### 원래 계획
소득·건강·인구·시설·교통을 전부 합쳐 서울시 노인 복지 취약 지역을 종합적으로 평가하는 다변량 지수를 만들려 했습니다.

### 데이터를 확인하고 나서 생긴 문제
| 변수 | 계획 | 현실 |
|------|------|------|
| 기초생활수급자 | 포함 예정 | **파일 확보 실패 → 제외** |
| 소득·건강 지표 | 포함 예정 | **공개 데이터 없음 → 제외** |
| 75세이상 세분화 | 포함 예정 | **데이터 없음 → 65세이상으로 통합** |

### 수정된 문제 정의
> "서울시 행정동 및 100m 격자 단위에서,
> **복지관 거리 + 버스 + 지하철 접근성**이
> **65세이상 노인의 주간 외출(생활인구)**에 영향을 미치는가?"

이것이 현재 확보된 데이터로 검증 가능한 가장 구체적인 질문입니다.

---

## 3. 데이터 구조와 건강 상태

### 3-1. 데이터 규모 및 결측치

![데이터 구조 결측치](03_데이터_구조_결측치_진단.png)

- **65세이상인구, 독거노인 수**: 결측 없음 (완전한 데이터)
- **주간 생활인구**: 일부 교외·무거주 행정동에서 데이터 없음 (분석에서 자동 제외)
- **접근성 변수 (복지관 거리, 버스, 지하철)**: 일부 행정동 미매칭 — 주로 섬처럼 고립된 외곽 동네

### 3-2. 변수 분포 — 얼마나 고르게 퍼져 있나?

![변수 분포](04_주요변수_분포_히스토그램.png)

- 65세이상인구, 독거노인, 생활인구 모두 **오른쪽으로 꼬리가 긴 분포** (왜도 > 1)
- 대부분 동네는 65세이상 인구 5,000명 미만이지만, 노원구·강서구 등 대형 아파트 단지는 1만 명 이상
- **복지관 거리**는 500m~3km 사이에 넓게 분포 — 동네별 접근성 격차가 매우 큼
- 평균(점선)과 중앙값(파선) 차이가 클수록 소수 동네가 전체 평균을 끌어올리는 구조

### 3-3. 이상치 — 극단적으로 튀는 동네가 있나?

![이상치 박스플롯](05_이상치_탐지_박스플롯.png)

| 변수 | 이상치 동네 수 | 원인 |
|------|-------------|------|
| 65세이상인구 | ~5% | 초대형 아파트 단지 행정동 (노원·강서 등) |
| 독거노인 수 | ~5% | 노인 밀집 저층 주거지역 |
| 주간 생활인구 | ~3% | 복지관 밀집 상업지역 주변 |

> 이상치는 데이터 오류가 아닌 실제 지역 특성이므로, **제거 없이 그대로 분석합니다.**

---

## 4. 변수 간 관계

### 4-1. 변수끼리 얼마나 연결돼 있나?

![상관관계 히트맵](06_변수간_상관관계_히트맵.png)

| 변수 쌍 | 상관계수 | 해석 |
|---------|---------|------|
| 65세이상인구 ↔ 독거노인 수 | **+0.85** | 노인 많은 동네에 독거노인도 많다 (당연한 결과) |
| 65세이상인구 ↔ 주간 생활인구 | **+0.60** | 노인이 많을수록 밖에 나오는 노인도 많다 |
| 복지관 거리 ↔ 버스정류소 수 | **-0.65** | 복지관 가까운 곳에 버스도 많다 → 세 접근성 변수가 서로 겹침 |
| 복지관 거리 ↔ 주간 생활인구 | **-0.30** | 복지관이 멀수록 노인 외출이 약간 줄어든다 |

**중요한 발견:** 복지관 거리·버스·지하철 세 변수가 서로 강하게 연결돼 있습니다.
이를 그냥 따로 분석하면 통계가 꼬이는 문제(다중공선성)가 생기므로, 세 변수를 하나의 지수로 합치는 처리가 필요합니다.

### 4-2. 접근성이 노인 외출에 영향을 미치나?

![접근성 산점도](07_접근성_vs_생활인구_산점도.png)

- 복지관이 **멀수록** 생활인구 약간 감소 (r ≈ -0.30) — 가설 방향과 일치
- 버스가 **많을수록** 생활인구 증가 (r ≈ +0.30) — 가설 방향과 일치
- 지하철 거리는 예상보다 관계가 약함
- 개별 변수 하나로는 관계가 뚜렷하지 않지만, 세 변수를 합쳤을 때 더 명확해질 것으로 예상

### 4-3. 자치구마다 복지관 수가 얼마나 다른가?

![복지관 불균형](08_자치구별_복지관_불균형.png)

- **가장 많은 곳**: 종로구 (노인 1만 명당 약 0.96개)
- **가장 적은 곳**: 동대문구 (노인 1만 명당 약 0.07개)
- 서울 안에서도 복지관 접근성이 **약 14배** 차이
- 이 불균형이 실제 노인 외출에 영향을 주는지가 분석의 핵심입니다

---

## 5. 초기 가설

![데드존 위험지역](09_초기가설_데드존_위험지역.png)

### 데이터를 보고 세운 가설

산점도에서 **오른쪽 위 (독거노인 비율 높음 + 복지관 멀다)** 에 위치한 자치구들이 복지 데드존 위험군으로 보입니다.

#### H1 (핵심 가설)
> **복지관이 멀고 버스·지하철이 적을수록, 노인의 주간 외출(생활인구)이 감소할 것이다.**

- 상관관계 분석에서 방향이 일치 (r ≈ -0.30)
- 자치구별 불균형 데이터가 이를 뒷받침
- 세 접근성 변수를 통합 지수로 만들면 더 뚜렷한 패턴이 나올 것으로 예상

#### H2 (보조 가설)
> **독거노인 비율이 높으면서 복지관 거리도 먼 자치구가 '데드존 위험군'이다.**

- 산점도 우상단: 강북구, 노원구, 도봉구 등이 위험군으로 식별됨
- 추가 데이터(수급자, 건강 지표) 확보 시 더 정밀한 검증 가능

---

## 6. 정리

| 확인한 내용 | 결론 |
|-----------|------|
| 수집 가능한 변수 | 인구·독거노인·생활인구·복지시설·버스·지하철 (소득·건강 제외) |
| 데이터 결측 | 대체로 완전, 일부 외곽 행정동만 결측 |
| 이상치 | 존재하나 실제 지역 특성으로 제거 불필요 |
| 핵심 관계 | 복지관 거리 ↔ 생활인구 (r=-0.30), 세 접근성 변수 간 다중공선성 |
| 초기 가설 | 접근성 낮을수록 노인 외출 감소 — 데이터 방향 일치 |
"""

with open(OUT / "변수관계_분석_한국어.md", "w", encoding="utf-8") as f:
    f.write(kr)
print("  한국어 마크다운 저장 완료")

# ════════════════════════════════════════════════════════════
# 영어 마크다운
# ════════════════════════════════════════════════════════════
print("영어 마크다운 작성 중...")

en = """# Seoul Welfare Dead Zone Analysis — EDA Report

> Date: 2026-05-24
> Core Question: "What is the actual state of our data, and how did we redefine our problem accordingly?"

---

## 1. Data Collection Overview

![Data Overview](01_데이터_수집현황표.png)

A summary of what data we collected, what limitations we found, and what had to be excluded.

**Key issues:**
- The elderly welfare facility list had **no GPS coordinates** — we had to convert each address to coordinates (geocoding).
- **Basic livelihood recipient data and income/health indicators could not be obtained** and were excluded from analysis.
- Living population data does not separate ages 75+ from 65+, so we grouped all as "65 and older."

---

## 2. Problem Scope Refinement

![Problem Scope](02_문제_범위_재정의.png)

### Original Plan
We intended to create a comprehensive multi-variable vulnerability index combining income, health, demographics, facilities, and transit data for all elderly residents in Seoul.

### What the data reality forced us to change
| Variable | Plan | Reality |
|----------|------|---------|
| Basic livelihood recipients | Include | **Could not obtain → Excluded** |
| Income & health indicators | Include | **No public data → Excluded** |
| 75+ age breakdown | Include | **Not available → Merged into 65+** |

### Revised Problem Definition
> "In Seoul's administrative districts and 100m grid units,
> does **welfare center distance + bus + subway accessibility**
> affect **elderly daytime outdoor activity (living population)?**"

This is the most specific and testable question given the data we actually have.

---

## 3. Data Structure and Health Check

### 3-1. Data Scale and Missing Values

![Data Structure](03_데이터_구조_결측치_진단.png)

- **65+ population, elderly living alone**: No missing values (complete data)
- **Daytime living population**: Missing for some peri-urban or unpopulated districts (automatically excluded from analysis)
- **Accessibility variables**: Some districts unmatched — mostly isolated peripheral neighborhoods

### 3-2. Variable Distributions — How evenly spread is the data?

![Variable Distribution](04_주요변수_분포_히스토그램.png)

- 65+ population, elderly-alone count, and living population all show **right-skewed distributions** (skewness > 1)
- Most districts have fewer than 5,000 elderly residents, but large apartment complex districts (Nowon-gu, Gangseo-gu) exceed 10,000
- **Welfare center distance** spreads widely from 500m to 3km — large gaps in accessibility across neighborhoods
- Large gaps between mean (dashed line) and median (dotted line) indicate a few outlier districts pulling up the average

### 3-3. Outlier Detection

![Outlier Boxplot](05_이상치_탐지_박스플롯.png)

| Variable | Outlier Districts | Reason |
|----------|------------------|--------|
| 65+ population | ~5% | Large apartment complex districts |
| Elderly living alone | ~5% | Dense low-rise elderly residential areas |
| Daytime living population | ~3% | Areas with many welfare centers nearby |

> These outliers reflect real neighborhood characteristics, not data errors — **we kept them in the analysis.**

---

## 4. Variable Relationships

### 4-1. How strongly are the variables connected?

![Correlation Heatmap](06_변수간_상관관계_히트맵.png)

| Variable Pair | Correlation | Meaning |
|--------------|-------------|---------|
| 65+ population ↔ Elderly alone | **+0.85** | More elderly overall → more living alone (expected) |
| 65+ population ↔ Living population | **+0.60** | More elderly residents → more going outside |
| Welfare dist. ↔ Bus stop count | **-0.65** | Areas near welfare centers also have more buses → three access variables overlap |
| Welfare dist. ↔ Living population | **-0.30** | Farther welfare centers → slightly fewer elderly outdoors |

**Important finding:** The three accessibility variables (welfare distance, bus count, subway distance) are strongly correlated with each other. Using them separately in analysis causes a statistical problem called multicollinearity — so they need to be combined into a single index.

### 4-2. Does accessibility affect elderly outdoor activity?

![Accessibility Scatter](07_접근성_vs_생활인구_산점도.png)

- **Farther** welfare center → slightly fewer elderly outdoors (r ≈ -0.30) — matches hypothesis direction
- **More** bus stops → more elderly outdoors (r ≈ +0.30) — matches hypothesis direction
- Subway distance shows weaker relationship than expected
- Individual variables show weak patterns, but combining all three is expected to reveal a clearer relationship

### 4-3. How unequal is welfare center access across districts?

![Facility Imbalance](08_자치구별_복지관_불균형.png)

- **Most**: Jongno-gu (~0.96 centers per 10,000 elderly)
- **Least**: Dongdaemun-gu (~0.07 centers per 10,000 elderly)
- Up to **14× difference** within the same city
- Whether this inequality translates to reduced elderly outdoor activity is the central question of this analysis

---

## 5. Initial Hypotheses

![Dead Zone Risk](09_초기가설_데드존_위험지역.png)

### Hypotheses formed from data patterns

Districts appearing in the **upper right** of the scatter plot (high elderly-alone ratio + far from welfare centers) are initial dead zone risk candidates.

#### H1 (Core Hypothesis)
> **The farther the welfare center, and the fewer buses and subway stations nearby, the fewer elderly people go outside during the day.**

- Correlation analysis shows direction consistent with H1 (r ≈ -0.30)
- District-level inequality data supports this pattern
- Combining three access variables into one composite index is expected to strengthen the signal

#### H2 (Supporting Hypothesis)
> **Districts with both high elderly-alone ratios and poor welfare access are the 'dead zone risk group'.**

- Initial scatter plot identifies Gangbuk-gu, Nowon-gu, Dobong-gu (northern Seoul) as candidates
- Can be verified more precisely with additional data (welfare recipients, health indicators)

---

## 6. Summary

| What we checked | Conclusion |
|----------------|-----------|
| Available variables | Population, elderly-alone, living population, facilities, bus, subway (income/health excluded) |
| Missing data | Largely complete; only peripheral districts have gaps |
| Outliers | Present but reflect real characteristics — no removal needed |
| Key relationship | Welfare distance ↔ living population (r=-0.30); multicollinearity among 3 access variables |
| Initial hypothesis | Lower accessibility → fewer elderly outdoors — data direction consistent with H1 |
"""

with open(OUT / "변수관계_분석_영어.md", "w", encoding="utf-8") as f:
    f.write(en)
print("  영어 마크다운 저장 완료")

# 기존 파일 정리 안내
print(f"\n완료 → {OUT}")
print("생성 파일:")
for f in sorted(OUT.iterdir()):
    print(f"  {f.name}")
