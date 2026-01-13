import sys
import time # Import time

# --- CẤU HÌNH ---
SLOTS_PER_SESSION = 6
MAX_SLOTS = 60

# --- HÀM HỖ TRỢ ĐỌC DỮ LIỆU ---
def input_stream(input_content=None):
    if input_content:
        full_input = input_content.split()
    else:
        try:
            full_input = sys.stdin.read().split()
        except Exception: return
        
    if not full_input: return
    
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

# Thêm tham số time_limit
def solve(input_content=None, time_limit=0.95):
    start_time = time.time() # Ghi nhận thời gian bắt đầu
    
    reader = input_stream(input_content)
    try:
        T_val = next(reader)
        N_val = next(reader)
        M_val = next(reader)
        T, N, M = int(T_val), int(N_val), int(M_val)
        
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
    except StopIteration: return 0

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
    tasks.sort(key=lambda x: (len(x['eligible']), -x['d'], x['c']))

    teacher_degrees = [len(s) for s in teacher_abilities]

    assigned_tasks = {}
    class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]

    unassigned_list = []

    # --- GIAI ĐOẠN 1: SMART GREEDY ---
    for task in tasks:
        # Check time limit
        if time.time() - start_time > time_limit: break
        
        tid = task['id']
        c, d = task['c'], task['d']
        
        candidates = sorted(task['eligible'], key=lambda t: (teacher_degrees[t], t))
        
        is_assigned = False
        for t in candidates:
            if is_assigned: break
            for s in range(1, MAX_SLOTS - d + 2):
                if not is_valid_session(s, d): continue
                
                e = s + d - 1
                conflict = False
                for k in range(s, e + 1):
                    if class_grid[c][k] != -1 or teacher_grid[t][k] != -1:
                        conflict = True; break
                
                if not conflict:
                    assigned_tasks[tid] = (s, t)
                    for k in range(s, e + 1):
                        class_grid[c][k] = tid
                        teacher_grid[t][k] = tid
                    is_assigned = True
                    break
        
        if not is_assigned:
            unassigned_list.append(task)

    # --- GIAI ĐOẠN 2: LOCAL SEARCH (BUMP & INSERT) ---
    MAX_RETRIES = 3 
    for _ in range(MAX_RETRIES):
        # Check time limit trong vòng lặp cải thiện
        if time.time() - start_time > time_limit: break
        
        if not unassigned_list: break
        
        still_unassigned = []
        for u_task in unassigned_list:
            if time.time() - start_time > time_limit: break # Check kỹ hơn
            
            u_tid = u_task['id']
            uc, ud = u_task['c'], u_task['d']
            u_candidates = sorted(u_task['eligible'], key=lambda t: (teacher_degrees[t], t))
            
            inserted = False
            
            for t in u_candidates:
                if inserted: break
                for s in range(1, MAX_SLOTS - ud + 2):
                    if not is_valid_session(s, ud): continue
                    
                    e = s + ud - 1
                    
                    conflicting_tasks = set()
                    possible_spot = True
                    
                    for k in range(s, e + 1):
                        ct = class_grid[uc][k]
                        if ct != -1: 
                            conflicting_tasks.add(ct)
                        
                        tt = teacher_grid[t][k]
                        if tt != -1:
                            conflicting_tasks.add(tt)

                    if len(conflicting_tasks) == 1:
                        victim_id = list(conflicting_tasks)[0]
                        victim_task = next((x for x in tasks if x['id'] == victim_id), None)
                        
                        if victim_task:
                            # --- THỬ DỜI VICTIM ---
                            v_s, v_t = assigned_tasks[victim_id]
                            v_c, v_d = victim_task['c'], victim_task['d']
                            v_e = v_s + v_d - 1
                            
                            # Clear grid tạm thời
                            for k in range(v_s, v_e + 1):
                                class_grid[v_c][k] = -1
                                teacher_grid[v_t][k] = -1
                            del assigned_tasks[victim_id]
                            
                            # Thử đặt U_Task vào
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
                                
                                # Tìm chỗ mới cho Victim
                                victim_reassigned = False
                                v_candidates = sorted(victim_task['eligible'], key=lambda tx: (teacher_degrees[tx], tx))
                                
                                for new_vt in v_candidates:
                                    if victim_reassigned: break
                                    for new_vs in range(1, MAX_SLOTS - v_d + 2):
                                        if not is_valid_session(new_vs, v_d): continue
                                        
                                        new_ve = new_vs + v_d - 1
                                        v_conflict = False
                                        for k in range(new_vs, new_ve + 1):
                                            if class_grid[v_c][k] != -1 or teacher_grid[new_vt][k] != -1:
                                                v_conflict = True; break
                                        
                                        if not v_conflict:
                                            for k in range(new_vs, new_ve + 1):
                                                class_grid[v_c][k] = victim_id
                                                teacher_grid[new_vt][k] = victim_id
                                            assigned_tasks[victim_id] = (new_vs, new_vt)
                                            victim_reassigned = True
                                            break
                                
                                if victim_reassigned:
                                    inserted = True
                                    break 
                                else:
                                    # Hoàn tác U
                                    for k in range(s, e + 1):
                                        class_grid[uc][k] = -1
                                        teacher_grid[t][k] = -1
                                    del assigned_tasks[u_tid]
                            
                            if not inserted:
                                # Trả victim về chỗ cũ
                                for k in range(v_s, v_e + 1):
                                    class_grid[v_c][k] = victim_id
                                    teacher_grid[v_t][k] = victim_id
                                assigned_tasks[victim_id] = (v_s, v_t)

            if not inserted:
                still_unassigned.append(u_task)
        
        if len(still_unassigned) < len(unassigned_list):
            unassigned_list = still_unassigned
        else:
            break

    # --- OUTPUT ---
    final_output = []
    for task in tasks:
        tid = task['id']
        if tid in assigned_tasks:
            s, t = assigned_tasks[tid]
            final_output.append((task['c'] + 1, task['m'], s, t + 1))
            
    if input_content is None:
        print(len(final_output))
        final_output.sort(key=lambda x: (x[0], x[1]))
        for item in final_output:
            print(f"{item[0]} {item[1]} {item[2]} {item[3]}")

    return len(final_output)

if __name__ == "__main__":
    solve()