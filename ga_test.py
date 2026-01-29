import random
import copy
import sys
import time
from io import StringIO

# --- CẤU TRÚC DỮ LIỆU ---

class Task:
    def __init__(self, id, class_id, subject_id, duration, capable_teachers):
        self.id = id
        self.class_id = class_id
        self.subject_id = subject_id
        self.duration = duration
        self.capable_teachers = capable_teachers

class ProblemData:
    def __init__(self):
        self.T = 0 
        self.N = 0 
        self.M = 0 
        self.tasks = []

# Biến toàn cục (Sẽ được reset trong hàm solve)
data = ProblemData()

# --- INPUT READING ---
def read_input():
    # Đọc từ sys.stdin (đã được redirect trong solve)
    try:
        input_data = sys.stdin.read().split()
    except Exception:
        return

    if not input_data: return
    iterator = iter(input_data)
    
    try:
        data.T = int(next(iterator))
        data.N = int(next(iterator))
        data.M = int(next(iterator))
        
        class_reqs = []
        for i in range(1, data.N + 1):
            while True:
                val = int(next(iterator))
                if val == 0: break
                class_reqs.append((i, val))
        
        teacher_caps = {}
        for t in range(1, data.T + 1):
            while True:
                val = int(next(iterator))
                if val == 0: break
                if val not in teacher_caps: teacher_caps[val] = []
                teacher_caps[val].append(t)
                
        durations = {}
        for m in range(1, data.M + 1):
            durations[m] = int(next(iterator))
            
        task_id = 0
        for c_id, s_id in class_reqs:
            dur = durations.get(s_id, 0)
            caps = teacher_caps.get(s_id, [])
            if dur > 0 and caps:
                data.tasks.append(Task(task_id, c_id, s_id, dur, caps))
                task_id += 1
            
    except StopIteration:
        pass

# --- LOGIC THỜI GIAN ---
def get_valid_slots(duration):
    slots = []
    for k in range(10):
        start_session = k * 6 + 1
        end_session = start_session + 6
        last_start = end_session - duration
        if last_start >= start_session:
            slots.extend(range(start_session, last_start + 1))
    return slots

# --- GENETIC ALGORITHM COMPONENTS ---

class Individual:
    def __init__(self, permutation):
        self.permutation = permutation 
        self.fitness = -1
        self.schedule = [] 
        self.failed_tasks = [] 

    @classmethod
    def random_create(cls):
        perm = list(range(len(data.tasks)))
        random.shuffle(perm)
        return cls(perm)

def decode_and_evaluate(ind):
    class_busy = [[-1] * 61 for _ in range(data.N + 1)]
    teacher_busy = [[-1] * 61 for _ in range(data.T + 1)]
    
    assigned_count = 0
    assignment_details = []
    failed_tasks = []
    
    for task_idx in ind.permutation:
        task = data.tasks[task_idx]
        valid_starts = get_valid_slots(task.duration)
        
        chosen_slot = -1
        chosen_teacher = -1
        
        # Greedy Search: First Fit
        for start in valid_starts:
            end = start + task.duration
            
            # 1. Check Lớp
            c_conflict = False
            for t in range(start, end):
                if class_busy[task.class_id][t] != -1:
                    c_conflict = True; break
            if c_conflict: continue
            
            # 2. Check Giáo viên
            for t_id in task.capable_teachers:
                t_conflict = False
                for t in range(start, end):
                    if teacher_busy[t_id][t] != -1:
                        t_conflict = True; break
                if not t_conflict:
                    chosen_teacher = t_id
                    break
            
            if chosen_teacher != -1:
                chosen_slot = start
                break
        
        if chosen_slot != -1:
            assigned_count += 1
            end = chosen_slot + task.duration
            for t in range(chosen_slot, end):
                class_busy[task.class_id][t] = task.id
                teacher_busy[chosen_teacher][t] = task.id
            
            assignment_details.append({
                'class': task.class_id,
                'sub': task.subject_id,
                'start': chosen_slot,
                'teacher': chosen_teacher
            })
        else:
            failed_tasks.append(task_idx)
            
    ind.fitness = assigned_count
    ind.schedule = assignment_details
    ind.failed_tasks = failed_tasks
    return ind.fitness

# --- MEMETIC LOCAL SEARCH ---
def memetic_local_search(ind):
    if not ind.failed_tasks: return
    
    rescue_candidates = ind.failed_tasks
    if len(rescue_candidates) > 3: 
        rescue_candidates = random.sample(rescue_candidates, 3)
        
    current_perm = list(ind.permutation)
    
    for task_idx in rescue_candidates:
        try:
            current_pos = current_perm.index(task_idx)
        except ValueError: continue
            
        new_pos = max(0, int(current_pos * 0.5)) 
        
        current_perm.pop(current_pos)
        current_perm.insert(new_pos, task_idx)
        
    temp_ind = Individual(current_perm)
    decode_and_evaluate(temp_ind)
    
    if temp_ind.fitness > ind.fitness:
        ind.permutation = temp_ind.permutation
        ind.fitness = temp_ind.fitness
        ind.schedule = temp_ind.schedule
        ind.failed_tasks = temp_ind.failed_tasks

