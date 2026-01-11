import sys
import math
import random
import time

# --- CẤU HÌNH ---
SLOTS_PER_SESSION = 6
SESSIONS_PER_DAY = 2
DAYS = 5
MAX_SLOTS = DAYS * SESSIONS_PER_DAY * SLOTS_PER_SESSION # 60 tiết
TIME_LIMIT = 0.95 # Giới hạn thời gian (quan trọng)

# --- HÀM HỖ TRỢ ---
def input_stream():
    try:
        full_input = sys.stdin.read().split()
    except Exception: return
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

def solve_smart_sa():
    start_time_prog = time.time()
    
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
                'd': durations[m_id - 1], 'eligible': eligible
            })
            task_counter += 1

    # HEURISTIC SORT (Rất quan trọng cho trạng thái ban đầu)
    tasks.sort(key=lambda x: (len(x['eligible']), -x['d'], x['c']))
    teacher_degrees = [len(s) for s in teacher_abilities]

    # --- KHỞI TẠO GREEDY ---
    assigned = {} # id -> (s, t)
    class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]
    unassigned = [] # List ID

    # Caching valid starts (Tăng tốc độ)
    valid_starts_cache = {}
    for d in range(1, 13):
        valid_starts_cache[d] = [s for s in range(1, MAX_SLOTS - d + 2) if is_valid_session(s, d)]

    # Greedy Construct
    for task in tasks:
        tid, c, d = task['id'], task['c'], task['d']
        cands = sorted(task['eligible'], key=lambda t: (teacher_degrees[t], t))
        is_set = False
        for t in cands:
            if is_set: break
            for s in range(1, MAX_SLOTS - d + 2):
                if not is_valid_session(s, d): continue
                # Conflict check
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

    # Hàm mục tiêu
    def get_score(n_unassigned, sum_start):
        # Ưu tiên tối đa là giảm unassigned (trọng số cực lớn)
        # Sau đó mới đến giảm thời gian
        return n_unassigned * 1000000 + sum_start

    current_score = get_score(len(unassigned), sum(v[0] for v in assigned.values()))
    best_assigned = assigned.copy()
    best_score = current_score

    # --- SA LOOP ---
    T_curr = 200.0 # Nhiệt độ bắt đầu không cần quá cao vì Greedy đã tốt
    alpha = 0.99   # Làm lạnh từ từ

    iter_count = 0
    
    while time.time() - start_time_prog < TIME_LIMIT:
        iter_count += 1
        
        # CHIẾN LƯỢC CHỌN NƯỚC ĐI (SMART NEIGHBORHOOD)
        # Nếu còn task chưa xếp, tập trung 100% vào việc nhét nó vào
        mode = "INSERT" if unassigned else "OPTIMIZE"
        
        move_type = None
        u_tid = -1
        victim_tid = -1
        new_s, new_t = -1, -1
        old_s, old_t = -1, -1
        
        if mode == "INSERT":
            # Chọn 1 task chưa xếp
            u_tid = random.choice(unassigned)
            u_task = next(t for t in tasks if t['id'] == u_tid)
            uc, ud = u_task['c'], u_task['d']
            
            # Thay vì random mù quáng, hãy tìm các slot "tiềm năng"
            # Tiềm năng = Trống HOẶC chỉ bị chắn bởi 1 task khác
            candidates_moves = []
            
            # Thử random 5 giáo viên (hoặc tất cả nếu ít) để đỡ tốn thời gian
            u_teachers = u_task['eligible']
            if len(u_teachers) > 5: u_teachers = random.sample(u_teachers, 5)
            
            for t in u_teachers:
                # Quét các slot hợp lệ
                for s in valid_starts_cache.get(ud, []):
                    e = s + ud - 1
                    
                    # Đếm vật cản
                    blockers = set()
                    possible = True
                    for k in range(s, e + 1):
                        if class_grid[uc][k] != -1: blockers.add(class_grid[uc][k])
                        if teacher_grid[t][k] != -1: blockers.add(teacher_grid[t][k])
                        if len(blockers) > 1: # Chỉ chấp nhận tối đa 1 vật cản để Swap
                            possible = False; break
                    
                    if possible:
                        if len(blockers) == 0:
                            candidates_moves.append(('FREE', s, t, -1))
                            # Nếu gặp slot trống, break luôn để ưu tiên
                            break 
                        elif len(blockers) == 1:
                            candidates_moves.append(('SWAP', s, t, list(blockers)[0]))
            
            if not candidates_moves:
                continue # Không tìm thấy nước đi nào khả thi cho task này, thử task khác
            
            # Chọn 1 nước đi từ danh sách gợi ý
            move = random.choice(candidates_moves)
            move_type, new_s, new_t, victim_tid = move
            
            # Thực hiện nước đi giả định
            delta_score = 0
            
            if move_type == 'FREE':
                # Chèn vào chỗ trống -> Score giảm cực mạnh (-1 unassigned)
                delta_score = -1000000 + new_s
            elif move_type == 'SWAP':
                # Đá victim ra -> Số lượng unassigned không đổi (1 vào 1 ra)
                # Score thay đổi dựa trên start time (new_s) và mất đi start time của victim
                v_start = assigned[victim_tid][0]
                delta_score = new_s - v_start 
                
        elif mode == "OPTIMIZE":
            # Chọn 1 task đã xếp để di chuyển sang chỗ tốt hơn (Compaction)
            u_tid = random.choice(list(assigned.keys()))
            u_task = next(t for t in tasks if t['id'] == u_tid)
            old_s, old_t = assigned[u_tid]
            
            # Tìm chỗ mới trống hoàn toàn và sớm hơn
            candidates_moves = []
            u_teachers = u_task['eligible']
            if len(u_teachers) > 3: u_teachers = random.sample(u_teachers, 3)
            
            for t in u_teachers:
                # Chỉ tìm các slot sớm hơn slot hiện tại (hoặc random gần đó)
                for s in valid_starts_cache.get(u_task['d'], []):
                    if s >= old_s and t == old_t: continue # Không chuyển về chỗ cũ hoặc muộn hơn
                    
                    # Check conflict
                    e = s + u_task['d'] - 1
                    # Cần check kỹ vì ta chưa gỡ task ra khỏi grid
                    conflict = False
                    for k in range(s, e + 1):
                        # Nếu ô đó đang bị chiếm bởi task khác (ko phải chính mình)
                        if (class_grid[u_task['c']][k] != -1 and class_grid[u_task['c']][k] != u_tid) or \
                           (teacher_grid[t][k] != -1 and teacher_grid[t][k] != u_tid):
                            conflict = True; break
                    if not conflict:
                        candidates_moves.append((s, t))
                        if s < old_s: break # Tìm thấy chỗ sớm hơn là lấy ngay
            
            if not candidates_moves: continue
            
            new_s, new_t = random.choice(candidates_moves)
            delta_score = new_s - old_s
            move_type = 'MOVE'

        # --- METROPOLIS ACCEPTANCE ---
        # Delta < 0: Tốt hơn -> Chọn
        # Delta > 0: Tệ hơn -> Chọn với xác suất
        # Với mode INSERT SWAP: Delta thường ~ 0 (vì unassigned không đổi), SA dễ dàng chấp nhận để đảo trộn
        
        accept = False
        if delta_score <= 0:
            accept = True
        else:
            if random.random() < math.exp(-delta_score / T_curr):
                accept = True
        
        # --- UPDATE STATE ---
        if accept:
            if mode == "INSERT":
                if move_type == 'FREE':
                    # Assign U
                    assigned[u_tid] = (new_s, new_t)
                    for k in range(new_s, new_s + u_task['d']):
                        class_grid[u_task['c']][k] = u_tid
                        teacher_grid[new_t][k] = u_tid
                    unassigned.remove(u_tid)
                    current_score += delta_score
                    
                elif move_type == 'SWAP':
                    # Remove Victim
                    v_task = next(t for t in tasks if t['id'] == victim_tid)
                    v_s, v_t = assigned[victim_tid]
                    for k in range(v_s, v_s + v_task['d']):
                        class_grid[v_task['c']][k] = -1
                        teacher_grid[v_t][k] = -1
                    del assigned[victim_tid]
                    unassigned.append(victim_tid)
                    
                    # Assign U
                    assigned[u_tid] = (new_s, new_t)
                    for k in range(new_s, new_s + u_task['d']):
                        class_grid[u_task['c']][k] = u_tid
                        teacher_grid[new_t][k] = u_tid
                    unassigned.remove(u_tid)
                    
                    current_score += delta_score
            
            elif mode == "OPTIMIZE":
                # Remove Old
                u_task = next(t for t in tasks if t['id'] == u_tid)
                for k in range(old_s, old_s + u_task['d']):
                    class_grid[u_task['c']][k] = -1
                    teacher_grid[old_t][k] = -1
                
                # Add New
                assigned[u_tid] = (new_s, new_t)
                for k in range(new_s, new_s + u_task['d']):
                    class_grid[u_task['c']][k] = u_tid
                    teacher_grid[new_t][k] = u_tid
                
                current_score += delta_score

            # Update Global Best
            if current_score < best_score:
                best_score = current_score
                best_assigned = assigned.copy()

        # Cooling
        T_curr *= alpha
        # Reheat nếu kẹt (Optional)
        if T_curr < 0.5: T_curr = 200.0

    # --- OUTPUT ---
    # In kết quả từ best_assigned
    final_output = []
    for tid, (s, t) in best_assigned.items():
        task = next(tk for tk in tasks if tk['id'] == tid)
        final_output.append((task['c'] + 1, task['m'], s, t + 1))
    
    print(len(final_output))
    final_output.sort(key=lambda x: (x[0], x[1]))
    for item in final_output:
        print(f"{item[0]} {item[1]} {item[2]} {item[3]}")

if __name__ == "__main__":
    solve_smart_sa()