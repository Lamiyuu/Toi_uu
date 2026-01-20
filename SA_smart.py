import sys
import math
import random
import time
from utils import load_and_preprocess, MAX_SLOTS

# --- CẤU HÌNH SA ---
TIME_LIMIT = 0.95
T_START = 5000.0
ALPHA = 0.98

def solve_sa_random_init(input_content=None):
    start_time_prog = time.time()
    
    # 1. GỌI TIỀN XỬ LÝ
    # Giả lập stdin nếu có input string (dùng cho benchmark runner)
    if input_content:
        from io import StringIO
        sys.stdin = StringIO(input_content)

    data = load_and_preprocess()
    if data is None: return

    # Bung dữ liệu ra các biến
    T, N, tasks = data['T'], data['N'], data['tasks']
    # valid_starts chính là valid_starts_cache trong code cũ
    valid_starts_cache = data['valid_starts'] 

    # --- KHỞI TẠO CẤU TRÚC DỮ LIỆU ---
    assigned = {} # Map: task_id -> (start_slot, teacher_index)
    
    # Grid để check va chạm nhanh: -1 là trống, >=0 là ID task đang chiếm
    class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]
    
    unassigned = [] # Danh sách id các task chưa xếp được

    # --- RANDOM CONSTRUCT ---
    # Xếp lịch khởi tạo ngẫu nhiên nhưng sử dụng cache slot hợp lệ
    for task in tasks:
        tid, c, d = task['id'], task['c'], task['d']
        
        # 1. Xáo trộn danh sách giáo viên
        candidates = list(task['eligible'])
        random.shuffle(candidates)
        
        is_set = False
        
        for t in candidates:
            if is_set: break
            
            # 2. Lấy slot từ Cache (Nhanh hơn tính thủ công)
            possible_slots = list(valid_starts_cache.get(d, []))
            random.shuffle(possible_slots) # Random hóa vị trí
            
            for s in possible_slots:
                e = s + d - 1
                
                # Check conflict
                ok = True
                for k in range(s, e + 1):
                    if class_grid[c][k] != -1 or teacher_grid[t][k] != -1:
                        ok = False; break
                
                if ok:
                    # Assign
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
        # Ưu tiên 1: Giảm unassigned
        # Ưu tiên 2: Giảm tổng thời gian bắt đầu (compact schedule)
        return n_unassigned * 1_000_000 + sum_start

    current_score = get_score(len(unassigned), sum(v[0] for v in assigned.values()))
    best_assigned = assigned.copy()
    best_score = current_score

    # --- SIMULATED ANNEALING LOOP ---
    T_curr = T_START
    
    while time.time() - start_time_prog < TIME_LIMIT:
        
        # Chọn chế độ: Nếu còn task chưa xếp thì ưu tiên chèn (INSERT), nếu hết thì tối ưu (OPTIMIZE)
        mode = "INSERT" if unassigned else "OPTIMIZE"
        
        move_type = None
        u_tid = -1
        victim_tid = -1
        new_s, new_t = -1, -1
        old_s, old_t = -1, -1
        delta_score = 0
        
        # --- TẠO NƯỚC ĐI (NEIGHBORHOOD MOVE) ---
        if mode == "INSERT":
            # [Logic cũ giữ nguyên] Cố gắng chèn task chưa xếp vào
            u_tid = random.choice(unassigned)
            u_task = next(t for t in tasks if t['id'] == u_tid)
            uc, ud = u_task['c'], u_task['d']
            
            candidates_moves = []
            u_teachers = u_task['eligible']
            if len(u_teachers) > 5: u_teachers = random.sample(u_teachers, 5)
            
            for t in u_teachers:
                # Dùng cache slot hợp lệ
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
                            break # Ưu tiên slot trống tìm thấy ngay
                        elif len(blockers) == 1:
                            candidates_moves.append(('SWAP', s, t, list(blockers)[0]))
            
            if not candidates_moves: continue
            
            move = random.choice(candidates_moves)
            move_type, new_s, new_t, victim_tid = move
            
            if move_type == 'FREE':
                delta_score = -1_000_000 + new_s
            elif move_type == 'SWAP':
                v_start = assigned[victim_tid][0]
                delta_score = new_s - v_start 
                
        elif mode == "OPTIMIZE":
            # [Logic cũ giữ nguyên] Di chuyển task đã xếp
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

        # --- QUYẾT ĐỊNH CHẤP NHẬN (METROPOLIS CRITERION) ---
        accept = False
        if delta_score <= 0:
            accept = True
        else:
            if random.random() < math.exp(-delta_score / T_curr):
                accept = True
        
        # --- CẬP NHẬT TRẠNG THÁI ---
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
                    # Gỡ nạn nhân
                    v_task = next(t for t in tasks if t['id'] == victim_tid)
                    v_s, v_t = assigned[victim_tid]
                    for k in range(v_s, v_s + v_task['d']):
                        class_grid[v_task['c']][k] = -1
                        teacher_grid[v_t][k] = -1
                    del assigned[victim_tid]
                    unassigned.append(victim_tid)
                    
                    # Chèn người mới
                    assigned[u_tid] = (new_s, new_t)
                    for k in range(new_s, new_s + u_task['d']):
                        class_grid[u_task['c']][k] = u_tid
                        teacher_grid[new_t][k] = u_tid
                    unassigned.remove(u_tid)
                    current_score += delta_score
            
            elif mode == "OPTIMIZE":
                u_task = next(t for t in tasks if t['id'] == u_tid)
                # Xóa cũ
                for k in range(old_s, old_s + u_task['d']):
                    class_grid[u_task['c']][k] = -1
                    teacher_grid[old_t][k] = -1
                # Thêm mới
                assigned[u_tid] = (new_s, new_t)
                for k in range(new_s, new_s + u_task['d']):
                    class_grid[u_task['c']][k] = u_tid
                    teacher_grid[new_t][k] = u_tid
                current_score += delta_score

            # Lưu kỷ lục
            if current_score < best_score:
                best_score = current_score
                best_assigned = assigned.copy()

        # Giảm nhiệt độ
        T_curr *= ALPHA
        if T_curr < 1.0: T_curr = T_START 

    # --- OUTPUT ---
    final_output = []
    for tid, (s, t) in best_assigned.items():
        task = next(tk for tk in tasks if tk['id'] == tid)
        # Cộng 1 cho đúng format đề bài (Index từ 1)
        # Lưu ý: trong utils, c và t (eligible) là 0-based.
        final_output.append((task['c'] + 1, task['m'], s, t + 1))
    
    if input_content is None:
        print(len(final_output))
        final_output.sort(key=lambda x: (x[0], x[1]))
        for item in final_output:
            print(f"{item[0]} {item[1]} {item[2]} {item[3]}")
    
    return len(final_output)

if __name__ == "__main__":
    solve_sa_random_init()