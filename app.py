import streamlit as st

st.set_page_config(page_title="南京科技职业学院 - 无人机地面站", layout="wide")

# 侧边栏导航
with st.sidebar:
    st.header("📌 导航")
    selected_page = st.radio(
        "功能页面",
        ["航线规划", "飞行监控"],
        index=0  # 默认页面
    )
    st.session_state.page = selected_page

# 根据选择加载对应页面
if selected_page == "航线规划":
    from pages import 1_航线规划
    # 如果页面文件尚未执行，可以在此导入并运行
    # 但实际上 Streamlit 会根据文件名自动加载，无需显式调用
    pass
elif selected_page == "飞行监控":
    from pages import 2_飞行监控
    pass
