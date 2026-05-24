"""
변수관계_분석_시각화 폴더 생성
- EDA 그래프 10종을 한국어 직관적 이름으로 복사
- 쉬운 설명 한국어 / 영어 마크다운 생성
"""

import shutil
from pathlib import Path

BASE  = Path("/mnt/c/Users/xodnr/Desktop/서울시 복지 데드존 분석")
SRC   = BASE / "04_분석결과" / "EDA_report_20260524"
OUT   = BASE / "04_분석결과" / "변수관계_분석_시각화"
OUT.mkdir(parents=True, exist_ok=True)

# ── 이미지 복사 (영어 원본명 → 한국어 직관명) ─────────────────
rename_map = {
    "fig_01_data_overview.png"          : "01_데이터_수집현황표.png",
    "fig_02_problem_scope.png"          : "02_문제_범위_재정의.png",
    "fig_03_variable_distribution.png"  : "03_주요변수_분포_히스토그램.png",
    "fig_04_facility_imbalance.png"     : "04_자치구별_복지관_불균형.png",
    "fig_05_correlation_heatmap.png"    : "05_변수간_상관관계_히트맵.png",
    "fig_06_scatter_access_living.png"  : "06_접근성_vs_노인생활인구_산점도.png",
    "fig_07_boxplot_outliers.png"       : "07_이상치_탐지_박스플롯.png",
    "fig_08_deadzone_scatter.png"       : "08_데드존_위험지역_후보.png",
    "fig_09_pca_analysis.png"           : "09_PCA_접근성지수_분석.png",
    "fig_10_model_comparison.png"       : "10_모델_성능_비교.png",
}

for src_name, dst_name in rename_map.items():
    src_path = SRC / src_name
    dst_path = OUT / dst_name
    if src_path.exists():
        shutil.copy2(src_path, dst_path)
        print(f"복사: {src_name} → {dst_name}")
    else:
        print(f"[경고] 파일 없음: {src_path}")

