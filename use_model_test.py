from ortools.sat.python import cp_model
import sys
from io import StringIO

# --- CẤU HÌNH MẶC ĐỊNH ---
SLOTS = 60
SLOTS_PER_SESSION = 6
DEFAULT_TIME_LIMIT = 5.0

def solve(input_content=None, time_limit=None):
    """
    Hàm giải sử dụng Constraint Programming (OR-Tools).
    - input_content: Nội dung file input (str).
    - time_limit: Giới hạn thời gian (seconds).
    """
    
    # 1. XỬ LÝ INPUT
    if input_content:
        sys.stdin = StringIO(input_content)
        
    input_data = sys.stdin.read().split()
    if not input_data: return 0
    
    iterator = iter(input_data)
    try:
        T = int(next(iterator))
        N = int(next(iterator))
        M = int(next(iterator))
        class_courses = []
        for _ in range(N):
            curr = []
            while True:
                val = int(next(iterator))
                if val == 0: break
                curr.append(val)
            class_courses.append(curr)
        teacher_abilities = []
        for _ in range(T):
            curr = set()
            while True:
                val = int(next(iterator))
                if val == 0: break
                curr.add(val)
            teacher_abilities.append(curr)
        durations = []
        for _ in range(M): durations.append(int(next(iterator)))
    except StopIteration:
        return 0

    # --- MÔ HÌNH HÓA (MODELING) ---
    model = cp_model.CpModel()
    
    # Biến lưu trữ: assignments[(c_idx, m_id)] = { 'start': var, 'teacher': var, 'is_present': var }
    assignments = {}
    
    # Danh sách intervals để ràng buộc không trùng
    class_intervals = [[] for _ in range(N)]
    teacher_intervals = [[] for _ in range(T)]

    for c_idx, courses in enumerate(class_courses):
        for m_id in courses:
            d = durations[m_id - 1]
            eligible = [t for t in range(T) if m_id in teacher_abilities[t]]
            if not eligible: continue

            # 1. Biến Boolean: Môn này có được xếp lịch không? (Mục tiêu là Maximize biến này)
            is_present = model.NewBoolVar(f'pres_c{c_idx}_m{m_id}')
            
            # 2. Biến Start/End
            start = model.NewIntVar(1, SLOTS - d + 1, f'start_c{c_idx}_m{m_id}')
            end = model.NewIntVar(1, SLOTS, f'end_c{c_idx}_m{m_id}')
            
            # 3. Interval (Khoảng thời gian) - OPTIONAL (chỉ tồn tại nếu is_present = true)
            interval = model.NewOptionalIntervalVar(start, d, end, is_present, f'interval_c{c_idx}_m{m_id}')
            class_intervals[c_idx].append(interval)

            # 4. Ràng buộc Session (Không vắt qua buổi)
            # start chỉ được nhận các giá trị hợp lệ
            valid_starts = []
            for s in range(1, SLOTS - d + 2):
                # Logic check session
                start_sess = (s - 1) // SLOTS_PER_SESSION
                end_sess = (s + d - 2) // SLOTS_PER_SESSION
                if start_sess == end_sess:
                    valid_starts.append(s)
            
            # Domain start chỉ nằm trong các slot hợp lệ
            model.AddAllowedAssignments([start], [[s] for s in valid_starts])

            # 5. Phân công giáo viên
            # Tạo biến bool cho từng giáo viên: t_active[t] = 1 nếu giáo viên t dạy môn này
            active_teachers = []
            for t in eligible:
                t_active = model.NewBoolVar(f'teach_c{c_idx}_m{m_id}_t{t}')
                active_teachers.append(t_active)
                
                # Link: t_active chỉ được = 1 nếu is_present = 1
                model.AddImplication(t_active, is_present)
                
                # Interval ảo cho giáo viên (cũng là optional)
                t_interval = model.NewOptionalIntervalVar(start, d, end, t_active, f't_int_c{c_idx}_m{m_id}_t{t}')
                teacher_intervals[t].append(t_interval)
            
            # Tổng số giáo viên dạy môn này phải bằng is_present (0 hoặc 1)
            model.Add(sum(active_teachers) == is_present)

            assignments[(c_idx, m_id)] = {
                'start': start, 'active_teachers': zip(eligible, active_teachers), 'is_present': is_present
            }

    # --- RÀNG BUỘC KHÔNG TRÙNG (NO OVERLAP) ---
    for c_list in class_intervals:
        model.AddNoOverlap(c_list)
    
    for t_list in teacher_intervals:
        model.AddNoOverlap(t_list)

    # --- HÀM MỤC TIÊU (Objective) ---
    # Tối đa hóa số môn được xếp (Tổng các biến is_present)
    total_scheduled = sum(info['is_present'] for info in assignments.values())
    model.Maximize(total_scheduled)

    # --- GIẢI ---
    solver = cp_model.CpSolver()
    
    # Thiết lập giới hạn thời gian từ tham số truyền vào
    limit = time_limit if time_limit is not None else DEFAULT_TIME_LIMIT
    solver.parameters.max_time_in_seconds = limit
    
    # Có thể thêm parameters để tối ưu log nếu muốn
    # solver.parameters.log_search_progress = True 
    
    status = solver.Solve(model)

    # --- OUTPUT ---
    final_count = 0
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        results = []
        for (c_idx, m_id), info in assignments.items():
            if solver.Value(info['is_present']):
                start_val = solver.Value(info['start'])
                # Tìm giáo viên được chọn
                chosen_t = -1
                for t_idx, t_var in info['active_teachers']:
                    if solver.Value(t_var):
                        chosen_t = t_idx
                        break
                results.append((c_idx + 1, m_id, start_val, chosen_t + 1))
        
        final_count = len(results)
        
        # Chỉ in ra stdout nếu không có input_content (chạy đơn lẻ)
        # hoặc benchmark runner capture stdout thì vẫn cần in.
        if input_content is None:
            print(final_count)
            results.sort(key=lambda x: (x[0], x[1]))
            for r in results:
                print(f"{r[0]} {r[1]} {r[2]} {r[3]}")
    else:
        if input_content is None:
            print(0)

    return final_count

if __name__ == "__main__":
    solve()