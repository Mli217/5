import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, MousePosition
import math
from datetime import datetime
from utils import (
    wgs84_to_gcj02, gcj02_to_wgs84, transform_to_gcj02,
    load_obstacles, save_obstacles,
    create_avoidance_path, generate_equidistant_waypoints, path_length,
    HeartbeatSim, HOVER_SECONDS
)

st.header("🗺️ 航线规划 - 点击地图 + 方向微调 + 手动输入坐标")

# 初始化状态
if 'points_gcj' not in st.session_state:
    st.session_state.points_gcj = {'A': [118.746426, 32.232384], 'B': [118.750966, 32.236290]}
if 'plan_path' not in st.session_state:
    st.session_state.plan_path = None
if 'waypoints' not in st.session_state:
    st.session_state.waypoints = None
if 'flight_alt' not in st.session_state:
    st.session_state.flight_alt = 50
if 'drone_speed' not in st.session_state:
    st.session_state.drone_speed = 50
if 'safety_radius' not in st.session_state:
    st.session_state.safety_radius = 5
if 'avoid_direction' not in st.session_state:
    st.session_state.avoid_direction = "最佳航线"
if 'point_select_mode' not in st.session_state:
    st.session_state.point_select_mode = 'A'
if 'flight_started' not in st.session_state:
    st.session_state.flight_started = False
if 'obstacles' not in st.session_state:
    st.session_state.obstacles = load_obstacles()

def update_plan_and_waypoints():
    if st.session_state.points_gcj.get('A') and st.session_state.points_gcj.get('B'):
        path = create_avoidance_path(
            st.session_state.points_gcj['A'],
            st.session_state.points_gcj['B'],
            st.session_state.obstacles,
            st.session_state.flight_alt,
            st.session_state.avoid_direction,
            st.session_state.safety_radius
        )
        st.session_state.plan_path = path
        waypoints = generate_equidistant_waypoints(path, num_segments=6)
        st.session_state.waypoints = waypoints
    else:
        st.session_state.plan_path = None
        st.session_state.waypoints = None

# 布局
col_map, col_panel = st.columns([3, 1.2])

with col_panel:
    st.markdown("### 🎮 控制面板")
    with st.expander("✏️ 手动输入起点/终点坐标", expanded=False):
        st.markdown("**注意：坐标将根据左侧「坐标系设置」自动转换为GCJ-02存储**")
        col_a_in, col_b_in = st.columns(2)
        with col_a_in:
            st.markdown("#### 起点 A")
            a_lng_input = st.number_input("经度 (A)", value=st.session_state.points_gcj['A'][0], format="%.6f", key="manual_a_lng")
            a_lat_input = st.number_input("纬度 (A)", value=st.session_state.points_gcj['A'][1], format="%.6f", key="manual_a_lat")
        with col_b_in:
            st.markdown("#### 终点 B")
            b_lng_input = st.number_input("经度 (B)", value=st.session_state.points_gcj['B'][0], format="%.6f", key="manual_b_lng")
            b_lat_input = st.number_input("纬度 (B)", value=st.session_state.points_gcj['B'][1], format="%.6f", key="manual_b_lat")
        if st.button("📌 应用手动输入坐标", key="apply_manual_coords"):
            # 简化为直接使用 GCJ-02
            st.session_state.points_gcj['A'] = [a_lng_input, a_lat_input]
            st.session_state.points_gcj['B'] = [b_lng_input, b_lat_input]
            update_plan_and_waypoints()
            st.success("坐标已更新")
            st.rerun()

    st.markdown("---")
    select_mode = st.radio("当前可移动的点", ["起点 (A)", "终点 (B)"],
                          index=0 if st.session_state.point_select_mode == 'A' else 1,
                          key="move_select", horizontal=True)
    st.session_state.point_select_mode = 'A' if select_mode == "起点 (A)" else 'B'

    st.markdown("#### 📍 当前坐标 (GCJ-02)")
    a_lng, a_lat = st.session_state.points_gcj['A']
    b_lng, b_lat = st.session_state.points_gcj['B']
    st.text(f"起点 A : {a_lng:.6f}, {a_lat:.6f}")
    st.text(f"终点 B : {b_lng:.6f}, {b_lat:.6f}")

    st.subheader("✈️ 飞行参数")
    new_alt = st.slider("飞行高度 (m)", 10, 200, st.session_state.flight_alt, 5)
    if new_alt != st.session_state.flight_alt:
        st.session_state.flight_alt = new_alt
        update_plan_and_waypoints()
        st.rerun()
    new_speed = st.slider("速度系数 (%)", 10, 100, st.session_state.drone_speed, 5)
    st.session_state.drone_speed = new_speed
    new_radius = st.slider("安全半径 (米)", 1, 20, st.session_state.safety_radius, 1)
    if new_radius != st.session_state.safety_radius:
        st.session_state.safety_radius = new_radius
        update_plan_and_waypoints()
        st.rerun()

    st.subheader("🤖 避障策略")
    direction = st.radio("绕行方向", ["最佳航线", "向左绕行", "向右绕行"],
                         index=["最佳航线", "向左绕行", "向右绕行"].index(st.session_state.avoid_direction))
    if direction != st.session_state.avoid_direction:
        st.session_state.avoid_direction = direction
        update_plan_and_waypoints()
        st.rerun()

    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("▶️ 开始飞行", type="primary", use_container_width=True):
            a = st.session_state.points_gcj.get('A')
            b = st.session_state.points_gcj.get('B')
            if a and b and st.session_state.waypoints and len(st.session_state.waypoints) >= 2:
                st.session_state.sim = HeartbeatSim(a.copy())
                st.session_state.sim.set_path(st.session_state.waypoints, st.session_state.flight_alt, st.session_state.drone_speed)
                st.session_state.flight_started = True
                st.success("飞行已开始，切换至「飞行监控」查看动态")
                st.rerun()
            else:
                st.error("请先设置起点、终点，并确保已生成等分航点")
    with col_stop:
        if st.button("⏹️ 停止飞行", use_container_width=True):
            st.session_state.flight_started = False
            if st.session_state.sim:
                st.session_state.sim.running = False
            st.info("飞行已停止")
            st.rerun()

with col_map:
    if st.session_state.plan_path is None:
        update_plan_and_waypoints()
    # 绘制地图... (使用原始代码中的 create_planning_map 函数)
    st.info("地图显示区域...")