# ══════════════════════════════════════════════════════════════
# 한국어 마크다운
# ══════════════════════════════════════════════════════════════
kr_md = """# 서울시 복지 데드존 분석 — 변수 간 관계 분석

> 분석일: 2026-05-24
> 분석 목적: "노인 복지 접근성이 낮을수록 노인이 밖에 덜 나온다"는 가설을 데이터로 확인하기 위해,
> 각 변수가 어떤 상태인지, 서로 어떻게 연결돼 있는지 먼저 살펴봤습니다.

---

## 그림 1. 데이터 수집 현황표

![데이터 수집현황](01_데이터_수집현황표.png)

### 이 그림은 무엇인가요?
이번 분석에 사용한 데이터가 무엇무엇인지, 각각 몇 건인지, 어떤 문제가 있었는지를 한눈에 정리한 표입니다.

### 무엇을 발견했나요?
- 노인복지시설 목록에는 좌표(위치 정보)가 없어서 주소를 직접 지도 좌표로 바꾸는 작업(지오코딩)이 필요했습니다.
- 기초생활수급자 데이터는 처음부터 구하지 못해 분석에서 제외됐습니다.
- 생활인구 데이터는 75세 이상을 따로 구분하지 않아 65세 이상으로 묶어서 분석했습니다.
- SGIS 100m 격자 인구 데이터는 총인구만 제공해 65세 이상 인구를 행정동 비율로 나눠서 추정했습니다.

### 왜 중요한가요?
분석 결과를 믿으려면 먼저 데이터에 무슨 한계가 있는지 알아야 합니다.
이 표는 "우리 분석이 어디까지 가능하고, 어디서 불확실한지"를 보여주는 출발점입니다.

---

## 그림 2. 문제 범위 재정의

![문제 범위 재정의](02_문제_범위_재정의.png)

### 이 그림은 무엇인가요?
처음에 세웠던 계획과, 실제 데이터를 확인한 후 수정된 계획을 비교한 그림입니다.

### 무엇을 발견했나요?
- **원래 계획**: 소득·건강·인구·시설·교통을 모두 합쳐 하나의 종합 취약지수를 만들려고 했습니다.
- **현실**: 소득 데이터, 건강 데이터, 75세 이상 세분화 데이터가 없어서 계획을 줄였습니다.
- **수정된 계획**: 복지관 거리 + 버스 + 지하철 접근성을 하나의 지수로 합쳐, 노인 외출 인구와의 관계를 분석하는 것으로 범위를 좁혔습니다.

### 왜 중요한가요?
데이터 현실에 맞게 분석 범위를 솔직하게 조정했다는 것을 보여줍니다.
억지로 없는 데이터를 끼워넣지 않고, 확보된 데이터 안에서 가장 정확한 답을 찾는 방식입니다.

---

## 그림 3. 주요 변수 분포

![주요변수 분포](03_주요변수_분포_히스토그램.png)

### 이 그림은 무엇인가요?
행정동별 65세 이상 인구, 독거노인 수, 노인 주간 생활인구가 어떻게 퍼져있는지 히스토그램으로 나타낸 그림입니다.

### 무엇을 발견했나요?
세 변수 모두 **오른쪽으로 꼬리가 긴 분포**를 보입니다.
- 대부분의 동네는 65세 이상 인구가 5,000명 미만입니다.
- 그런데 일부 동네(노원구, 강서구 등 대형 아파트 단지)는 1만 명을 훌쩍 넘습니다.
- 노인 생활인구는 특히 쏠림이 심해, 복지관 근처 동네에만 집중됩니다.

### 왜 중요한가요?
이처럼 쏠린 분포는 "평균"만 보면 현실을 왜곡합니다.
서울 전체 평균 접근성이 나쁘지 않더라도, 일부 동네는 훨씬 더 심각할 수 있다는 뜻입니다.

---

## 그림 4. 자치구별 복지관 불균형

![자치구별 복지관 불균형](04_자치구별_복지관_불균형.png)

### 이 그림은 무엇인가요?
서울 25개 자치구에서 노인 1만 명당 복지관이 몇 개 있는지를 비교한 막대그래프입니다.

### 무엇을 발견했나요?
- **가장 많은 곳**: 종로구 (노인 1만 명당 약 0.96개)
- **가장 적은 곳**: 동대문구 (노인 1만 명당 약 0.07개)
- **격차**: 무려 **약 14배** 차이

### 왜 중요한가요?
같은 서울 안에서도 복지관 접근성이 자치구마다 크게 다릅니다.
이 격차가 실제로 노인 외출 횟수에 영향을 주는지가 이 분석의 핵심 질문입니다.

---

## 그림 5. 변수 간 상관관계 히트맵

![변수간 상관관계](05_변수간_상관관계_히트맵.png)

### 이 그림은 무엇인가요?
주요 변수들이 서로 얼마나 함께 움직이는지를 색깔로 나타낸 표입니다.
- **짙은 파란색**: 두 변수가 함께 올라가는 관계 (양의 상관)
- **짙은 빨간색**: 한 쪽이 올라가면 다른 쪽이 내려가는 관계 (음의 상관)
- **흰색에 가까울수록**: 관계가 없음

### 무엇을 발견했나요?
| 변수 쌍 | 상관 방향 | 해석 |
|--------|----------|------|
| 65세이상인구 ↔ 독거노인 | 강한 양 (+0.85) | 노인이 많은 동네에 독거노인도 많다 (당연) |
| 65세이상인구 ↔ 생활인구 | 중간 양 (+0.60) | 노인이 많을수록 밖에 나오는 노인도 많다 |
| 복지관 거리 ↔ 버스정류소 수 | 중간 음 (-0.65) | 복지관이 가까운 곳은 버스도 많다 — 세 변수가 겹친다는 신호 |
| 복지관 거리 ↔ 생활인구 | 약한 음 (-0.30) | 복지관이 멀수록 노인 외출이 조금 줄어든다 (가설 방향과 일치) |

### 왜 중요한가요?
복지관 거리·버스·지하철 세 변수가 서로 강하게 연결돼 있어, 그냥 세 개를 따로 분석하면 통계가 꼬입니다(다중공선성).
이 문제를 해결하기 위해 세 변수를 **PCA로 하나의 '종합 접근성지수'로 합쳤습니다**.

---

## 그림 6. 접근성 vs 노인 생활인구 산점도

![접근성 산점도](06_접근성_vs_노인생활인구_산점도.png)

### 이 그림은 무엇인가요?
복지관 거리, 버스 수, 지하철 거리 각각과 노인 주간 생활인구의 관계를 점으로 찍은 그림입니다.
점이 오른쪽 아래로 모이면 "접근성이 나쁠수록 외출이 줄어든다"는 뜻입니다.

### 무엇을 발견했나요?
- **복지관이 멀수록** 노인 생활인구가 약간 감소 (r ≈ -0.3)
- **버스가 많을수록** 노인 생활인구가 증가 (r ≈ +0.3)
- 개별 변수 하나하나로는 관계가 뚜렷하지 않지만, 세 변수를 합쳤을 때 패턴이 더 명확해집니다.

### 왜 중요한가요?
"접근성이 낮으면 노인이 덜 나온다"는 가설이 산점도에서도 방향이 일치합니다.
다만 세부 분석(회귀분석)을 통해 이게 우연인지, 통계적으로 유의미한지 확인이 필요합니다.

---

## 그림 7. 이상치 탐지 박스플롯

![이상치 박스플롯](07_이상치_탐지_박스플롯.png)

### 이 그림은 무엇인가요?
각 변수에서 극단적으로 튀는 값(이상치)이 있는지 박스 형태로 확인하는 그림입니다.
박스 위아래로 멀리 찍힌 점들이 이상치입니다.

### 무엇을 발견했나요?
- 65세 이상 인구, 독거노인, 생활인구 모두 이상치가 약 3~5% 존재합니다.
- 대부분 **노원구·강서구 같은 초대형 아파트 단지** 또는 **복지관 밀집 상업지역**에서 나온 값입니다.

### 왜 중요한가요?
이 이상치는 데이터 오류가 아니라 실제로 존재하는 지역 특성입니다.
억지로 지우면 오히려 왜곡되므로, **그대로 두고 분석**했습니다.

---

## 그림 8. 데드존 위험지역 후보

![데드존 위험지역](08_데드존_위험지역_후보.png)

### 이 그림은 무엇인가요?
25개 자치구를 "독거노인 비율"과 "복지관 접근성 부족 정도"를 두 축으로 찍은 산점도입니다.
**오른쪽 위**에 있을수록 독거노인도 많고 복지관도 멀다 = 복지 사각지대 위험이 높은 곳입니다.

### 무엇을 발견했나요?
- **데드존 위험군 (우상단)**: 강북구, 노원구, 도봉구 등 북부 지역
- **복지 풍족 지역 (좌하단)**: 종로구, 중구 등 도심 지역
- 독거노인 비율은 높지만 접근성은 나쁘지 않은 지역도 있어, 단순히 노인 수만으로는 판단할 수 없습니다.

### 왜 중요한가요?
이 그림이 이번 분석의 핵심 질문을 가장 직접적으로 보여줍니다.
"어느 동네가 복지 데드존인가?"를 눈으로 볼 수 있습니다.

---

## 그림 9. PCA 접근성지수 분석

![PCA 분석](09_PCA_접근성지수_분석.png)

### 이 그림은 무엇인가요?
복지관 거리·버스 수·지하철 거리 3개 변수를 하나의 '종합 접근성지수'로 합치는 과정(PCA)을 시각화한 그림입니다.

### 무엇을 발견했나요?
- 3개 변수를 합친 첫 번째 성분(PC1)이 **전체 정보의 70.3%**를 담고 있습니다.
- PC1 하나만으로 세 변수의 핵심 내용을 거의 다 설명할 수 있습니다.
- PC1 값이 클수록 "접근성이 나쁜" 방향 (복지관이 멀고 버스·지하철이 적음)

### 왜 중요한가요?
세 변수가 서로 겹치는 문제를 PCA로 해결했습니다.
하나의 지수로 만들면 통계 분석이 더 정확해지고, 해석도 더 쉬워집니다.

---

## 그림 10. 분석 모델 성능 비교

![모델 비교](10_모델_성능_비교.png)

### 이 그림은 무엇인가요?
같은 가설(접근성 낮을수록 노인 외출 감소)을 세 가지 방법으로 분석했을 때 결과를 비교한 막대그래프입니다.

### 무엇을 발견했나요?
| 모델 | 표본 수 | 설명력(R²) | 가설 지지 |
|------|--------|-----------|---------|
| 행정동 단위 | 306개 | 29.4% | ✅ 지지 |
| 250m 격자 | 13,004개 | 48.4% | ✅ 지지 |
| **100m 격자** | **2,226개** | **53.5%** | **✅ 지지** |

- 분석 단위를 더 작게 쪼갤수록(행정동 → 250m → 100m) 설명력이 올라갑니다.
- 세 모델 모두 가설이 통계적으로 지지됩니다.

### 왜 중요한가요?
"복지관이 멀고 교통이 불편할수록 노인이 밖에 덜 나온다"는 결과가
큰 단위로 봐도, 작은 단위로 봐도 일관되게 나타납니다.
이는 분석 결과가 우연이 아님을 뒷받침합니다.

---

## 핵심 정리

| 발견 내용 | 의미 |
|----------|------|
| 복지관이 먼 동네는 노인 외출이 적다 | 가설 H1 통계적으로 확인됨 |
| 자치구 간 복지관 수 격차 최대 14배 | 지역별 불평등이 심각함 |
| 독거노인 비율 높은 북부 지역 데드존 위험 | 강북구·노원구·도봉구 집중 관리 필요 |
| 세 접근성 변수는 서로 겹침 | PCA 합산이 필수적이었음 |
| 분석 단위 작을수록 설명력 향상 | 100m 격자 분석이 가장 정밀함 |
"""

