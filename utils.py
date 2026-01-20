import sys

# --- CẤU HÌNH CHUNG ---
SLOTS_PER_SESSION = 6
MAX_SLOTS = 60  # 5 ngày * 2 buổi * 6 tiết

def input_stream():
    """Hàm đọc dữ liệu an toàn từ stdin"""
    try:
        input_data = sys.stdin.read().split()
    except Exception:
        return None
    if not input_data:
        return None
    
    iterator = iter(input_data)
    while True:
        try:
            yield int(next(iterator))
        except StopIteration:
            break

def is_valid_session(start, duration):
    """Kiểm tra môn học có bị vắt qua trưa/chiều không"""
    end = start + duration - 1
    if end > MAX_SLOTS: return False
    # Công thức: (start-1)//6 phải bằng (end-1)//6
    return ((start - 1) // SLOTS_PER_SESSION) == ((end - 1) // SLOTS_PER_SESSION)

def load_and_preprocess():
    """
    Hàm Tiền xử lý trung tâm:
    1. Đọc dữ liệu
    2. Phẳng hóa Task
    3. Tính toán trước các Slot hợp lệ
    4. Sắp xếp Heuristic
    """
    reader = input_stream()
    if reader is None: return None

    # 1. ĐỌC DỮ LIỆU THÔ
    try:
        T = next(reader) # Số giáo viên
        N = next(reader) # Số lớp
        M = next(reader) # Số môn
        
        class_courses = []
        for _ in range(N):
            curr = []
            while True:
                val = next(reader)
                if val == 0: break
                curr.append(val)
            class_courses.append(curr)
            
        teacher_abilities = []
        for _ in range(T):
            curr = set()
            while True:
                val = next(reader)
                if val == 0: break
                curr.add(val)
            teacher_abilities.append(curr)
            
        durations = []
        for _ in range(M): durations.append(next(reader))
        
    except StopIteration:
        return None

    # 2. PHẲNG HÓA DATA (FLATTENING) -> DANH SÁCH TASK
    tasks = []
    task_counter = 0
    for c_idx, courses in enumerate(class_courses):
        for m_id in courses:
            # Tìm giáo viên dạy được môn này
            eligible = [t for t in range(T) if m_id in teacher_abilities[t]]
            
            # Thời lượng
            d = durations[m_id - 1]
            
            tasks.append({
                'id': task_counter,
                'c': c_idx,         # Index lớp (0-based)
                'm': m_id,          # ID môn (1-based theo input)
                'd': d,             # Thời lượng
                'eligible': eligible, # Danh sách GV dạy được
                'num_eligible': len(eligible) # Để sort nhanh
            })
            task_counter += 1

    # 3. SẮP XẾP HEURISTIC (STATIC ORDERING)
    # Ưu tiên: Ít giáo viên -> Môn dài -> Index lớp nhỏ
    tasks.sort(key=lambda x: (x['num_eligible'], -x['d'], x['c']))

    # 4. TÍNH TRƯỚC SLOT HỢP LỆ (CACHING)
    # Map: Duration -> List of valid start slots
    valid_starts = {}
    # Giả sử môn dài nhất không quá 12 tiết
    max_duration = max(durations) if durations else 12
    
    for d in range(1, max_duration + 1):
        valid_starts[d] = []
        for s in range(1, MAX_SLOTS - d + 2):
            if is_valid_session(s, d):
                valid_starts[d].append(s)

    # Trả về gói dữ liệu đã xử lý sạch sẽ
    return {
        'T': T, 'N': N, 'M': M,
        'tasks': tasks,
        'valid_starts': valid_starts,
        'num_tasks': len(tasks)
    }