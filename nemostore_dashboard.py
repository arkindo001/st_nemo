import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os

# 페이지 설정
st.set_page_config(
    page_title="Nemostore 상가 매물 대시보드",
    page_icon="🏠",
    layout="wide"
)

# 데이터 로드 함수 (캐싱 적용)
@st.cache_data
def load_data():
    db_path = 'nemostore.db' # 현재 폴더에 있다고 가정
    if not os.path.exists(db_path):
        # 만약 경로가 다르면 조정 (상위 폴더 등)
        db_path = 'e:/FCICB6-PROJ2/nemostore/nemostore.db'
    
    conn = sqlite3.connect(db_path)
    df = pd.read_sql('SELECT * FROM items', conn)
    conn.close()
    
    # 데이터 전처리
    # floor가 -1, -2 인 경우를 대비해 처리 필요할 수 있음
    return df

# 데이터 불러오기
df = load_data()

# 사이드바 설정
st.sidebar.header("🔍 검색 및 필터")

# 1. 검색 기능
search_query = st.sidebar.text_input("매물 제목 검색", "")

# 2. 가격 관련 필터
st.sidebar.subheader("💰 가격 조건 (단위: 만원)")

# 보증금 범위
min_deposit, max_deposit = int(df['deposit'].min()), int(df['deposit'].max())
deposit_range = st.sidebar.slider(
    "보증금 범위",
    min_value=min_deposit,
    max_value=max_deposit,
    value=(min_deposit, max_deposit),
    step=1000
)

# 월세 범위
min_rent, max_rent = int(df['monthlyRent'].min()), int(df['monthlyRent'].max())
rent_range = st.sidebar.slider(
    "월세 범위",
    min_value=min_rent,
    max_value=max_rent,
    value=(min_rent, max_rent),
    step=50
)

# 권리금 범위
min_premium, max_premium = int(df['premium'].min()), int(df['premium'].max())
premium_range = st.sidebar.slider(
    "권리금 범위",
    min_value=min_premium,
    max_value=max_premium,
    value=(min_premium, max_premium),
    step=1000
)

# 3. 업종 필터
st.sidebar.subheader("🏢 업종 필터")
large_categories = ["전체"] + sorted(df['businessLargeCodeName'].unique().tolist())
selected_large = st.sidebar.selectbox("업종 대분류", large_categories)

if selected_large != "전체":
    middle_categories = ["전체"] + sorted(df[df['businessLargeCodeName'] == selected_large]['businessMiddleCodeName'].unique().tolist())
else:
    middle_categories = ["전체"] + sorted(df['businessMiddleCodeName'].unique().tolist())
selected_middle = st.sidebar.selectbox("업종 중분류", middle_categories)

# 데이터 필터링 로직
filtered_df = df.copy()

# 제목 검색
if search_query:
    filtered_df = filtered_df[filtered_df['title'].str.contains(search_query, case=False, na=False)]

# 가격 필터링
filtered_df = filtered_df[
    (filtered_df['deposit'] >= deposit_range[0]) & (filtered_df['deposit'] <= deposit_range[1]) &
    (filtered_df['monthlyRent'] >= rent_range[0]) & (filtered_df['monthlyRent'] <= rent_range[1]) &
    (filtered_df['premium'] >= premium_range[0]) & (filtered_df['premium'] <= premium_range[1])
]

# 업종 필터링
if selected_large != "전체":
    filtered_df = filtered_df[filtered_df['businessLargeCodeName'] == selected_large]
if selected_middle != "전체":
    filtered_df = filtered_df[filtered_df['businessMiddleCodeName'] == selected_middle]

# --- 메인 화면 구성 ---
st.title("🏠 Nemostore 상가 매물 대시보드")
st.markdown(f"전체 매물 수: **{len(df)}** | 필터링된 매물 수: **{len(filtered_df)}**")

# 주요 지표 (KPI)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("평균 보증금", f"{filtered_df['deposit'].mean():,.0f} 만원")
with col2:
    st.metric("평균 월세", f"{filtered_df['monthlyRent'].mean():,.0f} 만원")