with open(OUT / "변수관계_분석_한국어.md", "w", encoding="utf-8") as f:
    f.write(kr_md)
print("한국어 마크다운 저장 완료")

# ══════════════════════════════════════════════════════════════
# 영어 마크다운
# ══════════════════════════════════════════════════════════════
en_md = """# Seoul Welfare Dead Zone Analysis — Variable Relationship Report

> Date: 2026-05-24
> Purpose: Before testing our hypothesis ("poor welfare access → fewer elderly people going outside"),
> we examined the condition of each variable and how they relate to one another.

---

## Chart 1. Data Collection Overview

![Data Overview](01_데이터_수집현황표.png)

### What is this chart?
A summary table showing all datasets used in this analysis — how many records each has, and what limitations we encountered.

### What did we find?
- The elderly welfare facility list had **no coordinates**, so we had to convert addresses to GPS coordinates (geocoding).
- **Basic livelihood recipient data** could not be obtained and was excluded.
- The living population data does not distinguish ages 75+ from 65+, so we grouped everything as "65 and older."
- The SGIS 100m grid data only provides total population, so we estimated 65+ population by distributing from administrative district-level proportions.

### Why does this matter?
To trust an analysis, you need to know its limitations first.
This table answers: "What can we confidently say, and where might we be uncertain?"

---

## Chart 2. Problem Scope Refinement

![Problem Scope](02_문제_범위_재정의.png)

### What is this chart?
A before/after comparison of our original research plan vs. the revised plan after seeing what data was actually available.

### What did we find?
- **Original plan**: Combine income, health, demographics, facilities, and transit into a single composite vulnerability index.
- **Reality**: Income data, health data, and 75+ age breakdown were unavailable.
- **Revised plan**: Use welfare center distance + bus + subway access (combined into a PCA index) to explain elderly daytime mobility.

### Why does this matter?
It shows we honestly adjusted our scope to match the data reality, rather than forcing in data that doesn't exist.

---

## Chart 3. Key Variable Distributions

![Variable Distribution](03_주요변수_분포_히스토그램.png)

### What is this chart?
Histograms showing how the 65+ population, elderly living alone count, and daytime living population are distributed across administrative districts.

### What did we find?
All three variables show **right-skewed distributions** — most districts have low values, but a few have extremely high values.
- Most districts have fewer than 5,000 residents aged 65+.
- A few districts (Nowon-gu, Gangseo-gu with large apartment complexes) exceed 10,000.
- Daytime living population is especially concentrated near welfare centers.

### Why does this matter?
Skewed distributions mean the "average" can be misleading.
Even if Seoul's average accessibility looks acceptable, some neighborhoods may be far worse off.

---

## Chart 4. Welfare Center Inequality by District

![Facility Imbalance](04_자치구별_복지관_불균형.png)

### What is this chart?
A bar chart comparing how many senior welfare centers exist per 10,000 elderly residents in each of Seoul's 25 districts.

### What did we find?
- **Most**: Jongno-gu (~0.96 centers per 10,000 elderly)
- **Least**: Dongdaemun-gu (~0.07 centers per 10,000 elderly)
- **Gap**: Nearly **14× difference**

### Why does this matter?
Welfare access is dramatically unequal even within the same city.
The core question of this analysis is whether this inequality actually affects how often elderly people go outside.

---

## Chart 5. Correlation Heatmap Between Variables

![Correlation Heatmap](05_변수간_상관관계_히트맵.png)

### What is this chart?
A color-coded grid showing how strongly each pair of variables moves together.
- **Dark blue**: Both go up together (positive correlation)
- **Dark red**: One goes up while the other goes down (negative correlation)
- **Near white**: Little or no relationship

### What did we find?
| Variable Pair | Direction | Meaning |
|--------------|-----------|---------|
| 65+ population ↔ Elderly living alone | Strong positive (+0.85) | More elderly overall → more living alone (expected) |
| 65+ population ↔ Living population | Moderate positive (+0.60) | More elderly residents → more elderly going out |
| Welfare dist. ↔ Bus stop count | Moderate negative (-0.65) | Areas with welfare centers also have more buses — the 3 variables overlap |
| Welfare dist. ↔ Living population | Weak negative (-0.30) | Farther welfare centers → slightly fewer elderly outdoors (matches H1) |

### Why does this matter?
The three accessibility variables (welfare distance, bus count, subway distance) are strongly correlated with each other. Using all three separately would distort the statistics (multicollinearity).
This is why we **combined them into one composite index using PCA**.

---

## Chart 6. Accessibility vs. Elderly Living Population Scatter Plot

![Accessibility Scatter](06_접근성_vs_노인생활인구_산점도.png)

### What is this chart?
Scatter plots comparing each accessibility variable (welfare distance, bus count, subway distance) against elderly daytime living population.
A downward-right cluster would mean "worse access = fewer elderly going out."

### What did we find?
- Farther welfare centers → slightly fewer elderly outdoors (r ≈ -0.3)
- More bus stops → more elderly outdoors (r ≈ +0.3)
- Individual variables show weak but consistent relationships with H1.

### Why does this matter?
The direction aligns with our hypothesis.
Combining the three variables into one index makes the relationship clearer and more statistically reliable.

---

## Chart 7. Outlier Detection Boxplot

![Outlier Boxplot](07_이상치_탐지_박스플롯.png)

### What is this chart?
Box plots showing whether any districts have extreme outlier values (dots far above/below the box).

### What did we find?
- About 3–5% of districts show outlier values for all three variables.
- These mostly come from **large apartment complex districts** (e.g., Nowon-gu) or **welfare-center-dense commercial zones**.

### Why does this matter?
These are not data errors — they represent genuinely unusual neighborhoods.
Removing them would distort reality, so we **kept them in the analysis**.

---

## Chart 8. Dead Zone Risk Area Candidates

![Dead Zone Scatter](08_데드존_위험지역_후보.png)

### What is this chart?
A scatter plot placing Seoul's 25 districts by two axes: "elderly-alone ratio" (x) and "lack of welfare center access" (y).
Districts in the **upper right** have both high elderly-alone populations AND poor welfare access — the highest dead zone risk.

### What did we find?
- **High-risk (upper right)**: Gangbuk-gu, Nowon-gu, Dobong-gu (northern Seoul)
- **Well-served (lower left)**: Jongno-gu, Jung-gu (central Seoul)
- Some districts have many elderly living alone but decent access — showing that population alone doesn't determine dead zones.

### Why does this matter?
This chart most directly visualizes the core research question:
"Which neighborhoods are welfare dead zones?"

---

## Chart 9. PCA Accessibility Index Analysis

![PCA Analysis](09_PCA_접근성지수_분석.png)

### What is this chart?
A visualization of the PCA (Principal Component Analysis) process that compressed three correlated accessibility variables into one composite index.

### What did we find?
- The first component (PC1) captures **70.3% of the total information** from all three variables.
- PC1 alone is sufficient to represent the combined effect of welfare distance, bus access, and subway distance.
- Higher PC1 = worse accessibility (farther welfare center + fewer buses + farther subway)

### Why does this matter?
PCA resolved the multicollinearity problem.
A single index is easier to interpret and produces more reliable regression results.

---

## Chart 10. Analysis Model Comparison

![Model Comparison](10_모델_성능_비교.png)

### What is this chart?
A bar chart comparing how well the same hypothesis was tested at three different geographic scales.

### What did we find?
| Model | Sample Size | Explanatory Power (R²) | H1 Supported? |
|-------|------------|----------------------|--------------|
| Administrative district | 306 | 29.4% | ✅ Yes |
| 250m grid | 13,004 | 48.4% | ✅ Yes |
| **100m grid** | **2,226** | **53.5%** | **✅ Yes** |

- Smaller geographic units → higher explanatory power.
- All three models consistently support H1.

### Why does this matter?
"Poor welfare access → fewer elderly going outside" holds true at every scale.
This consistency across scales strengthens confidence that the finding is real, not a statistical artifact.

---

## Summary of Key Findings

| Finding | Implication |
|---------|------------|
| Worse welfare access → fewer elderly outdoors | Hypothesis H1 statistically confirmed |
| Up to 14× gap in welfare centers across districts | Severe inequality within Seoul |
| High elderly-alone rates in northern Seoul | Gangbuk-gu, Nowon-gu, Dobong-gu need priority attention |
| Three access variables are highly correlated | PCA combination was essential |
| Smaller analysis unit → better model fit | 100m grid analysis is most precise |
"""

with open(OUT / "변수관계_분석_영어.md", "w", encoding="utf-8") as f:
    f.write(en_md)
print("영어 마크다운 저장 완료")

print(f"\n완료 → {OUT}")
print("생성된 파일 목록:")
for f in sorted(OUT.iterdir()):
    print(f"  {f.name}")
