import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os
import requests
import json

# --- 1. 페이지 설정 및 디자인 (CSS) ---
st.set_page_config(
    page_title="Nemostore Premium Dashboard",
    page_icon="🏙️",
    layout="wide"
)

# 자치구 코드 매핑
GU_MAP = {
    '11110': '종로구', '11140': '중구', '11170': '용산구', '11200': '성동구', '11215': '광진구',
    '11230': '동대문구', '11260': '중랑구', '11290': '성북구', '11305': '강북구', '11320': '도봉구',
    '11350': '노원구', '11380': '은평구', '11410': '서대문구', '11440': '마포구', '11470': '양천구',
    '11500': '강서구', '11530': '구로구', '11545': '금천구', '11560': '영등포구', '11590': '동작구',
    '11620': '관악구', '11650': '서초구', '11680': '강남구', '11710': '송파구', '11740': '강동구'
}

# 자치구 중심 좌표 (위도, 경도)
GU_COORDS = {
    '종로구': [37.5730, 126.9794], '중구': [37.5641, 126.9979], '용산구': [37.5326, 126.9902],
    '성동구': [37.5633, 127.0371], '광진구': [37.5385, 127.0824], '동대문구': [37.5744, 127.0400],
    '중랑구': [37.6065, 127.0927], '성북구': [37.5891, 127.0182], '강북구': [37.6396, 127.0255],
    '도봉구': [37.6688, 127.0471], '노원구': [37.6542, 127.0568], '은평구': [37.6027, 126.9291],
    '서대문구': [37.5791, 126.9368], '마포구': [37.5662, 126.9016], '양천구': [37.5169, 126.8665],
    '강서구': [37.5509, 126.8497], '구로구': [37.4954, 126.8875], '금천구': [37.4568, 126.8954],
    '영등포구': [37.5264, 126.8962], '동작구': [37.5124, 126.9395], '관악구': [37.4784, 126.9515],
    '서초구': [37.4836, 127.0327], '강남구': [37.4959, 127.0664], '송파구': [37.5145, 127.1061],
    '강동구': [37.5301, 127.1238]
}

