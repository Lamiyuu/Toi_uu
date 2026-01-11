import sys
import time
import random

# --- CẤU HÌNH ---
SLOTS_PER_SESSION = 6
MAX_SLOTS = 60
TIME_LIMIT = 0.95 

# --- BỘ ĐỌC INPUT SỬA LẠI (Dạng kết thúc bằng 0) ---
def input_stream():
    try:
        input_data = sys.stdin.read().split()
    except Exception: return
    if not input_data: return
    
    iterator = iter(input_data)
    while True:
        try:
            yield int(next(iterator))
        except StopIteration: break

def solve():
    start_time = time.time()
    reader = input_stream()
    
    # 1. HEADER
    try:
        T_val = next(reader)
        N_val = next(reader)
        M_val = next(reader)
        T, N, M = int(T_val), int(N_val), int(M_val)
    except StopIteration:
        return

    # 2. ĐỌC CLASSES (Sửa lại: Đọc đến khi gặp số 0)
    class_courses = []
    for c_id in range(N):
        curr = []
        while True:
            try:
                val = next(reader)
                if val == 0: break
                curr.append(val)
            except StopIteration: break
        class_courses.append(curr)
    
    # 3. ĐỌC TEACHERS (Sửa lại: Đọc đến khi gặp số 0)
    # Mở rộng mảng để tránh lỗi index nếu input có môn ID > M
    course_teachers = [[] for _ in range(M + 50)] 
    
    teachers_read_count = 0
    for t_id in range(1, T + 1):
        try:
            # Kiểm tra xem còn dữ liệu không trước khi đọc
            # (Hack để tránh lỗi nếu file kết thúc bất ngờ)
            first_val = next(reader) 
            if first_val == 0: # Trường hợp dòng rỗng chỉ có số 0
                teachers_read_count += 1
                continue
                
            # Xử lý giá trị đầu tiên vừa đọc
            m_id = first_val
            if m_id < len(course_teachers):
                course_teachers[m_id].append(t_id)
            
            # Đọc tiếp các giá trị còn lại cho đến khi gặp 0
            while True:
                val = next(reader)
                if val == 0: break
                m_id = val
                if m_id < len(course_teachers):
                    course_teachers[m_id].append(t_id)
            
            teachers_read_count += 1
        except StopIteration: break
        

    # 4. ĐỌC DURATIONS
    # Input duration là dòng cuối cùng, không có số 0 ngắt giữa các môn
    durations = [0]
    durations_read_count = 0
    
    # Đọc đúng M số
    for _ in range(M):
        try:
            val = next(reader)
            durations.append(val)
            durations_read_count += 1
        except StopIteration:
            durations.append(1) # Default
            

    # --- CHUẨN BỊ TASK ---
    tasks = []
    skipped = 0
    for c_idx, courses in enumerate(class_courses):
        for m_id in courses:
            if m_id < len(durations):
                tasks.append((c_idx, m_id))
            else:
                skipped += 1
    
    
    if not tasks:
        print(0)
        return

    # --- PRE-CALCULATION ---
    valid_starts = [[] for _ in range(13)]
    for d in range(1, 13):
        for start in range(1, MAX_SLOTS - d + 2):
            end = start + d - 1
            if ((start - 1) // SLOTS_PER_SESSION) == ((end - 1) // SLOTS_PER_SESSION):
                valid_starts[d].append(start)

    # --- RANDOMIZED GREEDY ---
    best_solution = []
    best_score = -1
    loop_count = 0
    
    while True:
        loop_count += 1
        if loop_count % 50 == 0:
            if time.time() - start_time > TIME_LIMIT: break
        
        # Shuffle task
        current_tasks = list(tasks)
        random.shuffle(current_tasks)
        
        current_sol = []
        class_busy = [0] * N
        teacher_busy = [0] * (T + 1)
        cnt = 0
        
        for c_idx, m_id in current_tasks:
            d = durations[m_id]
            candidates = course_teachers[m_id]
            if not candidates: continue
            
            # Chọn giáo viên ngẫu nhiên trong danh sách
            start_offset = random.randint(0, len(candidates) - 1)
            assigned = False
            
            for i in range(len(candidates)):
                t_id = candidates[(start_offset + i) % len(candidates)]
                
                # Check collision
                c_mask = class_busy[c_idx]
                t_mask = teacher_busy[t_id]
                if (c_mask & t_mask): # Sơ loại nhanh (optional)
                     pass 

                combined = c_mask | t_mask
                
                # Find First Fit Slot
                for start in valid_starts[d]:
                    mask = ((1 << d) - 1) << (start - 1)
                    if (combined & mask) == 0:
                        class_busy[c_idx] |= mask
                        teacher_busy[t_id] |= mask
                        current_sol.append((c_idx + 1, m_id, start, t_id))
                        cnt += 1
                        assigned = True
                        break
                if assigned: break
        
        if cnt > best_score:
            best_score = cnt
            best_solution = list(current_sol)
            if cnt == len(tasks): break

    # --- OUTPUT ---
    print(len(best_solution))
    best_solution.sort(key=lambda x: (x[0], x[1]))
    for item in best_solution:
        print(f"{item[0]} {item[1]} {item[2]} {item[3]}")

if __name__ == "__main__":
    solve()