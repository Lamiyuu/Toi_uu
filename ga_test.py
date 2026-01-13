import sys
import random
import time

# --- CẤU HÌNH ---
SLOTS_PER_SESSION = 6
MAX_SLOTS = 60

# Cấu hình GA
POPULATION_SIZE = 100    # Số lượng cá thể trong quần thể
MAX_GENERATIONS = 200    # Số thế hệ tối đa
MUTATION_RATE = 0.1      # Tỷ lệ đột biến
ELITISM_COUNT = 5        # Giữ lại bao nhiêu cá thể tốt nhất

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

# --- CLASS BIỂU DIỄN 1 CÁ THỂ (SCHEDULE) ---
class Schedule:
    def __init__(self, tasks, teacher_abilities, empty=False):
        self.tasks = tasks
        self.teacher_abilities = teacher_abilities
        self.genes = [None] * len(tasks)
        self.fitness = -float('inf')
        
        if not empty:
            self.random_init()

    def random_init(self):
        for i, task in enumerate(self.tasks):
            possible_teachers = list(task['eligible'])
            if not possible_teachers: continue
            
            t = random.choice(possible_teachers)
            duration = task['d']
            valid_starts = []
            for s in range(1, MAX_SLOTS - duration + 2):
                if is_valid_session(s, duration):
                    valid_starts.append(s)
            
            if valid_starts:
                s = random.choice(valid_starts)
                self.genes[i] = (s, t)
            else:
                self.genes[i] = (1, t) 

    def calculate_fitness(self, num_classes, num_teachers):
        conflicts = 0
        class_occupancy = {}   
        teacher_occupancy = {} 
        assigned_count = 0
        
        for idx, gene in enumerate(self.genes):
            if gene is None: continue
            assigned_count += 1
            
            start, teacher = gene
            task = self.tasks[idx]
            class_id = task['c']
            duration = task['d']
            
            for s in range(start, start + duration):
                if (class_id, s) in class_occupancy: conflicts += 1
                else: class_occupancy[(class_id, s)] = idx
                
                if (teacher, s) in teacher_occupancy: conflicts += 1
                else: teacher_occupancy[(teacher, s)] = idx

        self.fitness = (assigned_count * 10) - (conflicts * 50)
        return self.fitness, conflicts

def solve(input_content=None, time_limit=0.95):
    start_time = time.time()
    # 1. ĐỌC DỮ LIỆU
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

    # Tạo danh sách Tasks
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
            
    # --- GA LOOP ---
    population = [Schedule(tasks, teacher_abilities) for _ in range(POPULATION_SIZE)]
    global_best_fitness = -float('inf')
    global_best_schedule = None
    
    for generation in range(MAX_GENERATIONS):
        for ind in population:
            ind.calculate_fitness(N, T)
        
        population.sort(key=lambda x: x.fitness, reverse=True)
        
        current_best = population[0]
        if current_best.fitness > global_best_fitness:
            global_best_fitness = current_best.fitness
            global_best_schedule = current_best
            
        if global_best_fitness == len(tasks) * 10:
            break
            
        new_population = []
        new_population.extend(population[:ELITISM_COUNT])
        
        while len(new_population) < POPULATION_SIZE:
            parent1 = random.choice(population[:50])
            parent2 = random.choice(population[:50])
            
            child = Schedule(tasks, teacher_abilities, empty=True)
            for i in range(len(tasks)):
                if random.random() < 0.5:
                    child.genes[i] = parent1.genes[i]
                else:
                    child.genes[i] = parent2.genes[i]
            
            if random.random() < MUTATION_RATE:
                idx_to_mutate = random.randint(0, len(tasks) - 1)
                task = tasks[idx_to_mutate]
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
    best_ind = global_best_schedule
    
    final_output = []
    class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]
    
    for i, gene in enumerate(best_ind.genes):
        if gene is None: continue
        s, t = gene
        task = tasks[i]
        c, d = task['c'], task['d']
        e = s + d - 1
        
        is_conflict = False
        for k in range(s, e + 1):
            if class_grid[c][k] != -1 or teacher_grid[t][k] != -1:
                is_conflict = True
                break
        
        if not is_conflict:
            final_output.append((c + 1, task['m'], s, t + 1))
            for k in range(s, e + 1):
                class_grid[c][k] = task['id']
                teacher_grid[t][k] = task['id']

    if input_content is None:
        print(len(final_output))
        final_output.sort(key=lambda x: (x[0], x[1]))
        for item in final_output:
            print(f"{item[0]} {item[1]} {item[2]} {item[3]}")

    return len(final_output)

if __name__ == "__main__":    
    solve()