with col3:
    st.metric("평균 권리금", f"{filtered_df['premium'].mean():,.0f} 만원")
with col4:
    st.metric("평균 면적", f"{filtered_df['size'].mean():.2f} ㎡")

# --- 시각화 섹션 (Plotly) ---
st.divider()
st.subheader("📊 데이터 시각화 분석")

v_col1, v_col2 = st.columns(2)

with v_col1:
    # 1. 업종 대분류 분포
    fig_biz = px.bar(
        filtered_df['businessLargeCodeName'].value_counts().reset_index(),
        x='businessLargeCodeName',
        y='count',
        title="업종 대분류별 매물 수",
        labels={'count': '매물 수', 'businessLargeCodeName': '업종'},
        color='businessLargeCodeName',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_biz, use_container_width=True)

with v_col2:
    # 2. 층수 분포
    floor_counts = filtered_df['floor'].value_counts().reset_index()
    # 층수 이름을 보기 좋게 변경 (예: -1 -> 지하 1층)
    floor_counts['floor_label'] = floor_counts['floor'].apply(lambda x: f"지하 {-x}층" if x < 0 else (f"{x}층" if x > 0 else "1층(옥탑)"))
    
    fig_floor = px.pie(
        floor_counts,
        values='count',
        names='floor_label',
        title="매물 층수 분포",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    st.plotly_chart(fig_floor, use_container_width=True)

# 3. 가격대 분포 (히스토그램)
fig_hist = px.histogram(
    filtered_df,
    x='monthlyRent',
    nbins=30,
    title="월세 가격대 분포",
    labels={'monthlyRent': '월세 (만원)'},
    color_discrete_sequence=['#FF4B4B']
)
st.plotly_chart(fig_hist, use_container_width=True)

# 4. 면적 vs 월세 산점도
fig_scatter = px.scatter(
    filtered_df,
    x='size',
    y='monthlyRent',
    size='deposit',
    color='businessLargeCodeName',
    hover_name='title',
    title="면적 대비 월세 분포 (버블 크기: 보증금)",
    labels={'size': '전용면적 (㎡)', 'monthlyRent': '월세 (만원)'},
    template="plotly_white"
)
st.plotly_chart(fig_scatter, use_container_width=True)

# --- 매물 리스트 섹션 ---
st.divider()
st.subheader("📋 필터링된 매물 리스트")

# 출력할 컬럼 선택
display_cols = ['title', 'businessLargeCodeName', 'businessMiddleCodeName', 'deposit', 'monthlyRent', 'premium', 'size', 'floor', 'nearSubwayStation']
st.dataframe(
    filtered_df[display_cols].sort_values(by='monthlyRent', ascending=True),
    use_container_width=True,
    hide_index=True
)

# 매물 상세 보기 (선택한 매물)
st.sidebar.divider()
if not filtered_df.empty:
    selected_title = st.sidebar.selectbox("상세 정보를 볼 매물을 선택하세요", filtered_df['title'].tolist())
    item_detail = filtered_df[filtered_df['title'] == selected_title].iloc[0]
    
    with st.expander(f"📌 {selected_title} 상세 정보"):
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            st.write(f"**업종:** {item_detail['businessLargeCodeName']} ({item_detail['businessMiddleCodeName']})")
            st.write(f"**층수:** {item_detail['floor']}층")
            st.write(f"**면적:** {item_detail['size']} ㎡")
            st.write(f"**지하철:** {item_detail['nearSubwayStation']}")
        with d_col2:
            st.write(f"**보증금:** {item_detail['deposit']:,} 만원")
            st.write(f"**월세:** {item_detail['monthlyRent']:,} 만원")
            st.write(f"**권리금:** {item_detail['premium']:,} 만원")
            st.write(f"**조회수:** {item_detail['viewCount']} | **찜:** {item_detail['favoriteCount']}")
else:
    st.sidebar.warning("조건에 맞는 매물이 없습니다.")
