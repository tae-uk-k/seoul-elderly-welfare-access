"""
데이터 카탈로그 자동 생성 스크립트
실행: python 03_분석스크립트/make_data_catalog.py
출력: 04_분석결과/데이터_카탈로그.md
"""

import pandas as pd
import os
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

BASE = Path(__file__).parent.parent

# ── 파일 메타 정의 ─────────────────────────────────────────────────────────────
# (파일 상대경로, 인코딩, 헤더행, 주제, 분석단위, 기준시점, 출처)
FILE_META = [
    # 원본데이터
    ("01_원본데이터/노인복지시설_서울_2025.xlsx",               "utf-8",      2, "복지시설",  "시설",    "2025",      "서울시 열린데이터광장"),
    ("01_원본데이터/독거노인_현황_행정동별_2024.xlsx",          "utf-8",      3, "인구",      "행정동",  "2024",      "서울시 통계"),
    ("01_원본데이터/버스정류소_위치정보_2026년5월.xlsx",        "utf-8",      0, "교통",      "정류소",  "2026-05",   "서울 버스정보 시스템"),
    ("01_원본데이터/도시철도_역사정보_전국_2026년2월.xlsx",     "utf-8",      0, "교통",      "역사",    "2026-02",   "국가철도공단"),
    ("01_원본데이터/생활인구_자치구별_2025.csv",                "utf-8-sig",  0, "인구",      "자치구",  "2025",      "서울시 생활인구"),
    ("01_원본데이터/생활인구_행정동별_시간대별_2026년4월.csv",  "utf-8-sig",  0, "인구",      "행정동",  "2026-04",   "서울시 생활인구"),
    ("01_원본데이터/연령별_인구현황_서울_2026년4월.csv",        "cp949",      0, "인구",      "행정동",  "2026-04",   "주민등록 인구통계"),
    ("01_원본데이터/주민등록인구_세대현황_서울_2026년4월.csv",  "cp949",      0, "인구",      "행정동",  "2026-04",   "주민등록 인구통계"),
    ("01_원본데이터/연령별_인구현황_자치구_2026년3월.xlsx",     "utf-8",      2, "인구",      "자치구",  "2026-03",   "주민등록 인구통계"),
    ("01_원본데이터/_census_reqdoc_1779542403896/2024년_인구_다사_100M.csv",  "cp949", 0, "인구", "100m격자", "2024", "통계청 인구총조사"),
    ("01_원본데이터/_census_reqdoc_1779542403896/2024년_인구_다사_500M.csv",  "cp949", 0, "인구", "500m격자", "2024", "통계청 인구총조사"),
    # 가공데이터
    ("02_가공데이터/서울_노인복지시설_정제.xlsx",               "utf-8",      0, "복지시설",  "시설",    "2025",      "가공 (원본 → 정제)"),
    ("02_가공데이터/서울_복지시설_접근성분석용.xlsx",           "utf-8",      0, "복지시설",  "시설",    "2025",      "가공 (분석 대상만 필터)"),
    ("02_가공데이터/서울_노인복지시설_좌표.xlsx",               "utf-8",      0, "복지시설",  "시설",    "2025",      "가공 (지오코딩 완료)"),
    ("02_가공데이터/서울_복지시설_제외목록.xlsx",               "utf-8",      0, "복지시설",  "시설",    "2025",      "가공 (제외 사유 포함)"),
    ("02_가공데이터/서울_노인복지시설_제거목록.xlsx",           "utf-8",      0, "복지시설",  "시설",    "2025",      "가공 (중복/폐업 제거)"),
    ("02_가공데이터/지오코딩_실패목록.xlsx",                    "utf-8",      0, "복지시설",  "시설",    "2025",      "가공 (지오코딩 실패)"),
    ("02_가공데이터/지오코딩_재시도_결과.xlsx",                 "utf-8",      0, "복지시설",  "시설",    "2025",      "가공 (재시도 결과)"),
    ("02_가공데이터/지오코딩_최종실패.xlsx",                    "utf-8",      0, "복지시설",  "시설",    "2025",      "가공 (최종 미처리)"),
    ("02_가공데이터/격자별_생활인구_65세이상.csv",              "utf-8-sig",  0, "인구",      "행정동",  "2026-04",   "가공 (65세↑ 필터)"),
    ("02_가공데이터/독거노인_행정동코드포함.csv",               "utf-8-sig",  0, "인구",      "행정동",  "2024",      "가공 (행정동코드 조인)"),
    ("02_가공데이터/서울_지하철역_좌표.csv",                    "utf-8-sig",  0, "교통",      "역사",    "2026-02",   "가공 (서울 필터)"),
    ("02_가공데이터/행정동별_65세이상인구.csv",                 "utf-8-sig",  0, "인구",      "행정동",  "2026-04",   "가공 (행정동 집계)"),
    # 분석결과
    ("04_분석결과/analysis_100m_20260523/100m_격자_분석데이터.csv", "utf-8-sig", 0, "분석결과", "100m격자", "2026-05", "분석 산출물"),
]


