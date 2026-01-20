import sys
import random
import time
from io import StringIO

# Import các hàm tiện ích từ utils.py
# Đảm bảo bạn đã có file utils.py cùng thư mục
try:
    from utils import load_and_preprocess, MAX_SLOTS
except ImportError:
    print("Lỗi: Không tìm thấy file 'utils.py'. Hãy tạo file utils.py trước.")
    sys.exit(1)

# --- CẤU HÌNH ---
TIME_LIMIT = 0.95       # Thời gian chạy tối đa (giây)
TABU_TENURE = 10        # Số vòng lặp cấm quay lại vị trí cũ
MAX_NEIGHBORS = 20      # Số lượng hàng xóm kiểm tra mỗi vòng

def solve(input_content=None):
    start_time_prog = time.time()
    
    # 1. GỌI TIỀN XỬ LÝ
    # Giả lập stdin nếu chạy từ benchmark runner
    if input_content:
        sys.stdin = StringIO(input_content)

    data = load_and_preprocess()
    if data is None: return 0

    # Bung dữ liệu
    T, N, tasks = data['T'], data['N'], data['tasks']
    valid_starts = data['valid_starts'] 

    # --- KHỞI TẠO LỜI GIẢI BAN ĐẦU (GREEDY) ---
    assigned = {}   # {tid: (start_slot, teacher_id)}
    unassigned = [] # [tid, tid, ...]
    
    # Grid để check conflict O(1)
    class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]

    # Greedy First-Fit dựa trên list đã sort heuristic
    for task in tasks:
        tid, c, d = task['id'], task['c'], task['d']
        placed = False
        candidates = task['eligible']
        
        for t in candidates:
            if placed: break
            possible_slots = valid_starts.get(d, [])
            for s in possible_slots:
                e = s + d - 1
                # Check conflict nhanh
                conflict = False
                for k in range(s, e + 1):
                    if class_grid[c][k] != -1 or teacher_grid[t][k] != -1:
                        conflict = True; break
                
                if not conflict:
                    assigned[tid] = (s, t)
                    for k in range(s, e + 1):
                        class_grid[c][k] = tid
                        teacher_grid[t][k] = tid
                    placed = True
                    break
        
        if not placed: unassigned.append(tid)

    # --- HÀM TÍNH ĐIỂM ---
    def calculate_score(n_unassigned, current_assigned):
        s_time = sum(v[0] for v in current_assigned.values())
        # Ưu tiên số 1: Xếp hết môn (phạt 1 triệu điểm/môn thiếu)
        # Ưu tiên số 2: Tổng giờ học nhỏ nhất (sớm nhất)
        return n_unassigned * 1_000_000 + s_time

    current_score = calculate_score(len(unassigned), assigned)
    best_assigned = assigned.copy()
    best_score = current_score

    # --- TABU SEARCH (ATTRIBUTE-BASED) ---
    # Key: (task_id, forbidden_slot) -> Value: Expiration Iteration
    # Ý nghĩa: Task_ID bị cấm chuyển đến Slot này.
    # Quy ước: Slot -1 đại diện cho trạng thái Unassigned.
    tabu_list = {} 
    iteration = 0

    while time.time() - start_time_prog < TIME_LIMIT:
        iteration += 1
        candidate_moves = []
        
        # --- 1. TẠO ỨNG VIÊN (NEIGHBORHOOD) ---
        
        # Chiến lược A: Cố gắng chèn (INSERT/SWAP) nếu còn môn chưa xếp
        if unassigned:
            sample_unassigned = unassigned if len(unassigned) < 5 else random.sample(unassigned, 5)
            for u_tid in sample_unassigned:
                u_task = next(t for t in tasks if t['id'] == u_tid)
                
                # Chọn ngẫu nhiên vài giáo viên và slot để thử
                teachers = u_task['eligible']
                if len(teachers) > 3: teachers = random.sample(teachers, 3)
                
                slots = valid_starts.get(u_task['d'], [])
                if len(slots) > 5: try_slots = random.sample(slots, 5)
                else: try_slots = slots
                
                for t in teachers:
                    for s in try_slots:
                        # Kiểm tra xem đụng độ ai tại đích đến s?
                        e = s + u_task['d'] - 1
                        victims = set()
                        possible = True
                        for k in range(s, e + 1):
                            if class_grid[u_task['c']][k] != -1: victims.add(class_grid[u_task['c']][k])
                            if teacher_grid[t][k] != -1: victims.add(teacher_grid[t][k])
                            if len(victims) > 1: # Chỉ đá tối đa 1 người
                                possible = False; break
                        
                        if possible:
                            if len(victims) == 0:
                                candidate_moves.append(('INSERT', u_tid, s, t, -1))
                            elif len(victims) == 1:
                                candidate_moves.append(('SWAP_IN', u_tid, s, t, list(victims)[0]))

        # Chiến lược B: Tối ưu hóa (MOVE) môn đã xếp
        if assigned:
            # Chỉ thử Move nếu đã xếp được kha khá hoặc random trúng
            if not unassigned or random.random() < 0.5:
                sample_assigned = random.sample(list(assigned.keys()), min(len(assigned), 5))
                for tid in sample_assigned:
                    curr_task = next(t for t in tasks if t['id'] == tid)
                    old_s, old_t = assigned[tid]
                    
                    slots = valid_starts.get(curr_task['d'], [])
                    if len(slots) > 5: try_slots = random.sample(slots, 5)
                    else: try_slots = slots
                    
                    for s in try_slots:
                        if s == old_s: continue
                        e = s + curr_task['d'] - 1
                        
                        # Move chỉ thực hiện nếu đích đến hoàn toàn trống (với người khác)
                        conflict = False
                        for k in range(s, e + 1):
                            # Conflict nếu ô đó có người, VÀ người đó không phải chính mình
                            c_occupied = class_grid[curr_task['c']][k]
                            t_occupied = teacher_grid[old_t][k]
                            
                            if (c_occupied != -1 and c_occupied != tid) or \
                               (t_occupied != -1 and t_occupied != tid):
                                conflict = True; break
                        
                        if not conflict:
                            candidate_moves.append(('MOVE', tid, s, old_t, -1))

        # --- 2. CHỌN NƯỚC ĐI TỐT NHẤT ---
        best_move = None
        best_move_score = float('inf')
        
        if len(candidate_moves) > MAX_NEIGHBORS:
            candidate_moves = random.sample(candidate_moves, MAX_NEIGHBORS)

        for move in candidate_moves:
            m_type, tid, new_s, new_t, victim = move
            
            # Tính điểm thay đổi (Delta)
            delta = 0
            if m_type == 'INSERT':
                delta = -1_000_000 + new_s
            elif m_type == 'SWAP_IN':
                v_start = assigned[victim][0]
                delta = new_s - v_start # new_s (thêm) - v_start (bớt)
            elif m_type == 'MOVE':
                old_s = assigned[tid][0]
                delta = new_s - old_s
            
            temp_score = current_score + delta
            
            # --- LOGIC TABU MỚI (Attribute-based) ---
            is_tabu = False
            
            # 1. Kiểm tra Task chính (tid) có bị cấm đến new_s không?
            if (tid, new_s) in tabu_list and tabu_list[(tid, new_s)] > iteration:
                is_tabu = True
                
            # 2. Kiểm tra Victim (nếu có) có bị cấm quay về Unassigned (-1) không?
            if victim != -1:
                if (victim, -1) in tabu_list and tabu_list[(victim, -1)] > iteration:
                    is_tabu = True
            
            # Aspiration Criteria (Phá băng)
            if is_tabu and temp_score < best_score:
                is_tabu = False
            
            if not is_tabu:
                if temp_score < best_move_score:
                    best_move_score = temp_score
                    best_move = move

        # --- 3. THỰC HIỆN NƯỚC ĐI ---
        if best_move:
            m_type, tid, new_s, new_t, victim = best_move
            curr_task = next(t for t in tasks if t['id'] == tid)
            
            # Lấy vị trí cũ để ghi vào Tabu list
            old_s = -1
            if tid in assigned: old_s = assigned[tid][0]

            if m_type == 'INSERT':
                assigned[tid] = (new_s, new_t)
                unassigned.remove(tid)
                for k in range(new_s, new_s + curr_task['d']):
                    class_grid[curr_task['c']][k] = tid
                    teacher_grid[new_t][k] = tid
                
                # Tabu: Cấm tid quay lại Unassigned (-1)
                tabu_list[(tid, -1)] = iteration + TABU_TENURE
                
            elif m_type == 'SWAP_IN':
                # Gỡ Victim
                v_task = next(t for t in tasks if t['id'] == victim)
                v_s, v_t = assigned[victim]
                for k in range(v_s, v_s + v_task['d']):
                    class_grid[v_task['c']][k] = -1
                    teacher_grid[v_t][k] = -1
                del assigned[victim]
                unassigned.append(victim)
                
                # Tabu Victim: Cấm victim quay lại vị trí nó vừa bị đá (v_s)
                tabu_list[(victim, v_s)] = iteration + TABU_TENURE
                
                # Chèn Tid
                assigned[tid] = (new_s, new_t)
                unassigned.remove(tid)
                for k in range(new_s, new_s + curr_task['d']):
                    class_grid[curr_task['c']][k] = tid
                    teacher_grid[new_t][k] = tid
                
                # Tabu Tid: Cấm tid quay lại Unassigned
                tabu_list[(tid, -1)] = iteration + TABU_TENURE
                
            elif m_type == 'MOVE':
                old_s_move, _ = assigned[tid] # old_s ở đây là vị trí thực trước khi move
                # Xóa cũ
                for k in range(old_s_move, old_s_move + curr_task['d']):
                    class_grid[curr_task['c']][k] = -1
                    teacher_grid[new_t][k] = -1 
                # Thêm mới
                assigned[tid] = (new_s, new_t)
                for k in range(new_s, new_s + curr_task['d']):
                    class_grid[curr_task['c']][k] = tid
                    teacher_grid[new_t][k] = tid
                
                # Tabu: Cấm tid quay lại vị trí cũ (old_s_move)
                tabu_list[(tid, old_s_move)] = iteration + TABU_TENURE

            current_score = best_move_score
            if current_score < best_score:
                best_score = current_score
                best_assigned = assigned.copy()
            
            # Dọn dẹp Tabu List (Optional: để tránh dictionary quá lớn)
            if iteration % 100 == 0:
                 tabu_list = {k: v for k, v in tabu_list.items() if v > iteration}

    # --- OUTPUT ---
    final_output = []
    for tid, (s, t) in best_assigned.items():
        task = next(tk for tk in tasks if tk['id'] == tid)
        # Chuyển đổi ID về 1-based index
        final_output.append((task['c'] + 1, task['m'], s, t + 1))
    
    # Nếu chạy trực tiếp (không qua benchmark runner), in ra stdout
    if input_content is None:
        print(len(final_output))
        final_output.sort(key=lambda x: (x[0], x[1]))
        for item in final_output:
            print(f"{item[0]} {item[1]} {item[2]} {item[3]}")
    
    return len(final_output)

if __name__ == "__main__":
    solve()