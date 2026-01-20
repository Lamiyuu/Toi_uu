import random
import time
import sys
# Nạp các hàm tiện ích từ file utils.py
from utils import load_and_preprocess, MAX_SLOTS

# --- CẤU HÌNH PSO MẶC ĐỊNH ---
NUM_PARTICLES = 30   # Số lượng hạt
W = 0.7              # Trọng số quán tính (Inertia)
C1 = 1.5             # Hệ số cá nhân (Cognitive)
C2 = 1.5             # Hệ số xã hội (Social)
DEFAULT_TIME_LIMIT = 0.95    # Giới hạn thời gian mặc định (nếu chạy lẻ)

# --- HÀM GIẢI CHÍNH ---
def solve(input_content=None, time_limit=None):
    """
    Hàm giải chính của PSO.
    - input_content: Nội dung file input (str)
    - time_limit: Giới hạn thời gian chạy (float), nếu None sẽ dùng mặc định.
    """
    start_time = time.time()
    
    # XÁC ĐỊNH GIỚI HẠN THỜI GIAN
    # Nếu benchmark truyền time_limit thì dùng, không thì dùng mặc định
    limit = time_limit if time_limit is not None else DEFAULT_TIME_LIMIT
    
    # 1. GỌI TIỀN XỬ LÝ
    # Giả lập stdin nếu có input string (dùng cho benchmark runner)
    if input_content:
        from io import StringIO
        sys.stdin = StringIO(input_content)

    data = load_and_preprocess()
    if data is None: return 0

    # Bung dữ liệu ra các biến
    T, N, tasks = data['T'], data['N'], data['tasks']
    valid_starts = data['valid_starts']
    num_tasks = data['num_tasks']

    # --- HÀM DECODER (Random Key to Schedule) ---
    def decode_and_evaluate(position_vector):
        """
        Biến vector số thực (position) thành lịch học và tính điểm.
        Sử dụng valid_starts từ utils để tăng tốc.
        """
        # 1. Gán priority và sort
        # position_vector[i] là độ ưu tiên của tasks[i]
        indexed_tasks = []
        for i in range(num_tasks):
            indexed_tasks.append((position_vector[i], tasks[i]))
        
        # Sort giảm dần theo priority (số lớn ưu tiên trước)
        indexed_tasks.sort(key=lambda x: x[0], reverse=True)
        
        # 2. Chạy Greedy Constructive
        current_assigned = []
        
        # Grid check nhanh (Reset mỗi lần decode)
        class_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(N)]
        teacher_grid = [[-1] * (MAX_SLOTS + 1) for _ in range(T)]
        
        assigned_count = 0
        sum_start_time = 0
        
        for _, task in indexed_tasks:
            c, d = task['c'], task['d'] # c is 0-based
            placed = False
            
            # Chọn giáo viên
            for t in task['eligible']: # t is 0-based
                if placed: break
                
                # LẤY SLOT TỪ CACHE (TỐI ƯU HÓA)
                # Thay vì tính toán lại, lấy luôn list slot hợp lệ
                slots = valid_starts.get(d, [])
                
                for s in slots:
                    e = s + d - 1
                    
                    # Check Conflict
                    conflict = False
                    for k in range(s, e + 1):
                        if class_grid[c][k] != -1 or teacher_grid[t][k] != -1:
                            conflict = True; break
                    
                    if not conflict:
                        # Gán task
                        for k in range(s, e + 1):
                            class_grid[c][k] = task['id']
                            teacher_grid[t][k] = task['id']
                            
                        # Lưu kết quả (Class và Teacher cần +1 khi in, nhưng lưu raw trước)
                        current_assigned.append((c, task['m'], s, t))
                        
                        assigned_count += 1
                        sum_start_time += s
                        placed = True
                        break
        
        # 3. Tính Fitness (Minimize Cost)
        # Cost = (Số môn chưa xếp * Phạt nặng) + Tổng thời gian bắt đầu
        n_unassigned = num_tasks - assigned_count
        cost = n_unassigned * 1_000_000 + sum_start_time
        return cost, current_assigned

    # --- KHỞI TẠO PSO ---
    particles_pos = []      # Vị trí
    particles_vel = []      # Vận tốc
    particles_pbest_pos = [] # PBest Position
    particles_pbest_val = [] # PBest Value
    
    global_best_pos = None
    global_best_val = float('inf')
    global_best_sol = []

    for _ in range(NUM_PARTICLES):
        # Random Keys: [0.0, 1.0]
        pos = [random.random() for _ in range(num_tasks)]
        # Vận tốc nhỏ khởi đầu
        vel = [(random.random() - 0.5) * 0.1 for _ in range(num_tasks)]
        
        val, sol = decode_and_evaluate(pos)
        
        particles_pos.append(pos)
        particles_vel.append(vel)
        particles_pbest_pos.append(list(pos))
        particles_pbest_val.append(val)
        
        if val < global_best_val:
            global_best_val = val
            global_best_pos = list(pos)
            global_best_sol = sol

    # --- VÒNG LẶP PSO ---
    # Sử dụng biến limit đã xác định ở trên
    while time.time() - start_time < limit:
        for i in range(NUM_PARTICLES):
            # Cập nhật từng chiều (dimension)
            for d in range(num_tasks):
                r1 = random.random()
                r2 = random.random()
                
                # Update Velocity
                # v = w*v + c1*r1*(pbest-x) + c2*r2*(gbest-x)
                vel_new = (W * particles_vel[i][d]) + \
                          (C1 * r1 * (particles_pbest_pos[i][d] - particles_pos[i][d])) + \
                          (C2 * r2 * (global_best_pos[d] - particles_pos[i][d]))
                
                # Clamp Velocity (Tránh bay quá xa)
                vel_new = max(-0.2, min(0.2, vel_new))
                particles_vel[i][d] = vel_new
                
                # Update Position
                particles_pos[i][d] += vel_new
            
            # Đánh giá lại
            val, sol = decode_and_evaluate(particles_pos[i])
            
            # Update PBest
            if val < particles_pbest_val[i]:
                particles_pbest_val[i] = val
                particles_pbest_pos[i] = list(particles_pos[i])
                
                # Update GBest
                if val < global_best_val:
                    global_best_val = val
                    global_best_pos = list(particles_pos[i])
                    global_best_sol = sol

    # --- OUTPUT ---
    # Chuẩn hóa format đầu ra
    final_output = []
    for (c, m, s, t) in global_best_sol:
        # Utils dùng 0-based index cho c và t, output cần 1-based
        final_output.append((c + 1, m, s, t + 1))

    if input_content is None:
        print(len(final_output))
        final_output.sort(key=lambda x: (x[0], x[1]))
        for item in final_output:
            print(f"{item[0]} {item[1]} {item[2]} {item[3]}")
    
    return len(final_output)

if __name__ == "__main__":
    solve()