# 커스텀 CSS
st.markdown("""
<style>
    .stMetric { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #eee; }
    .property-card { background-color: white; padding: 15px; border-radius: 15px; box-shadow: 0 8px 16px rgba(0,0,0,0.08); border: 1px solid #f0f0f0; margin-bottom: 20px; transition: transform 0.2s; }
    .property-card:hover { transform: translateY(-5px); box-shadow: 0 12px 24px rgba(0,0,0,0.12); }
    .price-tag { color: #FF4B4B; font-weight: bold; font-size: 1.2rem; }
    .info-label { color: #666; font-size: 0.9rem; }
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
    
    # 층수 및 구 데이터 전처리
    df['floor_label'] = df['floor'].apply(lambda x: f"지하 {-x}층" if x < 0 else (f"{x}층" if x > 0 else "1층(옥탑)"))
    
    # PNU에서 자치구 코드 추출 및 위도/경도 매핑
    df['gu_code'] = df['buildingManagementSerialNumber'].astype(str).str[:5]
    df['gu_name'] = df['gu_code'].map(GU_MAP)
    df['lat'] = df['gu_name'].apply(lambda x: GU_COORDS.get(x, [0, 0])[0])
    df['lon'] = df['gu_name'].apply(lambda x: GU_COORDS.get(x, [0, 0])[1])
    
    # 면적당 월세 계산
    df['price_per_sqm'] = df['monthlyRent'] / df['size']
    
    return df

@st.cache_data
def load_geojson():
    # 서울시 자치구 GeoJSON 데이터 (GitHub 공공 데이터 활용)
    url = 'https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json'
    resp = requests.get(url)
    return resp.json()

df = load_data()
seoul_geojson = load_geojson()

# 전체 평균
avg_deposit = df['deposit'].mean()
avg_rent = df['monthlyRent'].mean()
avg_premium = df['premium'].mean()

# --- 3. 사이드바 ---
st.sidebar.title("🏙️ Nemostore")
st.sidebar.markdown("---")

search_query = st.sidebar.text_input("📍 매물 제목/지역 검색", "")
selected_large = st.sidebar.multiselect("업종 대분류 선택", sorted(df['businessLargeCodeName'].unique().tolist()), default=sorted(df['businessLargeCodeName'].unique().tolist()))

st.sidebar.subheader("💰 가격 필터 (만원)")
deposit_range = st.sidebar.slider("보증금", 0, int(df['deposit'].max()), (0, int(df['deposit'].max())), step=1000)
rent_range = st.sidebar.slider("월세", 0, int(df['monthlyRent'].max()), (0, int(df['monthlyRent'].max())), step=50)
premium_range = st.sidebar.slider("권리금", 0, int(df['premium'].max()), (0, int(df['premium'].max())), step=1000)

mask = (
    (df['title'].str.contains(search_query, case=False, na=False)) &
    (df['businessLargeCodeName'].isin(selected_large)) &
    (df['deposit'].between(deposit_range[0], deposit_range[1])) &
    (df['monthlyRent'].between(rent_range[0], rent_range[1])) &
    (df['premium'].between(premium_range[0], premium_range[1]))
)
filtered_df = df[mask]

# --- 4. 메인 대시보드 (탭 구조) ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 종합 대시보드", "🗺️ 서울 지도 분석", "🔍 매물 탐색", "📈 상세 데이터 분석"])

# --- Tab 1: 종합 대시보드 ---
with tab1:
    st.title("🏡 실시간 시장 요약")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        c_rent = filtered_df['monthlyRent'].mean() if not filtered_df.empty else 0
        st.metric("평균 월세", f"{c_rent:,.0f} 만원", delta=f"{c_rent - avg_rent:,.0f} 만원", delta_color="inverse")
    with k2:
        c_dep = filtered_df['deposit'].mean() if not filtered_df.empty else 0
        st.metric("평균 보증금", f"{c_dep:,.0f} 만원", delta=f"{c_dep - avg_deposit:,.0f} 만원", delta_color="inverse")
    with k3:
        c_pre = filtered_df['premium'].mean() if not filtered_df.empty else 0
        st.metric("평균 권리금", f"{c_pre:,.0f} 만원", delta=f"{c_pre - avg_premium:,.0f} 만원", delta_color="inverse")
    with k4:
        st.metric("검색 결과", f"{len(filtered_df)} 건", delta=f"전체의 {len(filtered_df)/len(df)*100:.1f}%")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        fig_pie = px.pie(filtered_df, names='businessLargeCodeName', title="선택 업종 비중", hole=0.5)
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        fig_dist = px.histogram(filtered_df, x="monthlyRent", title="월세 가격대 분포", marginal="box")
        st.plotly_chart(fig_dist, use_container_width=True)

# --- Tab 2: 서울 지도 분석 (Choropleth) ---
with tab2:
    st.title("🗺️ 서울시 자치구별 매물 분석")
    
    # 구별 데이터 집계
    gu_stats = filtered_df.groupby('gu_name').agg({
        'monthlyRent': 'mean',
        'deposit': 'mean',
        'id': 'count'
    }).reset_index().rename(columns={'id': '매물수', 'monthlyRent': '평균월세', 'deposit': '평균보증금'})
    
    m_col1, m_col2 = st.columns([2, 1])
    
    with m_col1:
        # Choropleth Map 구현
        fig_map = px.choropleth_mapbox(
            gu_stats,
            geojson=seoul_geojson,
            locations='gu_name',
            featureidkey="properties.name",
            color='평균월세',
            color_continuous_scale="Reds",
            mapbox_style="carto-positron",
            zoom=10,
            center={"lat": 37.5633, "lon": 126.9037},
            opacity=0.6,
            labels={'평균월세': '평균 월세(만원)'},
            title="서울시 자치구별 평균 월세 현황"
        )
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)

    with m_col2:
        st.write("📍 **자치구별 주요 통계**")
        st.dataframe(gu_stats.sort_values(by='평균월세', ascending=False), hide_index=True)
        
        # 위도/경도를 활용한 버블 맵 (추가 시각화)
        fig_bubble = px.scatter_mapbox(
            gu_stats, lat=gu_stats['gu_name'].map(lambda x: GU_COORDS[x][0]),
            lon=gu_stats['gu_name'].map(lambda x: GU_COORDS[x][1]),
            size="매물수", color="평균월세",
            hover_name="gu_name", size_max=30, zoom=9,
            mapbox_style="carto-positron", title="자치구별 매물 밀집도"
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

# --- Tab 3: 매물 탐색 (그리드 레이아웃) ---
with tab3:
    st.subheader("🏠 필터링된 매물 리스트")
    csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 필터링 결과 다운로드 (CSV)", csv, "nemostore_filtered.csv", "text/csv")
    
    if filtered_df.empty:
        st.warning("조건에 맞는 매물이 없습니다.")
    else:
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

# --- Tab 4: 상세 데이터 분석 ---
with tab4:
    an_col1, an_col2 = st.columns(2)
    with an_col1:
        fig_area = px.scatter(
            filtered_df, x="size", y="monthlyRent", size="price_per_sqm",
            color="businessLargeCodeName", hover_name="title", title="면적 vs 월세 (버블 크기: ㎡당 단가)"
        )
        st.plotly_chart(fig_area, use_container_width=True)
    with an_col2:
        station_avg = filtered_df.groupby('nearSubwayStation')['monthlyRent'].mean().sort_values(ascending=False).head(10).reset_index()
        fig_station = px.bar(station_avg, x="monthlyRent", y="nearSubwayStation", orientation='h', title="주요 지하철역별 평균 월세 TOP 10")
        st.plotly_chart(fig_station, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("© 2026 Nemostore Advanced Analytics Dashboard")
