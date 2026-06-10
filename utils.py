import json
import os
import math
from datetime import datetime
from coord_convert.transform import wgs2gcj, gcj2wgs

# ------------------------------------------------------------
# 配置
# ------------------------------------------------------------
CONFIG_FILE = "obstacle_config.json"
HEARTBEAT_INTERVAL = 0.2
BASE_SPEED = 5.0
HOVER_SECONDS = 5

# ------------------------------------------------------------
# 坐标转换
# ------------------------------------------------------------
def wgs84_to_gcj02(lng, lat):
    return wgs2gcj(lng, lat)
def gcj02_to_wgs84(lng, lat):
    return gcj2wgs(lng, lat)
def transform_to_gcj02(lng, lat, from_coord):
    if from_coord == "WGS-84":
        return wgs84_to_gcj02(lng, lat)
    return lng, lat
def transform_to_display(lng, lat, to_coord):
    if to_coord == "WGS-84":
        return gcj02_to_wgs84(lng, lat)
    return lng, lat

# ------------------------------------------------------------
# 障碍物管理
# ------------------------------------------------------------
def load_obstacles():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            obstacles = data.get('obstacles', [])
            for obs in obstacles:
                if 'height' not in obs:
                    obs['height'] = 30
                if 'selected' not in obs:
                    obs['selected'] = False
            return obstacles
        except:
            return []
    return []
def save_obstacles(obstacles):
    data = {
        'obstacles': obstacles,
        'count': len(obstacles),
        'save_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'version': 'v13.3'
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ------------------------------------------------------------
# 几何辅助函数
# ------------------------------------------------------------
def distance(p1, p2):
    return math.hypot(p1[0]-p2[0], p1[1]-p2[1])
def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i+1)%n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1)*(y - y1)/(y2 - y1) + x1):
            inside = not inside
    return inside
def segments_intersect(p1, p2, p3, p4):
    def orientation(p, q, r):
        val = (q[1]-p[1])*(r[0]-q[0]) - (q[0]-p[0])*(r[1]-q[1])
        if abs(val) < 1e-10: return 0
        return 1 if val > 0 else 2
    def on_segment(p, q, r):
        return (min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and
                min(p[1], r[1]) <= q[1] <= max(p[1], r[1]))
    o1 = orientation(p1,p2,p3)
    o2 = orientation(p1,p2,p4)
    o3 = orientation(p3,p4,p1)
    o4 = orientation(p3,p4,p2)
    if o1 != o2 and o3 != o4:
        return True
    if o1==0 and on_segment(p1,p3,p2): return True
    if o2==0 and on_segment(p1,p4,p2): return True
    if o3==0 and on_segment(p3,p1,p4): return True
    if o4==0 and on_segment(p3,p2,p4): return True
    return False
def line_intersects_polygon(p1, p2, polygon):
    if point_in_polygon(p1, polygon) or point_in_polygon(p2, polygon):
        return True
    n = len(polygon)
    for i in range(n):
        p3 = polygon[i]
        p4 = polygon[(i+1)%n]
        if segments_intersect(p1, p2, p3, p4):
            return True
    return False
def get_blocking_obstacles(start, end, obstacles, flight_alt, ignore_alt=False):
    blocking = []
    for obs in obstacles:
        if ignore_alt or obs.get('height', 30) > flight_alt:
            coords = obs.get('polygon', [])
            if coords and line_intersects_polygon(start, end, coords):
                blocking.append(obs)
    return blocking
def meters_to_deg(meters, lat=32.23):
    lat_deg = meters / 111000
    lng_deg = meters / (111000 * math.cos(math.radians(lat)))
    return lng_deg, lat_deg

# ------------------------------------------------------------
# 绕行算法（优化版：递归路径规划，确保无碰撞）
# ------------------------------------------------------------
def compute_blocked_bounds(blocking_obs):
    min_lng = float('inf')
    max_lng = -float('inf')
    min_lat = float('inf')
    max_lat = -float('inf')
    for obs in blocking_obs:
        for p in obs.get('polygon', []):
            min_lng = min(min_lng, p[0])
            max_lng = max(max_lng, p[0])
            min_lat = min(min_lat, p[1])
            max_lat = max(max_lat, p[1])
    return min_lng, max_lng, min_lat, max_lat
def is_path_clear(p1, p2, obstacles, flight_alt, ignore_alt=False):
    blocking = get_blocking_obstacles(p1, p2, obstacles, flight_alt, ignore_alt)
    return len(blocking) == 0
def find_avoidance_point(start, end, obstacles, flight_alt, direction, safety_radius=5):
    blocking = get_blocking_obstacles(start, end, obstacles, flight_alt, ignore_alt=True)
    if not blocking:
        return None, []
    min_lng, max_lng, min_lat, max_lat = compute_blocked_bounds(blocking)
    safe_lat = meters_to_deg(safety_radius * 3)[1]
    safe_lng = meters_to_deg(safety_radius * 3)[0]
    if direction == "向左绕行":
        lat_offset = max_lat + safe_lat
        lng_mid = (start[0] + end[0]) / 2
        waypoint = [lng_mid, lat_offset]
    elif direction == "向右绕行":
        lat_offset = min_lat - safe_lat
        lng_mid = (start[0] + end[0]) / 2
        waypoint = [lng_mid, lat_offset]
    else:
        raise ValueError("direction must be '向左绕行' or '向右绕行'")
    max_attempts = 10
    for _ in range(max_attempts):
        collide = False
        for obs in blocking:
            if point_in_polygon(waypoint, obs['polygon']):
                collide = True
                if direction == "向左绕行":
                    waypoint[1] += safe_lat
                else:
                    waypoint[1] -= safe_lat
                break
        if not collide:
            break
    return waypoint, blocking
