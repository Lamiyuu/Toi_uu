import sys
import random
import time
from collections import defaultdict

# ============================================
# CONFIGURATION
# ============================================
DEFAULT_TIME_LIMIT = 0.95
MAX_SLOTS = 60  # 5 days x 2 sessions x 6 periods
BASE_TABU_TENURE = 8
MIN_TENURE = 3
MAX_TENURE = 15

# Thresholds
INTENSIFICATION_THRESHOLD = 10
DIVERSIFICATION_THRESHOLD = 30
RESTART_THRESHOLD = 80
ELITE_POOL_SIZE = 5

# ============================================
# MEMORY STRUCTURES
# ============================================
class MultiLevelMemory:
    def __init__(self):
        self.tabu_list = {}
        self.move_frequency = defaultdict(int)
        self.region_frequency = defaultdict(int)
        self.elite_solutions = []
        
        self.iteration = 0
        self.last_improvement_iter = 0
        self.stagnation_count = 0
        self.consecutive_improvements = 0
        
    def is_stagnating(self):
        return self.stagnation_count > DIVERSIFICATION_THRESHOLD
    
    def need_restart(self):
        return self.stagnation_count > RESTART_THRESHOLD
    
    def is_intensifying(self):
        return self.consecutive_improvements > INTENSIFICATION_THRESHOLD
    
    def add_elite(self, score, assigned):
        sol_copy = assigned.copy()
        self.elite_solutions.append((score, sol_copy))
        self.elite_solutions.sort(key=lambda x: x[0]) # Sort theo score (duration âm -> càng nhỏ càng tốt)
        if len(self.elite_solutions) > ELITE_POOL_SIZE:
            self.elite_solutions.pop() # Bỏ cái tệ nhất (lớn nhất)
    
    def get_random_elite(self):
        if not self.elite_solutions:
            return None
        return random.choice(self.elite_solutions)[1]

# ============================================
# INPUT PROCESSING
# ============================================
def load_and_preprocess():
    try:
        # Đọc line đầu tiên kiểm tra xem có dữ liệu không
        first_line = sys.stdin.readline()
        if not first_line: return None
        
        line = first_line.strip().split()
        if not line: return None
        
        T, N, M = int(line[0]), int(line[1]), int(line[2])
        
        # Đọc danh sách môn của từng lớp
        class_subjects = []
        for i in range(N):
            line_data = list(map(int, sys.stdin.readline().split()))
            subjects = [s for s in line_data if s != 0]
            class_subjects.append(subjects)
        
        # Đọc danh sách môn giáo viên có thể dạy
        teacher_subjects = []
        for t in range(T):
            line_data = list(map(int, sys.stdin.readline().split()))
            subjects = [s for s in line_data if s != 0]
            teacher_subjects.append(subjects)
        
        # Đọc số tiết của từng môn
        durations_line = list(map(int, sys.stdin.readline().split()))
        durations = [0] + durations_line  # Index 1-based
        
        # Tạo tasks (lớp-môn)
        tasks = []
        task_id = 0
        for c in range(N):
            for m in class_subjects[c]:
                # Tìm giáo viên có thể dạy môn m
                eligible = []
                for t in range(T):
                    if m in teacher_subjects[t]:
                        eligible.append(t)
                
                if eligible:  # Chỉ tạo task nếu có giáo viên
                    tasks.append({
                        'id': task_id,
                        'c': c,      # Class index (0-based)
                        'm': m,      # Subject (1-based)
                        'd': durations[m],
                        'eligible': eligible
                    })
                    task_id += 1
        
        # Tính valid starts cho mỗi duration
        valid_starts = {}
        for d in range(1, 7):  # Duration từ 1-6
            valid_starts[d] = []
            # Trong mỗi buổi (6 tiết)
            for session_start in range(0, MAX_SLOTS, 6):
                for start in range(session_start, session_start + 6):
                    if start + d - 1 < session_start + 6:
                        valid_starts[d].append(start)
        
        return {
            'T': T, 'N': N, 'M': M,
            'tasks': tasks,
            'valid_starts': valid_starts
        }
    except Exception as e:
        # print(f"Error parsing input: {e}")
        return None

