import sys

# --- CẤU HÌNH ---
SLOTS_PER_SESSION = 6
SESSIONS_PER_DAY = 2
DAYS = 5
MAX_SLOTS = DAYS * SESSIONS_PER_DAY * SLOTS_PER_SESSION  # 60 tiết

# --- BỘ ĐỌC INPUT NHANH (FAST I/O) ---
def input_stream():
    # Đọc toàn bộ input một lần để tối ưu tốc độ I/O
    full_input = sys.stdin.read().split()
    iterator = iter(full_input)
    while True:
        try:
            yield int(next(iterator))
        except StopIteration:
            break

# --- LOGIC KIỂM TRA ---
def is_valid_session(start, duration):
    """Kiểm tra môn học có bị gãy buổi (vắt qua trưa/chiều) không"""
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

    # --- TIỀN XỬ LÝ (PRE-PROCESSING) ---
    
    # 1. Tính "Độ đa năng" của từng giáo viên (Degree)
    # Giáo viên dạy được càng nhiều môn -> Càng nên để dành lại sau
    teacher_degrees = [len(abilities) for abilities in teacher_abilities]

    tasks = []
    for c_idx, courses in enumerate(class_courses):
        for m_id in courses:
            # Tìm danh sách giáo viên có thể dạy môn này
            eligible_teachers = []
            for t_idx in range(T):
                if m_id in teacher_abilities[t_idx]:
                    eligible_teachers.append(t_idx)
            
            # Lưu task kèm thông tin để sort
            tasks.append({
                'c_idx': c_idx,
                'm_id': m_id,
                'duration': durations[m_id - 1],
                'eligible': eligible_teachers,
                'num_eligible': len(eligible_teachers)
            })
    
    # --- HEURISTIC SẮP XẾP CÔNG VIỆC (TASK SORTING) ---
    # Chiến thuật: "Most Constrained First" (Cái gì khó xếp nhất thì làm trước)
    # Ưu tiên 1: Số lượng giáo viên dạy được (Tăng dần) -> Ít lựa chọn thì phải xếp ngay.
    # Ưu tiên 2: Thời lượng (Giảm dần) -> Môn dài khó nhét vào khe, nên xếp sớm.
    # Ưu tiên 3: Class Index (Tăng dần) -> Ổn định.
    tasks.sort(key=lambda x: (
        x['num_eligible'],  # Quan trọng nhất: Độ khan hiếm giáo viên
        -x['duration'],     # Quan trọng nhì: Độ dài
        x['c_idx']
    ))

    # Ma trận trạng thái (Boolean Matrix) để truy cập O(1)
    # Index 1..60
    class_busy = [[False] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_busy = [[False] * (MAX_SLOTS + 1) for _ in range(T)]
    
    final_solution = []

    # --- THUẬT TOÁN GREEDY THÔNG MINH ---
    
    for task in tasks:
        c_idx = task['c_idx']
        m_id = task['m_id']
        d = task['duration']
        candidates = task['eligible']
        
        if not candidates: continue # Không ai dạy được môn này (vô nghiệm)

        # --- HEURISTIC CHỌN GIÁO VIÊN (TEACHER SELECTION) ---
        # Trong số các GV dạy được, chọn ai?
        # Chọn người "kém đa năng" nhất (teacher_degree nhỏ nhất).
        # Logic: Để dành người giỏi (dạy được nhiều môn) cho các môn khác.
        candidates.sort(key=lambda t: (teacher_degrees[t], t))
        
        assigned = False
        
        # Duyệt từng giáo viên ứng viên
        for t_idx in candidates:
            if assigned: break
            
            # Duyệt từng slot thời gian (Earliest Start Time)
            # Quét từ 1 đến 60
            for start in range(1, MAX_SLOTS - d + 2):
                
                # 1. Check gãy buổi
                if not is_valid_session(start, d):
                    continue
                
                # 2. Check xung đột nhanh bằng Ma trận
                end = start + d - 1
                
                # Check biên trước để loại nhanh
                if class_busy[c_idx][start] or class_busy[c_idx][end] or \
                   teacher_busy[t_idx][start] or teacher_busy[t_idx][end]:
                    continue
                
                # Check kỹ phần thân
                is_conflict = False
                for k in range(start + 1, end): # start và end đã check ở trên
                    if class_busy[c_idx][k] or teacher_busy[t_idx][k]:
                        is_conflict = True
                        break
                
                if not is_conflict:
                    # --- TÌM THẤY SLOT HỢP LỆ ---
                    # Gán task và đánh dấu bận
                    for k in range(start, end + 1):
                        class_busy[c_idx][k] = True
                        teacher_busy[t_idx][k] = True
                    
                    final_solution.append((c_idx + 1, m_id, start, t_idx + 1))
                    assigned = True
                    
                    # Cập nhật Degree của giáo viên?
                    # Không cần thiết vì static degree hoạt động ổn định hơn cho Greedy
                    break
    
    # --- OUTPUT ---
    print(len(final_solution))
    # Sort lại kết quả theo Lớp -> Môn để khớp format chấm
    final_solution.sort(key=lambda x: (x[0], x[1])) 
    for item in final_solution:
        print(f"{item[0]} {item[1]} {item[2]} {item[3]}")

if __name__ == "__main__":
    solve()