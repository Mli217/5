# 南京科技职业学院 - 无人机地面站系统（多页版）

这是一个基于 Streamlit 开发的无人机地面站控制系统，具备 **航线规划、飞行监控、障碍物管理、坐标转换** 功能。

## 功能特点
- **航线规划**：在地图上点击设置起点/终点，支持手动输入坐标、方向微调，自动生成避障航线。
- **飞行监控**：实时模拟飞行轨迹、心跳包、航线进度、通信日志记录。
- **障碍物管理**：在地图上绘制多边形障碍物，自动避障路径规划，支持保存/加载配置。
- **坐标系统**：支持 WGS-84 / GCJ-02 坐标转换，并适配相应的高德地图底图。

## 部署到 Streamlit Cloud
1. 将此仓库 `Fork` 到你的 GitHub 账号。
2. 登录 [Streamlit Cloud](https://share.streamlit.io/)。
3. 点击 "New app"，选择你 Fork 的仓库和分支。
4. 主文件路径填写 `app.py`。
5. 点击 "Deploy"，等待部署完成。

## 本地运行
```bash
pip install -r requirements.txt
streamlit run app.py
