import random
import time
# Nạp các hàm tiện ích từ file utils.py
from utils import load_and_preprocess, MAX_SLOTS

# --- CẤU HÌNH GA ---
POPULATION_SIZE = 100    # Kích thước quần thể
MAX_GENERATIONS = 2000   # Tăng số thế hệ lên vì xử lý nhanh hơn
MUTATION_RATE = 0.1      # Tỷ lệ đột biến
ELITISM_COUNT = 5        # Số cá thể tinh hoa giữ lại
TIME_LIMIT = 0.95        # Giới hạn thời gian (giây)

# --- CLASS BIỂU DIỄN CÁ THỂ ---
class Schedule:
    def __init__(self, tasks, valid_starts, empty=False):
        self.tasks = tasks
        self.valid_starts = valid_starts
        # Genes: List các tuple (start_slot, teacher_id)
        # Index của genes tương ứng với index trong danh sách tasks
        self.genes = [None] * len(tasks) 
        self.fitness = -float('inf')
        
        if not empty:
            self.random_init()

    def random_init(self):
        """Khởi tạo ngẫu nhiên nhưng hợp lệ về mặt thời gian (dùng valid_starts)"""
        for i, task in enumerate(self.tasks):
            # 1. Chọn giáo viên ngẫu nhiên trong danh sách eligible
            if not task['eligible']: continue # Should not happen
            t = random.choice(task['eligible'])
            
            # 2. Chọn slot bắt đầu ngẫu nhiên từ Cache đã tính trước
            # (Không cần check is_valid_session nữa vì cache đã chuẩn rồi)
            possible_slots = self.valid_starts.get(task['d'], [])
            if possible_slots:
                s = random.choice(possible_slots)
                self.genes[i] = (s, t)
            else:
                # Trường hợp hiếm: môn quá dài không có slot (fallback)
                self.genes[i] = (1, t)

    def calculate_fitness(self, num_classes, num_teachers):
        """Tính điểm: Thưởng nếu xếp được, Phạt nếu trùng lịch"""
        assigned_count = 0
        conflicts = 0
        
        # Grid check nhanh (reset mỗi lần tính)
        # 0: Trống, 1: Bận
        # Lưu ý: Class index trong task là 0-based
        class_busy = [set() for _ in range(num_classes)]
        teacher_busy = [set() for _ in range(num_teachers + 1)] # Teacher ID 1-based or 0-based? 
        # Trong utils, teacher ID từ input thường là 1-based, ta nên check lại input. 
        # Để an toàn ta dùng mảng rộng hoặc dict. Ở đây dùng list set cho nhanh.
        
        for i, gene in enumerate(self.genes):
            if gene is None: continue
            
            s, t = gene
            task = self.tasks[i]
            c_idx = task['c']
            d = task['d']
            e = s + d - 1
            
            # Check xung đột
            is_conflict = False
            
            # Check Class
            for k in range(s, e + 1):
                if k in class_busy[c_idx]: is_conflict = True
                if k in teacher_busy[t]: is_conflict = True # t is usually 0-based in preprocessing? 
                # Kiểm tra lại utils: eligible lấy từ range(T), tức là 0-based.
                
                if is_conflict: break
            
            if is_conflict:
                conflicts += 1
            else:
                # Nếu không xung đột thì đánh dấu bận
                for k in range(s, e + 1):
                    class_busy[c_idx].add(k)
                    teacher_busy[t].add(k)
                assigned_count += 1
        
        # Hàm mục tiêu:
        # Càng nhiều môn được xếp càng tốt
        # Càng ít xung đột càng tốt (thực ra logic trên đã loại conflict khỏi grid, 
        # nên conflict chỉ đếm số task bị trùng lấp không xếp được vào grid)
        self.fitness = (assigned_count * 1000) - (conflicts * 10)
        return self.fitness