def read_file(rel_path, encoding, header_row):
    path = BASE / rel_path
    if not path.exists():
        return None, None
    ext = path.suffix.lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(path, encoding=encoding, low_memory=False)
        else:
            df = pd.read_excel(path, header=header_row)
        return df, path.stat().st_size
    except Exception:
        return None, path.stat().st_size if path.exists() else None


def fmt_size(n):
    if n is None:
        return "?"
    if n >= 1024 ** 2:
        return f"{n / 1024**2:.1f} MB"
    return f"{n / 1024:.0f} KB"


def key_cols(df, n=5):
    if df is None:
        return "읽기 실패"
    cols = [c for c in df.columns if not str(c).startswith("Unnamed")]
    sample = cols[:n]
    more = len(cols) - n
    s = ", ".join(sample)
    if more > 0:
        s += f" 외 {more}개"
    return s


# ── 테이블 1: 파일 개요 ────────────────────────────────────────────────────────
rows1 = []
for rel_path, enc, hdr, topic, unit, period, source in FILE_META:
    folder = rel_path.split("/")[0].replace("01_원본데이터", "01 원본").replace(
        "02_가공데이터", "02 가공").replace("04_분석결과", "04 분석결과")
    fname = Path(rel_path).name
    fmt = Path(rel_path).suffix.upper().lstrip(".")
    df, sz = read_file(rel_path, enc, hdr)
    nrow = len(df) if df is not None else "?"
    ncol = len(df.columns) if df is not None else "?"
    kcols = key_cols(df)
    rows1.append({
        "구분": folder,
        "파일명": fname,
        "형식": fmt,
        "주제": topic,
        "분석단위": unit,
        "행": f"{nrow:,}" if isinstance(nrow, int) else nrow,
        "열": ncol,
        "크기": fmt_size(sz),
        "기준시점": period,
        "핵심 변수 (앞 5개)": kcols,
        "출처/비고": source,
    })

df1 = pd.DataFrame(rows1)

# ── 테이블 2: 분석 변수 매핑 ───────────────────────────────────────────────────
var_map = [
    ("y_living_100m",   "65세 이상 생활인구 (100m 격자)",   "02_가공데이터/격자별_생활인구_65세이상.csv",         "격자별 집계 후 조인"),
    ("pop65_100m",      "65세 이상 등록인구 (100m 격자)",   "01_원본데이터/_census_reqdoc_1779542403896/2024년_인구_다사_100M.csv", "격자코드 조인"),
    ("alone_100m",      "독거노인 수 (100m 격자)",          "02_가공데이터/독거노인_행정동코드포함.csv",          "행정동→격자 면적 비례 배분"),
    ("dist_welfare",    "가장 가까운 복지시설까지 거리(m)",  "02_가공데이터/서울_복지시설_접근성분석용.xlsx",      "KD-Tree 최근접 탐색"),
    ("bus_count_500m",  "반경 500m 내 버스정류소 수",       "01_원본데이터/버스정류소_위치정보_2026년5월.xlsx",   "공간 버퍼 카운트"),
    ("access_index",    "복합 접근성 지수",                 "dist_welfare + bus_count_500m",                     "역수 가중합 정규화"),
    ("행정동코드",      "행정동 식별자 (8자리)",            "공통 키",                                           "조인 기준 컬럼"),
    ("GRID_CD",         "100m 격자 식별자",                 "공통 키",                                           "조인 기준 컬럼"),
]
df2 = pd.DataFrame(var_map, columns=["변수명", "설명", "원천 파일", "가공 방법"])


# ── 마크다운 출력 ──────────────────────────────────────────────────────────────
def df_to_md(df):
    cols = df.columns.tolist()
    header = "| " + " | ".join(cols) + " |"
    sep    = "| " + " | ".join(["---"] * len(cols)) + " |"
    lines  = [header, sep]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(lines)


md = f"""# 데이터 카탈로그

> 자동 생성: `03_분석스크립트/make_data_catalog.py`
> 마지막 업데이트: {pd.Timestamp.today().strftime("%Y-%m-%d")}

---

## 1. 파일 개요

{df_to_md(df1)}

---

## 2. 분석 변수 매핑

{df_to_md(df2)}

---

### 데이터 계보 요약

```
[원본] 노인복지시설_서울_2025.xlsx
        ↓ 불필요 시설 제거·지오코딩
[가공] 서울_복지시설_접근성분석용.xlsx  (분석 대상 485개)

[원본] 생활인구_행정동별_시간대별_2026년4월.csv
        ↓ 65세 이상 컬럼 합산
[가공] 격자별_생활인구_65세이상.csv

[원본] 2024년_인구_다사_100M.csv  (통계청 격자 인구)
[가공] 독거노인_행정동코드포함.csv
        ↓ 세 데이터 + 시설·버스 공간조인
[분석] 100m_격자_분석데이터.csv  (60,528 격자 × 11 변수)
```
"""

out_path = BASE / "04_분석결과" / "데이터_카탈로그.md"
out_path.write_text(md, encoding="utf-8")
print(f"저장 완료: {out_path}")
print("\n" + md)
