import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, MousePosition
import json
import datetime
import math

# ==================== 页面配置 ====================
st.set_page_config(page_title="航线规划 - 3D地图", layout="wide")
st.title("🗺️ 航线规划 (3D地图 + 多边形障碍物圈选)")

# ==================== 坐标转换 ====================
try:
    from utils import gcj02_to_wgs84
    def to_wgs84(lat, lng, input_type):
        if input_type == "GCJ-02":
            try:
                wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
                return wgs_lat, wgs_lng
            except:
                return lat, lng
        else:
            return lat, lng
except ImportError:
    def to_wgs84(lat, lng, input_type):
        return lat, lng

# ==================== 初始化会话状态 ====================
if 'coord_type' not in st.session_state:
    st.session_state.coord_type = "WGS-84"
if 'pointA' not in st.session_state:
    st.session_state.pointA = {"lat": 32.2322, "lng": 118.749}
if 'pointB' not in st.session_state:
    st.session_state.pointB = {"lat": 32.2343, "lng": 118.749}
if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 50
if 'polygon_obstacles' not in st.session_state:
    st.session_state.polygon_obstacles = []
if 'last_save_time' not in st.session_state:
    st.session_state.last_save_time = None
if 'pending_polygon' not in st.session_state:
    st.session_state.pending_polygon = None
if 'map_refresh' not in st.session_state:
    st.session_state.map_refresh = 0

# ==================== 布局 ====================
left_col, right_col = st.columns([3.5, 1.2])

# ==================== 左侧：地图 ====================
with left_col:
    latA_w, lngA_w = to_wgs84(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
    latB_w, lngB_w = to_wgs84(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)

    center_lat = (latA_w + latB_w) / 2
    center_lng = (lngA_w + lngB_w) / 2
    if not (-90 <= center_lat <= 90) or not (-180 <= center_lng <= 180):
        center_lat, center_lng = 32.233, 118.749

    # 底图切换
    if st.session_state.coord_type == "GCJ-02":
        m = folium.Map(location=[center_lat, center_lng], zoom_start=16, control_scale=True,
                       tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                       attr="Tiles © Esri — Source: Esri")
    else:
        m = folium.Map(location=[center_lat, center_lng], zoom_start=16, control_scale=True,
                       tiles='http://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
                       attr='高德地图')

    # 标记点、航线、障碍物、高度标注等（此处直接复用之前的代码）
    folium.Marker([latA_w, lngA_w], popup=f"起点 A<br>{latA_w:.6f}, {lngA_w:.6f}", icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(m)
    folium.Marker([latB_w, lngB_w], popup=f"终点 B<br>{latB_w:.6f}, {lngB_w:.6f}", icon=folium.Icon(color="red", icon="stop", prefix="fa")).add_to(m)
    folium.PolyLine([(latA_w, lngA_w), (latB_w, lngB_w)], color="blue", weight=5, opacity=0.8, dash_array="5, 10").add_to(m)

    for obs in st.session_state.polygon_obstacles:
        coords = obs["coordinates"]
        poly_coords = [[c[1], c[0]] for c in coords]
        height = obs.get("height", 40)
        folium.Polygon(locations=poly_coords, color="red", fill=True, fill_color="red", fill_opacity=0.2, weight=3).add_to(m)
        cx = sum(c[0] for c in coords) / len(coords)
        cy = sum(c[1] for c in coords) / len(coords)
        folium.Marker([cy, cx], icon=folium.DivIcon(html=f'<div style="background:rgba(0,0,0,0.7); color:white; padding:2px 6px; border-radius:12px;">{height}m</div>')).add_to(m)

    # 添加绘图工具
    Draw(
        draw_options={
            "polygon": {"shapeOptions": {"color": "#ffdd00"}, "allowIntersection": False},
            "rectangle": {"shapeOptions": {"color": "#ffdd00"}},
            "circle": {"shapeOptions": {"color": "#ffdd00"}},
        },
        edit_options={"edit": True, "remove": True}
    ).add_to(m)
    MousePosition().add_to(m)

    # ===== 核心修复：使用动态 Key 渲染地图 =====
    # 每次触发 st.session_state.map_refresh 都会重建一个新的地图实例
    output = st_folium(
        m,
        height=800,
        use_container_width=True,
        key=f"map_key_{st.session_state.map_refresh}",
        returned_objects=["last_draw"]
    )

    # ===== 捕获绘图 =====
    if output and output.get("last_draw") and output["last_draw"].get("geometry"):
        geom = output["last_draw"]["geometry"]
        if geom["type"] in ["Polygon", "Circle"]:
            coords = geom["coordinates"][0]
            st.session_state.pending_polygon = coords
            # 不要在这里调用 st.rerun()，而是增加 refresh 计数，让 Streamlit 自行刷新
            st.session_state.map_refresh += 1

# ==================== 右侧：控制面板 ====================
# (控制面板代码与之前完全一样，此处略去以节省篇幅，请保留原控制面板代码)
with right_col:
    st.subheader("🎮 控制面板")
    # ... 原有的右侧按钮和设置代码 ...
    # 你需要保留所有右侧的控制逻辑，以及“确认添加”障碍物的逻辑。
    # 在“确认添加”成功之后，同样执行： st.session_state.map_refresh += 1
    
    # 以下仅为展示确认添加的逻辑：
    if st.session_state.pending_polygon:
        st.warning("📍 检测到新绘制的障碍物")
        with st.form("add_obs"):
            name = st.text_input("名称", "障碍物")
            height = st.number_input("高度", 10, 200, 40)
            if st.form_submit_button("✅ 确认添加"):
                new_obs = {"name": name, "coordinates": st.session_state.pending_polygon, "height": height}
                st.session_state.polygon_obstacles.append(new_obs)
                st.session_state.pending_polygon = None
                st.session_state.map_refresh += 1  # 刷新地图
                st.rerun()

# ==================== 底部数据展示 ====================
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
c2.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
c3.metric("飞行高度", f"{st.session_state.flight_height} 米")