# ============================================
# TABU UTILITIES
# ============================================
def make_tabu_key(tid, slot, teacher):
    return (tid, slot, teacher)

def adaptive_tenure(memory):
    base = BASE_TABU_TENURE
    if memory.is_intensifying():
        return max(MIN_TENURE, base - 3)
    if memory.is_stagnating():
        return min(MAX_TENURE, base + 5)
    return base + random.randint(-2, 2)

def is_move_tabu(move, current_score, best_score, memory):
    tid, ns, nt = move['tid'], move['ns'], move['nt']
    key = make_tabu_key(tid, ns, nt)
    
    # Aspiration (Nếu move giúp đạt kỷ lục mới -> Phá Tabu)
    if current_score + move['delta'] < best_score:
        return False
        
    # Nếu tabu chưa hết hạn
    if key in memory.tabu_list and memory.tabu_list[key] > memory.iteration:
        return True
    
    return False

def calculate_move_penalty(move, memory):
    tid, ns, nt = move['tid'], move['ns'], move['nt']
    key = make_tabu_key(tid, ns, nt)
    
    freq_penalty = memory.move_frequency[key] * 80
    
    slot_bucket = ns // 30
    region_key = (slot_bucket, nt)
    region_penalty = memory.region_frequency[region_key] * 30
    
    diversify_bonus = 0
    if memory.is_stagnating() and memory.move_frequency[key] < 2:
        diversify_bonus = -200
    
    return freq_penalty + region_penalty + diversify_bonus

# ============================================
# DIVERSIFICATION
# ============================================
def perturb_solution(assigned, tasks, class_grid, teacher_grid, valid_starts, N, T, strength=0.2):
    task_ids = list(assigned.keys())
    if not task_ids:
        return assigned
    
    n_perturb = max(1, int(len(task_ids) * strength))
    to_perturb = random.sample(task_ids, min(n_perturb, len(task_ids)))
    
    # Remove
    for tid in to_perturb:
        task = next(t for t in tasks if t['id'] == tid)
        old_s, old_t = assigned[tid]
        for k in range(old_s, old_s + task['d']):
            class_grid[task['c']][k] = -1
            teacher_grid[old_t][k] = -1
        del assigned[tid]
    
    # Re-insert (Random Greedy)
    for tid in to_perturb:
        task = next(t for t in tasks if t['id'] == tid)
        placed = False
        
        teachers = task['eligible'][:5] if len(task['eligible']) > 5 else task['eligible']
        random.shuffle(teachers)
        
        for t in teachers:
            if placed: break
            slots = valid_starts.get(task['d'], [])
            random.shuffle(slots)
            for s in slots[:10]:
                e = s + task['d'] - 1
                conflict = False
                for k in range(s, e + 1):
                    if class_grid[task['c']][k] != -1 or teacher_grid[t][k] != -1:
                        conflict = True
                        break
                if not conflict:
                    assigned[tid] = (s, t)
                    for k in range(s, e + 1):
                        class_grid[task['c']][k] = tid
                        teacher_grid[t][k] = tid
                    placed = True
                    break
    
    return assigned