# --- GA OPERATIONS ---

def crossover(p1, p2):
    size = len(p1.permutation)
    if size < 2: return copy.deepcopy(p1), copy.deepcopy(p2)
    cx1, cx2 = sorted(random.sample(range(size), 2))
    
    def ox_create(parent1, parent2):
        child_perm = [-1] * size
        child_perm[cx1:cx2+1] = parent1.permutation[cx1:cx2+1]
        current_pos = (cx2 + 1) % size
        p2_pos = (cx2 + 1) % size
        copied_set = set(child_perm[cx1:cx2+1])
        count = 0
        while count < size - (cx2 - cx1 + 1):
            gene = parent2.permutation[p2_pos]
            if gene not in copied_set:
                child_perm[current_pos] = gene
                current_pos = (current_pos + 1) % size
                count += 1
            p2_pos = (p2_pos + 1) % size
        return Individual(child_perm)

    return ox_create(p1, p2), ox_create(p2, p1)

def mutate(ind, mutation_rate=0.1):
    if random.random() < mutation_rate:
        size = len(ind.permutation)
        if size > 1:
            i, j = random.sample(range(size), 2)
            ind.permutation[i], ind.permutation[j] = ind.permutation[j], ind.permutation[i]
            ind.fitness = -1 

# --- MAIN SOLVER ---

def solve(input_content=None, time_limit=None):
    """
    Hàm giải GA (Memetic) chuẩn cho Benchmark.
    """
    start_time = time.time()
    
    # 1. Reset dữ liệu toàn cục để tránh xung đột giữa các lần chạy
    global data
    data = ProblemData()
    
    # 2. Xử lý Input
    if input_content:
        sys.stdin = StringIO(input_content)
    
    read_input()
    
    num_tasks = len(data.tasks)
    if num_tasks == 0: 
        return {"count": 0, "makespan": 0}

    # 3. Cấu hình
    DEFAULT_TIME_LIMIT = 5.0
    limit = time_limit if time_limit is not None else DEFAULT_TIME_LIMIT
    
    POP_SIZE = 40
    MUTATION_RATE = 0.2
    
    # Khởi tạo quần thể
    population = [Individual.random_create() for _ in range(POP_SIZE)]
    best_global = None
    
    # Đánh giá ban đầu
    for ind in population:
        decode_and_evaluate(ind)
        if best_global is None or ind.fitness > best_global.fitness:
            best_global = copy.deepcopy(ind)

    # 4. Vòng lặp Tiến hóa (Dựa trên thời gian)
    generation = 0
    while time.time() - start_time < limit:
        generation += 1
        
        # Nếu đã tối ưu tuyệt đối thì dừng
        if best_global.fitness == num_tasks: break 
        
        population.sort(key=lambda x: x.fitness, reverse=True)
        next_gen = population[:int(POP_SIZE * 0.1)] 
        
        mating_pool = population[:int(POP_SIZE*0.6)]
        
        while len(next_gen) < POP_SIZE:
            # Kiểm tra thời gian trong vòng lặp con để thoát nhanh
            if time.time() - start_time > limit: break

            p1, p2 = random.sample(mating_pool, 2)
            
            c1, c2 = crossover(p1, p2)
            mutate(c1, MUTATION_RATE)
            mutate(c2, MUTATION_RATE)
            
            decode_and_evaluate(c1)
            decode_and_evaluate(c2)
            
            # Memetic Local Search (chỉ chạy cho cá thể tốt để tiết kiệm thời gian)
            if c1.fitness >= best_global.fitness * 0.9:
                memetic_local_search(c1)
            if c2.fitness >= best_global.fitness * 0.9:
                memetic_local_search(c2)
            
            next_gen.append(c1)
            if len(next_gen) < POP_SIZE: next_gen.append(c2)
            
            if c1.fitness > best_global.fitness: best_global = copy.deepcopy(c1)
            if c2.fitness > best_global.fitness: best_global = copy.deepcopy(c2)
        
        population = next_gen

    # 5. Output & Tính Makespan
    makespan = 0
    finish_times = []
    
    if best_global.schedule:
        for item in best_global.schedule:
            # item: {'class', 'sub', 'start', 'teacher'}
            # Tìm duration từ data.tasks
            # (Duyệt tìm task có class và sub tương ứng)
            d = 0
            for t in data.tasks:
                if t.class_id == item['class'] and t.subject_id == item['sub']:
                    d = t.duration
                    break
            
            finish_times.append(item['start'] + d)
        
        if finish_times:
            makespan = max(finish_times)

    # In ra stdout nếu chạy đơn lẻ
    if input_content is None:
        print(best_global.fitness)
        best_global.schedule.sort(key=lambda x: (x['class'], x['start']))
        for item in best_global.schedule:
            print(f"{item['class']} {item['sub']} {item['start']} {item['teacher']}")

    # Trả về Dict cho Benchmark
    return {
        "count": best_global.fitness,
        "makespan": makespan
    }

if __name__ == "__main__":
    solve()