# --- HÀM GIẢI CHÍNH ---
def solve(input_content=None, time_limit=TIME_LIMIT):
    start_time = time.time()
    
    # 1. GỌI TIỀN XỬ LÝ (Thay thế toàn bộ đoạn đọc file cũ)
    # Lưu ý: utils.py cần được chỉnh để nhận input_content nếu chạy benchmark
    # Tuy nhiên hàm load_and_preprocess mặc định đọc sys.stdin.
    # Để tương thích benchmark runner (truyền string), ta cần patch nhẹ sys.stdin hoặc sửa utils.
    # Ở đây giả sử utils đọc từ sys.stdin chuẩn, hoặc ta mock input nếu cần.
    
    # KHI CHẠY THỰC TẾ VỚI BENCHMARK RUNNER:
    # Benchmark Runner truyền string vào input_content.
    # Ta cần giả lập sys.stdin để utils đọc được.
    if input_content:
        import sys
        from io import StringIO
        sys.stdin = StringIO(input_content)

    data = load_and_preprocess()
    if data is None: return 0

    T, N, tasks = data['T'], data['N'], data['tasks']
    valid_starts = data['valid_starts']
    
    # 2. KHỞI TẠO QUẦN THỂ
    population = [Schedule(tasks, valid_starts) for _ in range(POPULATION_SIZE)]
    
    global_best_fitness = -float('inf')
    global_best_schedule = None
    
    # 3. VÒNG LẶP TIẾN HÓA
    generation = 0
    while True:
        # Check Time Limit
        if time.time() - start_time > time_limit:
            break
        if generation >= MAX_GENERATIONS:
            break
            
        generation += 1
        
        # Đánh giá Fitness
        for ind in population:
            ind.calculate_fitness(N, T)
        
        # Sort
        population.sort(key=lambda x: x.fitness, reverse=True)
        
        # Cập nhật Best Global
        if population[0].fitness > global_best_fitness:
            global_best_fitness = population[0].fitness
            global_best_schedule = population[0]
            
        # Tạo thế hệ mới
        new_population = []
        
        # Elitism
        new_population.extend(population[:ELITISM_COUNT])
        
        # Lai ghép & Đột biến
        # Chỉ lấy top 50% làm cha mẹ để tăng chất lượng
        parents_pool = population[:50] 
        
        while len(new_population) < POPULATION_SIZE:
            # Tournament Selection đơn giản
            p1 = random.choice(parents_pool)
            p2 = random.choice(parents_pool)
            
            # Crossover (Uniform)
            child = Schedule(tasks, valid_starts, empty=True)
            for i in range(len(tasks)):
                if random.random() < 0.5:
                    child.genes[i] = p1.genes[i]
                else:
                    child.genes[i] = p2.genes[i]
            
            # Mutation
            if random.random() < MUTATION_RATE:
                # Chọn random 1 gen để đột biến
                idx = random.randint(0, len(tasks) - 1)
                task = tasks[idx]
                
                # Chọn lại giá trị mới từ Cache
                possible_slots = valid_starts.get(task['d'], [])
                if possible_slots:
                    new_s = random.choice(possible_slots)
                    new_t = random.choice(task['eligible'])
                    child.genes[idx] = (new_s, new_t)
            
            new_population.append(child)
            
        population = new_population

    # 4. XUẤT KẾT QUẢ
    # Lấy schedule tốt nhất
    best = global_best_schedule
    
    # Tạo lại output sạch (không conflict)
    final_output = []
    
    # Grid check lần cuối
    class_grid = [[False] * (MAX_SLOTS + 1) for _ in range(N)]
    teacher_grid = [[False] * (MAX_SLOTS + 1) for _ in range(T)] # T index 0-based
    
    # Ưu tiên task trong genes của best individual
    for i, gene in enumerate(best.genes):
        if gene is None: continue
        s, t = gene
        task = tasks[i]
        c, d = task['c'], task['d']
        e = s + d - 1
        
        # Validate final conflict
        is_conflict = False
        for k in range(s, e + 1):
            if class_grid[c][k] or teacher_grid[t][k]:
                is_conflict = True; break
        
        if not is_conflict:
            # Add to result
            # Output format: ClassID(1-based) SubjectID Start TeacherID(1-based)
            # Trong utils, task['m'] đã là ID gốc, task['c'] là 0-based index
            # Teacher ID t là 0-based index từ eligible range(T) -> Cần +1 khi in
            final_output.append((c + 1, task['m'], s, t + 1))
            
            # Mark busy
            for k in range(s, e + 1):
                class_grid[c][k] = True
                teacher_grid[t][k] = True

    # In kết quả (Nếu chạy benchmark runner thì return len, nếu chạy trực tiếp thì print)
    if input_content is None:
        print(len(final_output))
        final_output.sort(key=lambda x: (x[0], x[1]))
        for item in final_output:
            print(f"{item[0]} {item[1]} {item[2]} {item[3]}")
            
    return len(final_output)

if __name__ == "__main__":
    solve()