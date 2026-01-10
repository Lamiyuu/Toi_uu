import sys

# --- CẤU HÌNH ---
SLOTS_PER_SESSION = 6
SESSIONS_PER_DAY = 2
DAYS = 5
MAX_SLOTS = DAYS * SESSIONS_PER_DAY * SLOTS_PER_SESSION  # 60 tiết

# --- BỘ ĐỌC INPUT NHANH ---
def input_stream():
    input_buffer = []
    # Đọc tất cả input một lần để giảm I/O latency
    full_input = sys.stdin.read().split()
    iterator = iter(full_input)
    while True:
        try:
            yield int(next(iterator))
        except StopIteration:
            break

# --- LOGIC KIỂM TRA ---
def is_valid_session(start, duration):
    """Kiểm tra môn học có bị vắt qua buổi trưa/chiều không"""
    end = start + duration - 1
    if end > MAX_SLOTS: return False
    start_session = (start - 1) // SLOTS_PER_SESSION
    end_session = (end - 1) // SLOTS_PER_SESSION
    return start_session == end_session

def solve():
    reader = input_stream()
    
    try:
        T = next(reader)
        N = next(reader)
        M = next(reader)
        
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
        for _ in range(M):
            durations.append(next(reader))
            
    except StopIteration:
        return

    # --- CHUẨN BỊ DỮ LIỆU ---
    tasks = []
    for c_idx, courses in enumerate(class_courses):
        for m_id in courses:
            tasks.append((c_idx, m_id))
    
    # --- HEURISTIC SẮP XẾP (QUAN TRỌNG) ---
    # 1. Ưu tiên môn dài (Duration giảm dần) -> Khó xếp nhất
    # 2. Ưu tiên môn có ít giáo viên dạy được (Tăng dần) -> Khan hiếm nguồn lực
    # 3. Ưu tiên lớp có số hiệu nhỏ -> Ổn định thứ tự
    
    # Pre-calculate số lượng giáo viên cho mỗi môn để sort nhanh
    teacher_counts = {}
    for m in range(1, M + 1):
        count = sum(1 for t in range(T) if m in teacher_abilities[t])
        teacher_counts[m] = count

    tasks.sort(key=lambda x: (
        -durations[x[1]-1],      # Môn dài xếp trước
        teacher_counts[x[1]],    # Môn ít GV dạy xếp trước
        x[0]                     # Class ID
    ))

    # --- CẤU TRÚC DỮ LIỆU TỐI ƯU (MA TRẬN) ---
    # class_busy[class_id][slot] = True/False
    # teacher_busy[teacher_id][slot] = True/False
    # Dùng mảng cố định kích thước 61 (index 1..60) để truy cập O(1)
    class_busy = [[False] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_busy = [[False] * (MAX_SLOTS + 1) for _ in range(T)]
    
    final_solution = []

    # --- THUẬT TOÁN GREEDY (FIRST FIT) ---
    # Vì input lớn, ta dùng Greedy thay vì Backtracking đệ quy sâu.
    # Với cách sắp xếp Heuristic tốt, Greedy sẽ tìm ra lời giải gần như tối ưu.
    
    for c_idx, m_id in tasks:
        d = durations[m_id - 1]
        
        # Lọc danh sách giáo viên, sort theo ID
        candidates = sorted([t for t in range(T) if m_id in teacher_abilities[t]])
        
        assigned = False
        
        # Tìm slot và giáo viên phù hợp
        # Chiến thuật: Quét toàn bộ time slot, tìm GV đầu tiên rảnh
        for t_idx in candidates:
            if assigned: break
            
            for start in range(1, MAX_SLOTS - d + 2):
                if not is_valid_session(start, d):
                    continue
                
                # Kiểm tra xung đột nhanh bằng ma trận
                # Chỉ cần check các slot từ start -> start+d-1
                is_conflict = False
                end = start + d - 1
                
                # Check nhanh: Nếu đầu hoặc đuôi bận thì bỏ qua luôn (optimization)
                if class_busy[c_idx][start] or class_busy[c_idx][end] or \
                   teacher_busy[t_idx][start] or teacher_busy[t_idx][end]:
                    continue

                # Check kỹ từng slot
                for k in range(start, end + 1):
                    if class_busy[c_idx][k] or teacher_busy[t_idx][k]:
                        is_conflict = True
                        break
                
                if not is_conflict:
                    # TÌM THẤY! Gán ngay (Greedy)
                    # Đánh dấu bận
                    for k in range(start, end + 1):
                        class_busy[c_idx][k] = True
                        teacher_busy[t_idx][k] = True
                    
                    final_solution.append((c_idx + 1, m_id, start, t_idx + 1))
                    assigned = True
                    break
    
    # --- OUTPUT ---
    print(len(final_solution))
    final_solution.sort(key=lambda x: (x[0], x[1])) # Sort theo Class -> Course
    for item in final_solution:
        print(f"{item[0]} {item[1]} {item[2]} {item[3]}")

if __name__ == "__main__":
    solve()