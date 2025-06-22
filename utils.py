import screeninfo

# 로그 출력
def log(msg):
    print(f"[LOG] {msg}")

# 화면 중앙 좌표 구하기
def calc_center(x, y, w, h):
    return x + w // 2, y + h // 2

# 현재 모니터 해상도 정보 가져오기
def get_monitor_info():
    screen = screeninfo.get_monitors()[0]
    return {
        "width": screen.width,
        "height": screen.height
    }

# 좌표 값 문자열 변환 (저장용)
def region_to_str(x, y, w, h):
    return f"{x},{y},{w},{h}"

# 문자열 좌표 값 파싱 (불러오기용)
def str_to_region(region_str):
    x, y, w, h = map(int, region_str.split(','))
    return x, y, w, h
