import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os
import base64

# --- 1. 페이지 설정 및 디자인 (CSS) ---
st.set_page_config(
    page_title="Nemostore Premium Dashboard",
    page_icon="🏙️",
    layout="wide"
)

# 커스텀 CSS (프리미엄 디자인)
st.markdown("""
<style>
    /* 메인 배경색 */
    .main {
        background-color: #f8f9fa;
    }
    /* 카드 스타일 */
    .stMetric {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eee;
    }
    .property-card {
        background-color: white;
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .property-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.12);
    }
    .price-tag {
        color: #FF4B4B;
        font-weight: bold;
        font-size: 1.2rem;
    }
    .info-label {
        color: #666;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터 로드 및 전처리 ---
@st.cache_data
def load_data():
    db_path = 'nemostore.db'
    if not os.path.exists(db_path):
        db_path = 'e:/FCICB6-PROJ2/nemostore/nemostore.db'
    
    conn = sqlite3.connect(db_path)
    df = pd.read_sql('SELECT * FROM items', conn)
    conn.close()
    
    # 층수 전처리
    df['floor_label'] = df['floor'].apply(lambda x: f"지하 {-x}층" if x < 0 else (f"{x}층" if x > 0 else "1층(옥탑)"))
    
    # 면적당 월세 계산 (평당 단가 개념)
    df['price_per_sqm'] = df['monthlyRent'] / df['size']
    
    return df

df = load_data()

# 전체 평균 계산 (Delta용)
avg_deposit = df['deposit'].mean()
avg_rent = df['monthlyRent'].mean()
avg_premium = df['premium'].mean()

# --- 3. 사이드바 (검색 및 멀티 필터) ---
st.sidebar.title("🏙️ Nemostore")
st.sidebar.markdown("---")

search_query = st.sidebar.text_input("📍 매물 제목/지역 검색", "")

# 멀티셀렉트 필터
all_large_cats = sorted(df['businessLargeCodeName'].unique().tolist())
selected_large = st.sidebar.multiselect("업종 대분류 선택", all_large_cats, default=all_large_cats[:2] if len(all_large_cats)>2 else all_large_cats)

# 가격 슬라이더 (실시간 필터링)
st.sidebar.subheader("💰 가격 필터 (만원)")
deposit_range = st.sidebar.slider("보증금", 0, int(df['deposit'].max()), (0, int(df['deposit'].max())), step=1000)
rent_range = st.sidebar.slider("월세", 0, int(df['monthlyRent'].max()), (0, int(df['monthlyRent'].max())), step=50)
premium_range = st.sidebar.slider("권리금", 0, int(df['premium'].max()), (0, int(df['premium'].max())), step=1000)

# 데이터 필터링 로직
mask = (
    (df['title'].str.contains(search_query, case=False, na=False)) &
    (df['businessLargeCodeName'].isin(selected_large)) &
    (df['deposit'].between(deposit_range[0], deposit_range[1])) &
    (df['monthlyRent'].between(rent_range[0], rent_range[1])) &
    (df['premium'].between(premium_range[0], premium_range[1]))
)
filtered_df = df[mask]

# --- 4. 메인 대시보드 (탭 구조) ---
tab1, tab2, tab3 = st.tabs(["📊 종합 대시보드", "🔍 매물 탐색", "📈 상세 데이터 분석"])

# --- Tab 1: 종합 대시보드 ---
with tab1:
    st.title("🏡 실시간 시장 요약")
    
    # KPI 섹션 (Delta 포함)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        current_avg_rent = filtered_df['monthlyRent'].mean() if not filtered_df.empty else 0
        diff_rent = current_avg_rent - avg_rent
        st.metric("평균 월세", f"{current_avg_rent:,.0f} 만원", delta=f"{diff_rent:,.0f} 만원", delta_color="inverse")
    with kpi2:
        current_avg_dep = filtered_df['deposit'].mean() if not filtered_df.empty else 0
        diff_dep = current_avg_dep - avg_deposit
        st.metric("평균 보증금", f"{current_avg_dep:,.0f} 만원", delta=f"{diff_dep:,.0f} 만원", delta_color="inverse")
    with kpi3:
        current_avg_pre = filtered_df['premium'].mean() if not filtered_df.empty else 0
        diff_pre = current_avg_pre - avg_premium
        st.metric("평균 권리금", f"{current_avg_pre:,.0f} 만원", delta=f"{diff_pre:,.0f} 만원", delta_color="inverse")
    with kpi4:
        st.metric("검색 결과", f"{len(filtered_df)} 건", delta=f"전체의 {len(filtered_df)/len(df)*100:.1f}%")

    st.markdown("---")
    
    # 차트 섹션
    c1, c2 = st.columns(2)
    with c1:
        # 업종별 비중 (Donut)
        fig_pie = px.pie(
            filtered_df, names='businessLargeCodeName', title="선택 업종 비중",
            hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_layout(showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with c2:
        # 월세 분포 (Histogram + Box)
        fig_dist = px.histogram(
            filtered_df, x="monthlyRent", title="월세 가격대 분포",
            marginal="box", color_discrete_sequence=['#636EFA']
        )
        st.plotly_chart(fig_dist, use_container_width=True)

# --- Tab 2: 매물 탐색 (그리드 레이아웃) ---
with tab2:
    st.subheader("🏠 필터링된 매물 리스트")
    
    # 데이터 다운로드 버튼
    csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 필터링 결과 다운로드 (CSV)", csv, "nemostore_filtered.csv", "text/csv")
    
    if filtered_df.empty:
        st.warning("조건에 맞는 매물이 없습니다.")
    else:
        # 3열 그리드로 매물 카드 배치
        rows = (len(filtered_df) // 3) + 1
        for i in range(rows):
            cols = st.columns(3)
            for j in range(3):
                idx = i * 3 + j
                if idx < len(filtered_df):
                    item = filtered_df.iloc[idx]
                    with cols[j]:
                        img_url = item['previewPhotoUrl'] if item['previewPhotoUrl'] else "https://via.placeholder.com/300x200?text=No+Image"
                        st.markdown(f"""
                        <div class="property-card">
                            <img src="{img_url}" style="width:100%; border-radius:10px; margin-bottom:10px;">
                            <h4 style="margin:5px 0;">{item['title'][:25]}...</h4>
                            <p class="price-tag">월세 {item['monthlyRent']:,} / 보증 {item['deposit']:,}</p>
                            <p class="info-label">📍 {item['nearSubwayStation']}<br>📏 {item['size']}㎡ | {item['floor_label']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"상세보기 #{item['number']}", key=f"btn_{item['id']}"):
                            st.session_state['selected_item'] = item['id']

# --- Tab 3: 상세 데이터 분석 ---
with tab3:
    st.subheader("📈 시장 심층 분석")
    
    an_col1, an_col2 = st.columns(2)
    
    with an_col1:
        # 1. 면적당 평단가 분석 (가성비 매물 찾기)
        fig_area = px.scatter(
            filtered_df, x="size", y="monthlyRent", size="price_per_sqm",
            color="businessLargeCodeName", hover_name="title",
            title="면적 vs 월세 (버블 크기: ㎡당 단가)",
            labels={"size": "전용면적(㎡)", "monthlyRent": "월세(만원)"},
            template="plotly_white"
        )
        st.plotly_chart(fig_area, use_container_width=True)
    
    with an_col2:
        # 2. 지하철역별 평균 월세 (상위 10개)
        station_avg = filtered_df.groupby('nearSubwayStation')['monthlyRent'].mean().sort_values(ascending=False).head(10).reset_index()
        fig_station = px.bar(
            station_avg, x="monthlyRent", y="nearSubwayStation", orientation='h',
            title="주요 지하철역별 평균 월세 TOP 10",
            color="monthlyRent", color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_station, use_container_width=True)

    # 3. 키워드 분석 (상위 10개)
    st.markdown("---")
    st.subheader("🔍 주요 키워드 트렌드")
    titles = " ".join(filtered_df['title'].astype(str))
    # 간단한 단어 빈도 분석 (명사 위주 유추 - 실제로는 KoNLPy 등이 좋으나 여기서는 간단히 공백 기준)
    word_counts = pd.Series(titles.split()).value_counts().head(15).reset_index()
    fig_word = px.bar(
        word_counts, x="count", y="index", orientation='h',
        title="매물 제목 빈출 키워드",
        labels={"index": "키워드", "count": "빈도"},
        color="count"
    )
    st.plotly_chart(fig_word, use_container_width=True)

# 푸터
st.sidebar.markdown("---")
st.sidebar.caption("© 2026 Nemostore Advanced Analytics Dashboard")
