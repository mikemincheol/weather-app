import pandas as pd
import streamlit as st

DATA_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/"
    "refs/heads/main/data/seoul_daily.csv"
)
MIN_VALID_DAYS = 350  # 연간 유효 날짜 수 기준

st.set_page_config(page_title="서울 연도별 평균 기온", layout="wide")
st.title("서울 연도별 평균 기온 분석")


@st.cache_data(show_spinner="데이터를 불러오는 중입니다")
def load_data(url: str) -> pd.DataFrame:
    return pd.read_csv(url)


df = load_data(DATA_URL)

# 열 이름은 파일에 맞춰 자동으로 찾고, 없으면 기본값을 사용
DATE_COL = "날짜" if "날짜" in df.columns else df.columns[0]
TEMP_COL = "평균기온" if "평균기온" in df.columns else df.columns[1]

df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
df[TEMP_COL] = pd.to_numeric(df[TEMP_COL], errors="coerce")

# ------------------------------------------------------------------
# 1. 데이터 개요
# ------------------------------------------------------------------
st.header("1. 데이터 개요")

c1, c2, c3, c4 = st.columns(4)
c1.metric("전체 행 수", f"{len(df):,}")
c2.metric("기록 시작일", df[DATE_COL].min().strftime("%Y-%m-%d"))
c3.metric("기록 종료일", df[DATE_COL].max().strftime("%Y-%m-%d"))
c4.metric("평균 기온 결측값", f"{df[TEMP_COL].isna().sum():,}개")

st.subheader("열 이름")
col_info = pd.DataFrame(
    {
        "열 이름": df.columns,
        "자료형": [str(t) for t in df.dtypes],
        "결측값 수": df.isna().sum().values,
    }
)
st.dataframe(col_info, hide_index=True, width="stretch")

invalid_dates = int(df[DATE_COL].isna().sum())
if invalid_dates:
    st.warning(f"날짜를 해석할 수 없는 행이 {invalid_dates}개 있어 분석에서 제외합니다.")
    df = df.dropna(subset=[DATE_COL])

# ------------------------------------------------------------------
# 2. 중복 날짜 확인
# ------------------------------------------------------------------
st.header("2. 중복 날짜 확인")

dup_mask = df[DATE_COL].duplicated(keep=False)
dup_rows = df[dup_mask].sort_values(DATE_COL)
n_dup_dates = dup_rows[DATE_COL].nunique()

if dup_rows.empty:
    st.success("같은 날짜가 중복된 기록은 없습니다.")
else:
    st.error(
        f"중복된 날짜가 {n_dup_dates}개 있습니다 (해당 행 {len(dup_rows)}개). "
        "날짜별로 평균 기온의 평균을 취해 하나로 합쳐서 분석합니다."
    )
    st.dataframe(dup_rows, hide_index=True, width="stretch")
    df = df.groupby(DATE_COL, as_index=False)[TEMP_COL].mean()

# ------------------------------------------------------------------
# 3. 연도별 유효 날짜 수와 분석 대상 선정
# ------------------------------------------------------------------
st.header("3. 연도별 유효 날짜 수")

df["연도"] = df[DATE_COL].dt.year
valid = df.dropna(subset=[TEMP_COL])

yearly = (
    valid.groupby("연도")
    .agg(유효_날짜_수=(TEMP_COL, "size"), 평균기온=(TEMP_COL, "mean"))
    .reindex(sorted(df["연도"].unique()))
)
yearly["유효_날짜_수"] = yearly["유효_날짜_수"].fillna(0).astype(int)
yearly["포함 여부"] = yearly["유효_날짜_수"] >= MIN_VALID_DAYS

included = yearly[yearly["포함 여부"]].copy()
excluded = yearly[~yearly["포함 여부"]].copy()

c1, c2 = st.columns(2)
c1.metric(f"분석에 포함된 연도 ({MIN_VALID_DAYS}일 이상)", f"{len(included)}개")
c2.metric("분석에서 제외된 연도", f"{len(excluded)}개")

st.subheader("분석에서 제외한 연도")
if excluded.empty:
    st.info("제외된 연도가 없습니다.")
else:
    st.dataframe(
        excluded[["유효_날짜_수"]].rename(columns={"유효_날짜_수": "유효 날짜 수"}),
        width="stretch",
    )

with st.expander("전체 연도의 유효 날짜 수 보기"):
    st.dataframe(
        yearly[["유효_날짜_수", "포함 여부"]].rename(
            columns={"유효_날짜_수": "유효 날짜 수"}
        ),
        width="stretch",
    )

# ------------------------------------------------------------------
# 4. 연도별 평균 기온
# ------------------------------------------------------------------
st.header("4. 연도별 평균 기온")

result = included[["평균기온", "유효_날짜_수"]].rename(
    columns={"평균기온": "연평균 기온(°C)", "유효_날짜_수": "유효 날짜 수"}
)
result["연평균 기온(°C)"] = result["연평균 기온(°C)"].round(2)

st.line_chart(result["연평균 기온(°C)"])
st.dataframe(result, width="stretch")

st.download_button(
    "연도별 평균 기온 CSV 내려받기",
    data=result.reset_index().to_csv(index=False).encode("utf-8-sig"),
    file_name="seoul_yearly_mean_temp.csv",
    mime="text/csv",
)
