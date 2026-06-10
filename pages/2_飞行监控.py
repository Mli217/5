import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import matplotlib.pyplot as plt
import random
from utils import HeartbeatData, HEARTBEAT_INTERVAL, BASE_SPEED, HOVER_SECONDS

st.header("📡 飞行实时画面 - 任务执行监控")

if 'sim' not in st.session_state or st.session_state.sim is None:
    st.warning("请先在「航线规划」页面启动飞行任务")
    st.stop()

sim = st.session_state.sim

# 更新飞行状态（逐心跳推进）
if sim.running and not sim.finished:
    steps = max(1, int(1.0 / HEARTBEAT_INTERVAL))
    for _ in range(steps):
        new_hb = sim.update_one_step()
        if new_hb:
            st.session_state.latest_hb = new_hb
        else:
            break

if sim.finished:
    st.success("🎉 飞行任务已完成！")

if st.session_state.latest_hb is None:
    st.warning("等待第一个心跳...")
    st.stop()

hb = st.session_state.latest_hb

# 显示实时数据
col1, col2, col3 = st.columns(3)
col1.metric("当前纬度", f"{hb.lat:.6f}")
col2.metric("当前经度", f"{hb.lng:.6f}")
col3.metric("高度", f"{hb.altitude} m")

# 地图显示
st.subheader("🗺️ 实时飞行地图")
# 使用 folium_static 显示地图...
st.info("地图渲染区域...")

# 通信日志
st.subheader("📋 通信日志")
if st.session_state.comm_logs:
    for log in st.session_state.comm_logs[:10]:
        st.caption(f"[{log['time']}] {log['direction']}: {log['message']}")
else:
    st.info("暂无通信日志")
