import sys
import random
import time

# --- CẤU HÌNH ---
SLOTS_PER_SESSION = 6
SESSIONS_PER_DAY = 2
DAYS = 5
MAX_SLOTS = DAYS * SESSIONS_PER_DAY * SLOTS_PER_SESSION  # 60 tiết

# Cấu hình GA
POPULATION_SIZE = 100    # Số lượng cá thể trong quần thể
MAX_GENERATIONS = 200    # Số thế hệ tối đa
MUTATION_RATE = 0.1      # Tỷ lệ đột biến
ELITISM_COUNT = 5        # Giữ lại bao nhiêu cá thể tốt nhất

# --- HÀM ĐỌC DỮ LIỆU (GIỮ NGUYÊN) ---
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
    # Kiểm tra xem start và end có cùng thuộc một kíp (sáng/chiều) không
    return ((start - 1) // SLOTS_PER_SESSION) == ((end - 1) // SLOTS_PER_SESSION)

# --- CLASS BIỂU DIỄN 1 CÁ THỂ (SCHEDULE) ---
class Schedule:
    def __init__(self, tasks, teacher_abilities, empty=False):
        self.tasks = tasks # Tham chiếu đến danh sách task gốc
        self.teacher_abilities = teacher_abilities
        self.genes = [None] * len(tasks) # genes[i] = (start_slot, teacher_id)
        self.fitness = -float('inf')
        
        if not empty:
            self.random_init()

    def random_init(self):
        for i, task in enumerate(self.tasks):
            # Random hợp lệ ngay từ đầu để giảm không gian tìm kiếm
            possible_teachers = list(task['eligible'])
            if not possible_teachers: continue # Should not happen if data is valid
            
            t = random.choice(possible_teachers)
            
            # Random slot hợp lệ
            duration = task['d']
            valid_starts = []
            for s in range(1, MAX_SLOTS - duration + 2):
                if is_valid_session(s, duration):
                    valid_starts.append(s)
            
            if valid_starts:
                s = random.choice(valid_starts)
                self.genes[i] = (s, t)
            else:
                # Trường hợp môn học quá dài không nhét vừa slot nào (hiếm)
                self.genes[i] = (1, t) 

    def calculate_fitness(self, num_classes, num_teachers):
        conflicts = 0
        
        # Grid để check nhanh: [ResourceID][TimeSlot]
        # ResourceID: 0 -> num_classes-1 (Lớp), num_classes -> ... (Giáo viên)
        # Giá trị grid: 1 nếu đã bận
        
        # Tuy nhiên để tiết kiệm bộ nhớ trong Python, ta dùng Set hoặc check chéo
        # Ở đây dùng logic check chéo tối ưu hơn cho số lượng task nhỏ
        
        # Xây dựng bản đồ chiếm dụng
        class_occupancy = {}   # Key: (class_id, slot) -> Value: task_index
        teacher_occupancy = {} # Key: (teacher_id, slot) -> Value: task_index
        
        assigned_count = 0
        
        for idx, gene in enumerate(self.genes):
            if gene is None: continue # Task này chưa gán được (phạt nặng)
            assigned_count += 1
            
            start, teacher = gene
            task = self.tasks[idx]
            class_id = task['c']
            duration = task['d']
            
            # Check từng slot thời gian
            for s in range(start, start + duration):
                # 1. Check Class Conflict
                if (class_id, s) in class_occupancy:
                    conflicts += 1
                else:
                    class_occupancy[(class_id, s)] = idx
                
                # 2. Check Teacher Conflict
                if (teacher, s) in teacher_occupancy:
                    conflicts += 1
                else:
                    teacher_occupancy[(teacher, s)] = idx

        # Fitness: Ưu tiên số lượng task được gán, trừ đi xung đột
        # Weight: Gán được task (+10), Xung đột (-50)
        self.fitness = (assigned_count * 10) - (conflicts * 50)
        return self.fitness, conflicts

# --- HÀM GIẢI CHÍNH BẰNG GA ---
def solve_genetic_algorithm():
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
                curr.add(val) # Python set: 0-based or input is 1-based? Input usually 1-based teacher ID?
                # Code cũ của bạn: teacher_abilities[t] chứa m_id.
                # Input teacher khả năng: Dòng chứa các môn teacher dạy được.
            teacher_abilities.append(curr)
        durations = []
        for _ in range(M): durations.append(next(reader))
    except StopIteration: return

    # Chuyển đổi ID giáo viên về 0-based nếu cần, nhưng set môn học giữ nguyên
    # Tạo danh sách Tasks
    tasks = []
    task_counter = 0
    for c_idx, courses in enumerate(class_courses):
        for m_id in courses:
            # Tìm giáo viên dạy được môn m_id
            eligible = [t for t in range(T) if m_id in teacher_abilities[t]]
            tasks.append({
                'id': task_counter,
                'c': c_idx, 
                'm': m_id, 
                'd': durations[m_id - 1], 
                'eligible': eligible
            })
            task_counter += 1
            
    # --- GA LOOP ---
    
    # 1. Khởi tạo quần thể
    population = [Schedule(tasks, teacher_abilities) for _ in range(POPULATION_SIZE)]
    
    global_best_fitness = -float('inf')
    global_best_schedule = None
    
    start_time = time.time()
    
    for generation in range(MAX_GENERATIONS):
        # Đánh giá fitness
        for ind in population:
            ind.calculate_fitness(N, T)
        
        # Sort theo fitness giảm dần
        population.sort(key=lambda x: x.fitness, reverse=True)
        
        # Lưu best
        current_best = population[0]
        if current_best.fitness > global_best_fitness:
            global_best_fitness = current_best.fitness
            global_best_schedule = current_best
            
        # Kiểm tra điều kiện dừng sớm (Nếu fitness đạt tối đa lý thuyết)
        # Lý thuyết: assign hết task (len(tasks)*10) và 0 conflict
        if global_best_fitness == len(tasks) * 10:
            break
            
        # Lai ghép & Đột biến để tạo thế hệ mới
        new_population = []
        
        # Elitism: Giữ lại top cá thể tốt nhất
        new_population.extend(population[:ELITISM_COUNT])
        
        # Sinh các cá thể còn lại
        while len(new_population) < POPULATION_SIZE:
            # Tournament Selection (Chọn cha mẹ)
            parent1 = random.choice(population[:50]) # Chọn trong top 50
            parent2 = random.choice(population[:50])
            
            # Crossover (Uniform Crossover)
            child = Schedule(tasks, teacher_abilities, empty=True)
            for i in range(len(tasks)):
                if random.random() < 0.5:
                    child.genes[i] = parent1.genes[i]
                else:
                    child.genes[i] = parent2.genes[i]
            
            # Mutation
            if random.random() < MUTATION_RATE:
                # Đột biến: Random lại 1 task bất kỳ
                idx_to_mutate = random.randint(0, len(tasks) - 1)
                task = tasks[idx_to_mutate]
                
                # Chọn lại giáo viên và giờ mới
                possible_teachers = task['eligible']
                if possible_teachers:
                    new_t = random.choice(list(possible_teachers))
                    valid_starts = []
                    d = task['d']
                    for s in range(1, MAX_SLOTS - d + 2):
                        if is_valid_session(s, d): valid_starts.append(s)
                    
                    if valid_starts:
                        new_s = random.choice(valid_starts)
                        child.genes[idx_to_mutate] = (new_s, new_t)
            
            new_population.append(child)
            
        population = new_population

    # --- OUTPUT ---
    # Lấy schedule tốt nhất tìm được
    best_ind = global_best_schedule
    best_fitness, conflicts = best_ind.calculate_fitness(N, T)
    
    # Lọc các task hợp lệ để in (Nếu còn conflict thì phải loại bỏ bớt để output clean)
    # Tuy nhiên, đề bài thường yêu cầu in ra tối đa số lượng xếp được.
    # Ta sẽ chạy lại check lần cuối, cái nào conflict thì vứt (để đảm bảo output đúng luật)
    
    final_output = []
    class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]
    
    # Sắp xếp các task theo mức độ ưu tiên (tùy chọn) trước khi đưa vào final check
    # Ở đây ta duyệt tuần tự theo genes của best individual
    
    assigned_count = 0
    for i, gene in enumerate(best_ind.genes):
        if gene is None: continue
        s, t = gene
        task = tasks[i]
        c, d = task['c'], task['d']
        e = s + d - 1
        
        # Final validation
        is_conflict = False
        for k in range(s, e + 1):
            if class_grid[c][k] != -1 or teacher_grid[t][k] != -1:
                is_conflict = True
                break
        
        if not is_conflict:
            # Chấp nhận
            assigned_count += 1
            final_output.append((c + 1, task['m'], s, t + 1)) # Output 1-based
            for k in range(s, e + 1):
                class_grid[c][k] = task['id']
                teacher_grid[t][k] = task['id']

    print(len(final_output))
    final_output.sort(key=lambda x: (x[0], x[1])) # Sort theo Class rồi đến Course
    for item in final_output:
        print(f"{item[0]} {item[1]} {item[2]} {item[3]}")

if __name__ == "__main__":    
    solve_genetic_algorithm()