def plan_recursive_path(start, end, obstacles, flight_alt, direction, safety_radius=5, depth=0):
    if depth > 10:
        return [start, end]
    if is_path_clear(start, end, obstacles, flight_alt, ignore_alt=True):
        return [start, end]
    waypoint, _ = find_avoidance_point(start, end, obstacles, flight_alt, direction, safety_radius)
    if waypoint is None:
        return [start, end]
    path1 = plan_recursive_path(start, waypoint, obstacles, flight_alt, direction, safety_radius, depth+1)
    path2 = plan_recursive_path(waypoint, end, obstacles, flight_alt, direction, safety_radius, depth+1)
    full_path = path1[:-1] + path2
    return full_path
def find_left_path(start, end, obstacles, flight_alt, safety_radius=5):
    return plan_recursive_path(start, end, obstacles, flight_alt, "向左绕行", safety_radius)
def find_right_path(start, end, obstacles, flight_alt, safety_radius=5):
    return plan_recursive_path(start, end, obstacles, flight_alt, "向右绕行", safety_radius)
def find_best_path(start, end, obstacles, flight_alt, safety_radius=5):
    blocking = get_blocking_obstacles(start, end, obstacles, flight_alt, ignore_alt=False)
    if not blocking:
        return [start, end]
    left_path = find_left_path(start, end, obstacles, flight_alt, safety_radius)
    right_path = find_right_path(start, end, obstacles, flight_alt, safety_radius)
    left_len = sum(distance(left_path[i], left_path[i+1]) for i in range(len(left_path)-1))
    right_len = sum(distance(right_path[i], right_path[i+1]) for i in range(len(right_path)-1))
    return left_path if left_len <= right_len else right_path
def create_avoidance_path(start, end, obstacles, flight_alt, direction, safety_radius=5):
    if direction == "向左绕行":
        return find_left_path(start, end, obstacles, flight_alt, safety_radius)
    elif direction == "向右绕行":
        return find_right_path(start, end, obstacles, flight_alt, safety_radius)
    else:
        return find_best_path(start, end, obstacles, flight_alt, safety_radius)

# ------------------------------------------------------------
# 等分航点生成 (将折线按长度均匀分为 N 段)
# ------------------------------------------------------------
def path_length(path):
    total = 0.0
    for i in range(len(path)-1):
        total += distance(path[i], path[i+1])
    return total
def interpolate_at_distance(path, dist):
    if dist <= 0:
        return path[0][:]
    total = 0.0
    for i in range(len(path)-1):
        seg_len = distance(path[i], path[i+1])
        if total + seg_len >= dist:
            t = (dist - total) / seg_len
            lng = path[i][0] + t * (path[i+1][0] - path[i][0])
            lat = path[i][1] + t * (path[i+1][1] - path[i][1])
            return [lng, lat]
        total += seg_len
    return path[-1][:]
def generate_equidistant_waypoints(path, num_segments=6):
    if not path or num_segments <= 0:
        return path
    total_len = path_length(path)
    if total_len == 0:
        return [path[0]] * (num_segments + 1)
    step = total_len / num_segments
    waypoints = []
    for i in range(num_segments + 1):
        dist = i * step
        waypoints.append(interpolate_at_distance(path, dist))
    return waypoints

# ------------------------------------------------------------
# 心跳模拟器 (支持航点停留)
# ------------------------------------------------------------
class HeartbeatData:
    def __init__(self, flight_time, seq, lat, lng, altitude):
        self.flight_time = flight_time
        self.seq = seq
        self.lat = lat
        self.lng = lng
        self.altitude = altitude

class HeartbeatSim:
    def __init__(self, start_point):
        self.current_pos = start_point[:]   # [lng, lat]
        self.waypoints = []                 # 等分航点列表（含起点终点）
        self.current_wp_idx = 0             # 下一个目标航点索引
        self.running = False
        self.start_time = None
        self.last_update = None
        self.history = []
        self.speed_pct = 50
        self.altitude = 50
        self.total_segments = 0
        self.arrival_flag = False
        self.arrived_wp_index = -1
        self.finished = False
        # 停留相关
        self.hover_remaining = 0.0          # 当前航点剩余停留时间（秒）
        self.waiting_at_wp = False          # 是否正在停留中

    def set_path(self, waypoints, altitude, speed_pct):
        self.waypoints = [wp[:] for wp in waypoints]
        self.current_pos = waypoints[0][:]
        self.current_wp_idx = 1
        self.running = True
        self.finished = False
        self.start_time = datetime.now()
        self.last_update = None
        self.history = []
        self.speed_pct = speed_pct
        self.altitude = altitude
        self.total_segments = len(waypoints) - 1
        self.arrival_flag = False
        self.arrived_wp_index = -1
        self.hover_remaining = 0.0
        self.waiting_at_wp = False
        self._add_heartbeat(seq=1)

    def _add_heartbeat(self, seq=None, arrived=False):
        flight_t = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        if seq is None:
            seq = len(self.history) + 1
        hb = HeartbeatData(flight_t, seq, self.current_pos[1], self.current_pos[0], self.altitude)
        self.history.append(hb)
        return hb

    def update_one_step(self):
        if not self.running or self.finished:
            return None
        # 简化版 update，实际需要完整实现，这里仅示意
        return None
