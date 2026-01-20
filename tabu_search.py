import sys
import random
import time
# Nạp các hàm tiện ích từ file utils.py
from utils import load_and_preprocess, MAX_SLOTS

# --- CẤU HÌNH ---
TIME_LIMIT = 0.95
TABU_TENURE = 10   # Số vòng lặp một task bị cấm sau khi di chuyển
MAX_NEIGHBORS = 20 # Giới hạn số lượng hàng xóm kiểm tra mỗi vòng (để chạy nhanh)

def solve(input_content=None):
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
    # valid_starts chính là cache các slot hợp lệ đã tính trước
    valid_starts = data['valid_starts'] 

    # --- KHỞI TẠO LỜI GIẢI BAN ĐẦU (GREEDY) ---
    # Sử dụng danh sách tasks đã được sort heuristic từ utils
    assigned = {} 
    class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]
    unassigned = []

    for task in tasks:
        tid, c, d = task['id'], task['c'], task['d']
        placed = False
        
        # Chọn GV (candidates đã được sort heuristic hoặc lấy từ utils)
        candidates = task['eligible']
        
        for t in candidates:
            if placed: break
            
            # LẤY SLOT TỪ CACHE (TỐI ƯU HÓA)
            possible_slots = valid_starts.get(d, [])
            
            for s in possible_slots:
                e = s + d - 1
                
                # Check Conflict
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

    # --- HÀM TÍNH ĐIỂM NHANH ---
    def calculate_score(n_unassigned, current_assigned):
        s_time = sum(v[0] for v in current_assigned.values())
        return n_unassigned * 1_000_000 + s_time

    current_score = calculate_score(len(unassigned), assigned)
    best_assigned = assigned.copy()
    best_score = current_score

    # --- TABU SEARCH ---
    # Tabu List: {task_id: expiration_iteration}
    tabu_list = {} 
    iteration = 0

    while time.time() - start_time_prog < TIME_LIMIT:
        iteration += 1
        
        # Tạo danh sách các nước đi ứng viên (Neighborhood)
        candidate_moves = []
        
        # CHIẾN LƯỢC 1: CỐ GẮNG CHÈN (Nếu còn unassigned)
        if unassigned:
            # Lấy mẫu ngẫu nhiên để không duyệt quá lâu
            sample_unassigned = unassigned if len(unassigned) < 5 else random.sample(unassigned, 5)
            
            for u_tid in sample_unassigned:
                u_task = next(t for t in tasks if t['id'] == u_tid)
                
                # Thử các giáo viên
                teachers = u_task['eligible']
                if len(teachers) > 3: teachers = random.sample(teachers, 3)
                
                for t in teachers:
                    # Lấy slot từ cache
                    slots = valid_starts.get(u_task['d'], [])
                    if len(slots) > 5: try_slots = random.sample(slots, 5)
                    else: try_slots = slots
                    
                    for s in try_slots:
                        # Kiểm tra va chạm & tìm nạn nhân
                        e = s + u_task['d'] - 1
                        victims = set()
                        possible = True
                        for k in range(s, e + 1):
                            if class_grid[u_task['c']][k] != -1: victims.add(class_grid[u_task['c']][k])
                            if teacher_grid[t][k] != -1: victims.add(teacher_grid[t][k])
                            if len(victims) > 1: # Chỉ cho phép đá tối đa 1 người
                                possible = False; break
                        
                        if possible:
                            if len(victims) == 0:
                                candidate_moves.append(('INSERT', u_tid, s, t, -1))
                            elif len(victims) == 1:
                                candidate_moves.append(('SWAP_IN', u_tid, s, t, list(victims)[0]))

        # CHIẾN LƯỢC 2: TỐI ƯU HÓA (Di chuyển task đã xếp)
        # Chỉ chạy khi đã xếp được tương đối hoặc hết unassigned
        if assigned:
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
                    
                    conflict = False
                    for k in range(s, e + 1):
                        # Chỉ check conflict với NGƯỜI KHÁC
                        if (class_grid[curr_task['c']][k] != -1 and class_grid[curr_task['c']][k] != tid) or \
                           (teacher_grid[old_t][k] != -1 and teacher_grid[old_t][k] != tid):
                            conflict = True; break
                    
                    if not conflict:
                        candidate_moves.append(('MOVE', tid, s, old_t, -1))

        # --- CHỌN NƯỚC ĐI TỐT NHẤT (Best Non-Tabu) ---
        best_move = None
        best_move_score = float('inf')
        
        # Chỉ xét một số lượng moves nhất định để đảm bảo tốc độ
        if len(candidate_moves) > MAX_NEIGHBORS:
            candidate_moves = random.sample(candidate_moves, MAX_NEIGHBORS)

        for move in candidate_moves:
            m_type, tid, new_s, new_t, victim = move
            
            # Tính điểm Delta
            delta = 0
            if m_type == 'INSERT':
                delta = -1_000_000 + new_s
            elif m_type == 'SWAP_IN':
                v_start = assigned[victim][0]
                delta = new_s - v_start 
            elif m_type == 'MOVE':
                old_s = assigned[tid][0]
                delta = new_s - old_s
            
            temp_score = current_score + delta
            
            # Check Tabu
            is_tabu = False
            if tid in tabu_list and tabu_list[tid] > iteration: is_tabu = True
            if victim != -1 and victim in tabu_list and tabu_list[victim] > iteration: is_tabu = True
            
            # Aspiration Criteria (Phá băng Tabu nếu tìm được kỷ lục mới)
            if is_tabu and temp_score < best_score:
                is_tabu = False
            
            if not is_tabu:
                if temp_score < best_move_score:
                    best_move_score = temp_score
                    best_move = move

        # --- THỰC HIỆN NƯỚC ĐI ---
        if best_move:
            m_type, tid, new_s, new_t, victim = best_move
            curr_task = next(t for t in tasks if t['id'] == tid)
            
            if m_type == 'INSERT':
                assigned[tid] = (new_s, new_t)
                unassigned.remove(tid)
                for k in range(new_s, new_s + curr_task['d']):
                    class_grid[curr_task['c']][k] = tid
                    teacher_grid[new_t][k] = tid
                # Gán Tabu
                tabu_list[tid] = iteration + TABU_TENURE
                
            elif m_type == 'SWAP_IN':
                # Gỡ victim
                v_task = next(t for t in tasks if t['id'] == victim)
                v_s, v_t = assigned[victim]
                for k in range(v_s, v_s + v_task['d']):
                    class_grid[v_task['c']][k] = -1
                    teacher_grid[v_t][k] = -1
                del assigned[victim]
                unassigned.append(victim)
                tabu_list[victim] = iteration + TABU_TENURE # Victim bị đá ra, cấm quay lại ngay
                
                # Chèn U
                assigned[tid] = (new_s, new_t)
                unassigned.remove(tid)
                for k in range(new_s, new_s + curr_task['d']):
                    class_grid[curr_task['c']][k] = tid
                    teacher_grid[new_t][k] = tid
                tabu_list[tid] = iteration + TABU_TENURE
                
            elif m_type == 'MOVE':
                old_s, _ = assigned[tid]
                # Xóa cũ
                for k in range(old_s, old_s + curr_task['d']):
                    class_grid[curr_task['c']][k] = -1
                    teacher_grid[new_t][k] = -1 
                # Thêm mới
                assigned[tid] = (new_s, new_t)
                for k in range(new_s, new_s + curr_task['d']):
                    class_grid[curr_task['c']][k] = tid
                    teacher_grid[new_t][k] = tid
                tabu_list[tid] = iteration + TABU_TENURE

            current_score = best_move_score
            if current_score < best_score:
                best_score = current_score
                best_assigned = assigned.copy()

    # --- OUTPUT ---
    final_output = []
    for tid, (s, t) in best_assigned.items():
        task = next(tk for tk in tasks if tk['id'] == tid)
        # Chuyển đổi ID về 1-based index theo format đề bài
        final_output.append((task['c'] + 1, task['m'], s, t + 1))
    
    if input_content is None:
        print(len(final_output))
        final_output.sort(key=lambda x: (x[0], x[1]))
        for item in final_output:
            print(f"{item[0]} {item[1]} {item[2]} {item[3]}")
    
    return len(final_output)

if __name__ == "__main__":
    solve()