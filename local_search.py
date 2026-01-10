import sys

# --- CẤU HÌNH ---
SLOTS_PER_SESSION = 6
SESSIONS_PER_DAY = 2
DAYS = 5
MAX_SLOTS = DAYS * SESSIONS_PER_DAY * SLOTS_PER_SESSION  # 60 tiết

# --- HÀM ĐỌC DỮ LIỆU ---
def input_stream():
    full_input = sys.stdin.read().split()
    iterator = iter(full_input)
    while True:
        try:
            yield int(next(iterator))
        except StopIteration:
            break

def is_valid_session(start, duration):
    end = start + duration - 1
    if end > MAX_SLOTS: return False
    return ((start - 1) // SLOTS_PER_SESSION) == ((end - 1) // SLOTS_PER_SESSION)

def solve_ultimate_local_search():
    # 1. ĐỌC DỮ LIỆU
    reader = input_stream()
    try:
        T, N, M = next(reader), next(reader), next(reader)
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
    except StopIteration: return

    # 2. CHUẨN BỊ DATA
    tasks = []
    task_counter = 0
    for c_idx, courses in enumerate(class_courses):
        for m_id in courses:
            eligible = [t for t in range(T) if m_id in teacher_abilities[t]]
            tasks.append({
                'id': task_counter,
                'c': c_idx, 'm': m_id, 
                'd': durations[m_id - 1], 
                'eligible': eligible
            })
            task_counter += 1

    # HEURISTIC SORT:
    # 1. Độ khan hiếm giáo viên (Ưu tiên môn ít người dạy) -> Rất quan trọng để đạt 100 điểm
    # 2. Môn dài -> Để xếp gọn
    tasks.sort(key=lambda x: (len(x['eligible']), -x['d'], x['c']))

    teacher_degrees = [len(s) for s in teacher_abilities]

    # Cấu trúc lưu trạng thái
    # assigned_tasks: map {task_id: (start, teacher)}
    assigned_tasks = {}
    
    # Ma trận bận: Lưu ID của task đang chiếm chỗ (để biết ai đang chắn đường)
    # Giá trị -1 là trống
    class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]

    unassigned_list = []

    # --- GIAI ĐOẠN 1: SMART GREEDY ---
    for task in tasks:
        tid = task['id']
        c, d = task['c'], task['d']
        
        # Chọn GV rảnh nhất
        candidates = sorted(task['eligible'], key=lambda t: (teacher_degrees[t], t))
        
        is_assigned = False
        for t in candidates:
            if is_assigned: break
            for s in range(1, MAX_SLOTS - d + 2):
                if not is_valid_session(s, d): continue
                
                # Check conflict
                e = s + d - 1
                conflict = False
                for k in range(s, e + 1):
                    if class_grid[c][k] != -1 or teacher_grid[t][k] != -1:
                        conflict = True; break
                
                if not conflict:
                    # Assign
                    assigned_tasks[tid] = (s, t)
                    for k in range(s, e + 1):
                        class_grid[c][k] = tid
                        teacher_grid[t][k] = tid
                    is_assigned = True
                    break
        
        if not is_assigned:
            unassigned_list.append(task)

    # --- GIAI ĐOẠN 2: LOCAL SEARCH (BUMP & INSERT) ---
    # Cố gắng chèn các task chưa xếp được bằng cách "đá" task khác ra
    
    # Lặp vài lần để thử chèn lại
    MAX_RETRIES = 3 
    for _ in range(MAX_RETRIES):
        if not unassigned_list: break
        
        still_unassigned = []
        for u_task in unassigned_list:
            u_tid = u_task['id']
            uc, ud = u_task['c'], u_task['d']
            u_candidates = sorted(u_task['eligible'], key=lambda t: (teacher_degrees[t], t))
            
            inserted = False
            
            # Duyệt tất cả các vị trí có thể đặt u_task
            for t in u_candidates:
                if inserted: break
                for s in range(1, MAX_SLOTS - ud + 2):
                    if not is_valid_session(s, ud): continue
                    
                    e = s + ud - 1
                    
                    # Tìm các task đang chắn đường (Victims)
                    conflicting_tasks = set()
                    possible_spot = True
                    
                    for k in range(s, e + 1):
                        # Nếu bị chắn bởi class khác -> Không thể đẩy (vì class đó chỉ có 1 lịch) -> Bỏ qua
                        # (Thực ra class conflict là cứng, nhưng teacher conflict có thể đổi GV)
                        ct = class_grid[uc][k]
                        if ct != -1: 
                            # u_task cần slot này của lớp uc, nhưng task ct đang chiếm
                            # Ta có thể thử dời ct sang giờ khác
                            conflicting_tasks.add(ct)
                        
                        tt = teacher_grid[t][k]
                        if tt != -1:
                            conflicting_tasks.add(tt)

                    # CHIẾN THUẬT: Chỉ thử "đá" nếu chỉ có ĐÚNG 1 task chắn đường
                    if len(conflicting_tasks) == 1:
                        victim_id = list(conflicting_tasks)[0]
                        victim_task = next((x for x in tasks if x['id'] == victim_id), None)
                        
                        if victim_task:
                            # --- THỬ DỜI VICTIM ---
                            # 1. Gỡ victim ra
                            v_s, v_t = assigned_tasks[victim_id]
                            v_c, v_d = victim_task['c'], victim_task['d']
                            v_e = v_s + v_d - 1
                            
                            # Clear grid tạm thời
                            for k in range(v_s, v_e + 1):
                                class_grid[v_c][k] = -1
                                teacher_grid[v_t][k] = -1
                            del assigned_tasks[victim_id]
                            
                            # 2. Thử đặt U_Task vào (Kiểm tra lại xem có sạch ko)
                            # (Lưu ý: Sau khi gỡ victim, slot (s, e) cho u_task phải trống hoàn toàn)
                            can_place_u = True
                            for k in range(s, e + 1):
                                if class_grid[uc][k] != -1 or teacher_grid[t][k] != -1:
                                    can_place_u = False; break
                            
                            if can_place_u:
                                # Đặt U vào tạm
                                for k in range(s, e + 1):
                                    class_grid[uc][k] = u_tid
                                    teacher_grid[t][k] = u_tid
                                assigned_tasks[u_tid] = (s, t)
                                
                                # 3. Tìm chỗ mới cho Victim
                                victim_reassigned = False
                                v_candidates = sorted(victim_task['eligible'], key=lambda tx: (teacher_degrees[tx], tx))
                                
                                for new_vt in v_candidates:
                                    if victim_reassigned: break
                                    for new_vs in range(1, MAX_SLOTS - v_d + 2):
                                        if not is_valid_session(new_vs, v_d): continue
                                        
                                        # Check conflict cho victim ở chỗ mới
                                        new_ve = new_vs + v_d - 1
                                        v_conflict = False
                                        for k in range(new_vs, new_ve + 1):
                                            if class_grid[v_c][k] != -1 or teacher_grid[new_vt][k] != -1:
                                                v_conflict = True; break
                                        
                                        if not v_conflict:
                                            # TÌM ĐƯỢC CHỖ MỚI! -> CHỐT ĐƠN
                                            for k in range(new_vs, new_ve + 1):
                                                class_grid[v_c][k] = victim_id
                                                teacher_grid[new_vt][k] = victim_id
                                            assigned_tasks[victim_id] = (new_vs, new_vt)
                                            victim_reassigned = True
                                            break
                                
                                if victim_reassigned:
                                    inserted = True
                                    break # Thành công, thoát vòng lặp slot
                                else:
                                    # Kèo này fail -> Hoàn tác U
                                    for k in range(s, e + 1):
                                        class_grid[uc][k] = -1
                                        teacher_grid[t][k] = -1
                                    del assigned_tasks[u_tid]
                            
                            # Nếu fail toàn tập -> Trả victim về chỗ cũ
                            if not inserted:
                                for k in range(v_s, v_e + 1):
                                    class_grid[v_c][k] = victim_id
                                    teacher_grid[v_t][k] = victim_id
                                assigned_tasks[victim_id] = (v_s, v_t)

            if not inserted:
                still_unassigned.append(u_task)
        
        # Cập nhật danh sách unassigned cho vòng lặp sau
        if len(still_unassigned) < len(unassigned_list):
            unassigned_list = still_unassigned
        else:
            break # Không cải thiện được nữa thì dừng

    # --- OUTPUT ---
    # Chuyển đổi kết quả về format in
    final_output = []
    for task in tasks:
        tid = task['id']
        if tid in assigned_tasks:
            s, t = assigned_tasks[tid]
            final_output.append((task['c'] + 1, task['m'], s, t + 1))
            
    print(len(final_output))
    final_output.sort(key=lambda x: (x[0], x[1]))
    for item in final_output:
        print(f"{item[0]} {item[1]} {item[2]} {item[3]}")

if __name__ == "__main__":
    solve_ultimate_local_search()