# ============================================
# MAIN SOLVER
# ============================================
def solve(input_content=None, time_limit=None):
    """
    Hàm giải Tabu Search có hỗ trợ time_limit.
    """
    start_time_prog = time.time()
    
    # XÁC ĐỊNH LIMIT
    limit = time_limit if time_limit is not None else DEFAULT_TIME_LIMIT

    if input_content:
        from io import StringIO
        sys.stdin = StringIO(input_content)

    data = load_and_preprocess()
    if data is None:
        return 0

    T, N = data['T'], data['N']
    tasks = data['tasks']
    valid_starts = data['valid_starts']
    
    memory = MultiLevelMemory()

    # === GREEDY INITIALIZATION ===
    assigned = {}
    class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]
    unassigned = []
    
    # Sort tasks khó xếp lên trước
    tasks.sort(key=lambda x: (len(x['eligible']), -x['d']))
    
    for task in tasks:
        tid, c, d = task['id'], task['c'], task['d']
        placed = False
        for t in task['eligible']:
            if placed: break
            for s in valid_starts.get(d, []):
                e = s + d - 1
                conflict = False
                for k in range(s, e + 1):
                    if class_grid[c][k] != -1 or teacher_grid[t][k] != -1:
                        conflict = True
                        break
                if not conflict:
                    assigned[tid] = (s, t)
                    for k in range(s, e + 1):
                        class_grid[c][k] = tid
                        teacher_grid[t][k] = tid
                    placed = True
                    break
        if not placed:
            unassigned.append(tid)

    # Score: Negative Total Duration (Maximize duration -> Minimize negative)
    # Vì bài toán yêu cầu max số lớp, nên việc xếp được nhiều lớp sẽ làm tổng duration tăng -> negative giảm -> tốt hơn.
    current_total_duration = sum(tasks[t_id]['d'] for t_id in assigned)
    current_score = -current_total_duration
    best_score = current_score
    best_assigned = assigned.copy()
    memory.add_elite(best_score, assigned)

    # === TABU SEARCH LOOP ===
    while time.time() - start_time_prog < limit:
        memory.iteration += 1
        
        # 1. RESTART STRATEGY
        if memory.need_restart():
            elite = memory.get_random_elite()
            if elite:
                assigned = elite.copy()
                # Rebuild grids from scratch
                class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
                teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]
                for tid, (s, t) in assigned.items():
                    task = next(tk for tk in tasks if tk['id'] == tid)
                    for k in range(s, s + task['d']):
                        class_grid[task['c']][k] = tid
                        teacher_grid[t][k] = tid
                
                unassigned = [t['id'] for t in tasks if t['id'] not in assigned]
                current_score = -sum(tasks[tid]['d'] for tid in assigned)
            
            memory.stagnation_count = 0
            memory.tabu_list.clear()
            continue
        
        # 2. DIVERSIFICATION STRATEGY
        if memory.is_stagnating() and memory.iteration % 20 == 0:
            assigned = perturb_solution(assigned.copy(), tasks, class_grid, teacher_grid,
                                        valid_starts, N, T, strength=0.15)
            unassigned = [t['id'] for t in tasks if t['id'] not in assigned]
            current_score = -sum(tasks[tid]['d'] for tid in assigned)

        tenure = adaptive_tenure(memory)
        
        # Chuyển đổi chế độ tìm kiếm
        mode = "INSERT" if unassigned else "OPTIMIZE"
        candidate_moves = []
        
        # === GENERATE NEIGHBORS ===
        if mode == "INSERT":
            # Cố gắng chèn các task chưa xếp được
            if unassigned:
                u_tid = random.choice(unassigned)
                u_task = next(t for t in tasks if t['id'] == u_tid)
                
                u_teachers = u_task['eligible'][:5] if len(u_task['eligible']) > 5 else u_task['eligible']
                
                for t in u_teachers:
                    slots = valid_starts.get(u_task['d'], [])
                    try_slots = random.sample(slots, min(5, len(slots)))
                    
                    for s in try_slots:
                        e = s + u_task['d'] - 1
                        victims = set()
                        
                        possible = True
                        # Kiểm tra va chạm để tìm nạn nhân (Kick move)
                        for k in range(s, e + 1):
                            c_occ = class_grid[u_task['c']][k]
                            t_occ = teacher_grid[t][k]
                            if c_occ != -1: victims.add(c_occ)
                            if t_occ != -1: victims.add(t_occ)
                            if len(victims) > 1: # Chỉ chấp nhận kick tối đa 1 nạn nhân (để đơn giản)
                                possible = False
                                break
                        
                        if not possible: continue
                        
                        # Nếu không va chạm ai -> INSERT FREE
                        if len(victims) == 0:
                            candidate_moves.append({
                                'type': 'INSERT_FREE',
                                'tid': u_tid, 'ns': s, 'nt': t,
                                'delta': -u_task['d'] # Giảm score (tốt hơn)
                            })
        
        else:  # OPTIMIZE MODE (Di chuyển task đã xếp để tìm cấu hình tốt hơn hoặc thoát kẹt)
            if assigned:
                tid = random.choice(list(assigned.keys()))
                curr_task = next(t for t in tasks if t['id'] == tid)
                old_s, old_t = assigned[tid]
                
                teachers = curr_task['eligible'][:3] if len(curr_task['eligible']) > 3 else curr_task['eligible']
                for t in teachers:
                    slots = valid_starts.get(curr_task['d'], [])
                    try_slots = random.sample(slots, min(5, len(slots)))
                    for s in try_slots:
                        if s == old_s and t == old_t: continue
                        e = s + curr_task['d'] - 1
                        conflict = False
                        for k in range(s, e + 1):
                            if (class_grid[curr_task['c']][k] != -1 and class_grid[curr_task['c']][k] != tid) or \
                               (teacher_grid[t][k] != -1 and teacher_grid[t][k] != tid):
                                conflict = True
                                break
                        if not conflict:
                            candidate_moves.append({
                                'type': 'MOVE',
                                'tid': tid, 'ns': s, 'nt': t,
                                'delta': 0 # Không đổi duration, nhưng đổi vị trí để tránh tabu
                            })

        # === SELECT BEST MOVE ===
        best_move = None
        best_adjusted_delta = float('inf')
        
        for move in candidate_moves:
            if is_move_tabu(move, current_score, best_score, memory):
                continue
            
            penalty = calculate_move_penalty(move, memory)
            adjusted_delta = move['delta'] + penalty
            
            if adjusted_delta < best_adjusted_delta:
                best_adjusted_delta = adjusted_delta
                best_move = move

        # === APPLY MOVE ===
        if best_move:
            m = best_move
            
            if m['type'] == 'INSERT_FREE':
                tid, ns, nt = m['tid'], m['ns'], m['nt']
                assigned[tid] = (ns, nt)
                unassigned.remove(tid)
                task = next(t for t in tasks if t['id'] == tid)
                for k in range(ns, ns + task['d']):
                    class_grid[task['c']][k] = tid
                    teacher_grid[nt][k] = tid
                
                memory.tabu_list[make_tabu_key(tid, ns, nt)] = memory.iteration + tenure
                
            elif m['type'] == 'MOVE':
                tid, ns, nt = m['tid'], m['ns'], m['nt']
                task = next(t for t in tasks if t['id'] == tid)
                old_s, old_t = assigned[tid]
                
                # Clear old pos
                for k in range(old_s, old_s + task['d']):
                    class_grid[task['c']][k] = -1
                    teacher_grid[old_t][k] = -1
                
                # Set new pos
                assigned[tid] = (ns, nt)
                for k in range(ns, ns + task['d']):
                    class_grid[task['c']][k] = tid
                    teacher_grid[nt][k] = tid
                
                old_key = make_tabu_key(tid, old_s, old_t)
                memory.tabu_list[old_key] = memory.iteration + tenure
            
            # Update Statistics
            new_key = make_tabu_key(m['tid'], m['ns'], m['nt'])
            memory.move_frequency[new_key] += 1
            slot_bucket = m['ns'] // 30
            region_key = (slot_bucket, m['nt'])
            memory.region_frequency[region_key] += 1
            
            current_score += m['delta']
            
            if current_score < best_score:
                best_score = current_score
                best_assigned = assigned.copy()
                memory.add_elite(best_score, assigned)
                memory.stagnation_count = 0
                memory.consecutive_improvements += 1
            else:
                memory.stagnation_count += 1
                memory.consecutive_improvements = 0
        
        # Cleanup Tabu List
        if memory.iteration % 100 == 0:
            cutoff = memory.iteration - 30
            memory.tabu_list = {k: v for k, v in memory.tabu_list.items() if v > cutoff}

    # === OUTPUT ===
    final_output = []
    for tid, (s, t) in best_assigned.items():
        task = next(tk for tk in tasks if tk['id'] == tid)
        final_output.append((task['c'] + 1, task['m'], s + 1, t + 1))
    
    if input_content is None:
        print(len(final_output))
        final_output.sort(key=lambda x: (x[0], x[1]))
        for item in final_output:
            print(f"{item[0]} {item[1]} {item[2]} {item[3]}")
    
    return len(final_output)

if __name__ == "__main__":
    solve()