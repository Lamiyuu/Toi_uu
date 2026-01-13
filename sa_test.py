import sys
import math
import random
import time

# --- CẤU HÌNH ---
SLOTS_PER_SESSION = 6
SESSIONS_PER_DAY = 2
DAYS = 5
MAX_SLOTS = DAYS * SESSIONS_PER_DAY * SLOTS_PER_SESSION # 60 tiết

# --- HÀM HỖ TRỢ ---
def input_stream(input_content=None):
    """
    Bộ đọc dữ liệu đa năng:
    - Nếu input_content có dữ liệu (khi chạy Benchmark): Đọc từ biến này.
    - Nếu input_content là None (khi nộp bài): Đọc từ sys.stdin (bàn phím).
    """
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
    """Kiểm tra môn học có bị vắt qua trưa/chiều không"""
    end = start + duration - 1
    if end > MAX_SLOTS: return False
    return ((start - 1) // SLOTS_PER_SESSION) == ((end - 1) // SLOTS_PER_SESSION)

# --- THÊM THAM SỐ time_limit ---
def solve(input_content=None, time_limit=0.95):
    start_time_prog = time.time()
    reader = input_stream(input_content)
    
    # 1. ĐỌC DỮ LIỆU
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
                'd': durations[m_id - 1], 'eligible': eligible
            })
            task_counter += 1

    # --- HEURISTIC SORT ---
    tasks.sort(key=lambda x: (len(x['eligible']), -x['d'], x['c']))
    
    # --- KHỞI TẠO ---
    assigned = {} 
    class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]
    unassigned = [] 

    # Cache valid slots
    valid_starts_cache = {}
    for d in range(1, 13):
        valid_starts_cache[d] = [s for s in range(1, MAX_SLOTS - d + 2) if is_valid_session(s, d)]

    # --- RANDOM CONSTRUCT ---
    for task in tasks:
        tid, c, d = task['id'], task['c'], task['d']
        candidates = list(task['eligible'])
        random.shuffle(candidates)
        is_set = False
        
        for t in candidates:
            if is_set: break
            possible_slots = list(valid_starts_cache.get(d, []))
            random.shuffle(possible_slots)
            
            for s in possible_slots:
                e = s + d - 1
                ok = True
                for k in range(s, e + 1):
                    if class_grid[c][k] != -1 or teacher_grid[t][k] != -1:
                        ok = False; break
                if ok:
                    assigned[tid] = (s, t)
                    for k in range(s, e + 1):
                        class_grid[c][k] = tid
                        teacher_grid[t][k] = tid
                    is_set = True
                    break 
        
        if not is_set:
            unassigned.append(tid)

    # --- HÀM MỤC TIÊU ---
    def get_score(n_unassigned, sum_start):
        return n_unassigned * 1000000 + sum_start

    current_score = get_score(len(unassigned), sum(v[0] for v in assigned.values()))
    best_assigned = assigned.copy()
    best_score = current_score

    # --- SA LOOP ---
    T_curr = 5000.0 
    alpha = 0.98   

    # DÙNG time_limit THAY VÌ BIẾN CỐ ĐỊNH
    while time.time() - start_time_prog < time_limit:
        mode = "INSERT" if unassigned else "OPTIMIZE"
        move_type = None
        u_tid = -1
        victim_tid = -1
        new_s, new_t = -1, -1
        old_s, old_t = -1, -1
        delta_score = 0
        
        if mode == "INSERT":
            if not unassigned: continue
            u_tid = random.choice(unassigned)
            u_task = next(t for t in tasks if t['id'] == u_tid)
            uc, ud = u_task['c'], u_task['d']
            
            candidates_moves = []
            u_teachers = u_task['eligible']
            if len(u_teachers) > 5: u_teachers = random.sample(u_teachers, 5)
            
            for t in u_teachers:
                for s in valid_starts_cache.get(ud, []):
                    e = s + ud - 1
                    blockers = set()
                    possible = True
                    for k in range(s, e + 1):
                        if class_grid[uc][k] != -1: blockers.add(class_grid[uc][k])
                        if teacher_grid[t][k] != -1: blockers.add(teacher_grid[t][k])
                        if len(blockers) > 1:
                            possible = False; break
                    
                    if possible:
                        if len(blockers) == 0:
                            candidates_moves.append(('FREE', s, t, -1))
                            break 
                        elif len(blockers) == 1:
                            candidates_moves.append(('SWAP', s, t, list(blockers)[0]))
            
            if not candidates_moves: continue
            
            move = random.choice(candidates_moves)
            move_type, new_s, new_t, victim_tid = move
            
            if move_type == 'FREE':
                delta_score = -1000000 + new_s
            elif move_type == 'SWAP':
                v_start = assigned[victim_tid][0]
                delta_score = new_s - v_start 
                
        elif mode == "OPTIMIZE":
            if not assigned: continue
            u_tid = random.choice(list(assigned.keys()))
            u_task = next(t for t in tasks if t['id'] == u_tid)
            old_s, old_t = assigned[u_tid]
            
            candidates_moves = []
            u_teachers = u_task['eligible']
            if len(u_teachers) > 3: u_teachers = random.sample(u_teachers, 3)
            
            for t in u_teachers:
                slots = valid_starts_cache.get(u_task['d'], [])
                try_slots = random.sample(slots, min(len(slots), 10)) 
                for s in try_slots:
                    if s == old_s and t == old_t: continue
                    e = s + u_task['d'] - 1
                    conflict = False
                    for k in range(s, e + 1):
                        if (class_grid[u_task['c']][k] != -1 and class_grid[u_task['c']][k] != u_tid) or \
                           (teacher_grid[t][k] != -1 and teacher_grid[t][k] != u_tid):
                            conflict = True; break
                    if not conflict:
                        candidates_moves.append((s, t))
            
            if not candidates_moves: continue
            new_s, new_t = random.choice(candidates_moves)
            delta_score = new_s - old_s
            move_type = 'MOVE'

        # Metropolis
        accept = False
        if delta_score <= 0:
            accept = True 
        else:
            if random.random() < math.exp(-delta_score / T_curr):
                accept = True
        
        # Update
        if accept:
            if mode == "INSERT":
                if move_type == 'FREE':
                    assigned[u_tid] = (new_s, new_t)
                    for k in range(new_s, new_s + u_task['d']):
                        class_grid[u_task['c']][k] = u_tid
                        teacher_grid[new_t][k] = u_tid
                    unassigned.remove(u_tid)
                    current_score += delta_score
                elif move_type == 'SWAP':
                    v_task = next(t for t in tasks if t['id'] == victim_tid)
                    v_s, v_t = assigned[victim_tid]
                    for k in range(v_s, v_s + v_task['d']):
                        class_grid[v_task['c']][k] = -1
                        teacher_grid[v_t][k] = -1
                    del assigned[victim_tid]
                    unassigned.append(victim_tid)
                    
                    assigned[u_tid] = (new_s, new_t)
                    for k in range(new_s, new_s + u_task['d']):
                        class_grid[u_task['c']][k] = u_tid
                        teacher_grid[new_t][k] = u_tid
                    unassigned.remove(u_tid)
                    current_score += delta_score
            elif mode == "OPTIMIZE":
                u_task = next(t for t in tasks if t['id'] == u_tid)
                for k in range(old_s, old_s + u_task['d']):
                    class_grid[u_task['c']][k] = -1
                    teacher_grid[old_t][k] = -1
                assigned[u_tid] = (new_s, new_t)
                for k in range(new_s, new_s + u_task['d']):
                    class_grid[u_task['c']][k] = u_tid
                    teacher_grid[new_t][k] = u_tid
                current_score += delta_score

            if current_score < best_score:
                best_score = current_score
                best_assigned = assigned.copy()

        T_curr *= alpha
        if T_curr < 1.0: T_curr = 5000.0 

    # --- OUTPUT ---
    final_output = []
    for tid, (s, t) in best_assigned.items():
        task = next(tk for tk in tasks if tk['id'] == tid)
        final_output.append((task['c'] + 1, task['m'], s, t + 1))
    
    if input_content is None:
        print(len(final_output))
        final_output.sort(key=lambda x: (x[0], x[1]))
        for item in final_output:
            print(f"{item[0]} {item[1]} {item[2]} {item[3]}")
            
    # TRẢ VỀ KẾT QUẢ CHO BENCHMARK
    return len(final_output)

if __name__ == "__main__":
    solve()