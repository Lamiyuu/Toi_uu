import sys
import time # (1) Import time để tránh lỗi nếu có dùng time_limit (dù code này chạy 1 lần)

# --- HÀM HỖ TRỢ ĐỌC DỮ LIỆU ---
def get_iterator(input_content=None):
    if input_content:
        # Chế độ Benchmark: Đọc từ biến truyền vào
        data = input_content.split()
    else:
        # Chế độ Nộp bài: Đọc từ bàn phím/sys.stdin
        try:
            data = sys.stdin.read().split()
        except Exception: return iter([])
        
    return iter(data)

# (2) Thêm tham số time_limit vào hàm solve cho đồng bộ
def solve(input_content=None, time_limit=0.95):
    # --- 1. ĐỌC DỮ LIỆU ---
    iterator = get_iterator(input_content)
    
    try:
        T = int(next(iterator))
        N = int(next(iterator))
        M = int(next(iterator))
    except StopIteration:
        return 0

    class_needs = []
    for _ in range(N):
        curr = []
        while True:
            try:
                v = int(next(iterator))
                if v == 0: break
                curr.append(v)
            except StopIteration: break
        class_needs.append(curr)

    # subject_to_teachers: Lưu danh sách ID giáo viên dạy được môn m
    subject_to_teachers = [[] for _ in range(M + 1)]
    for t_idx in range(1, T + 1):
        while True:
            try:
                v = int(next(iterator))
                if v == 0: break
                if v <= M: subject_to_teachers[v].append(t_idx)
            except StopIteration: break

    durations = [0]
    for _ in range(M):
        try:
            durations.append(int(next(iterator)))
        except StopIteration: 
            durations.append(1) # Default fallback

    # --- 2. TIỀN XỬ LÝ BITMASK ---
    # valid_masks: Lưu các vị trí bắt đầu và mặt nạ bit không nhảy buổi
    valid_masks = [[] for _ in range(13)]
    for d in range(1, 13):
        for start in range(1, 61 - d + 2):
            end = start + d - 1
            if (start - 1) // 6 == (end - 1) // 6: # Ràng buộc cùng buổi
                mask = ((1 << d) - 1) << (start - 1)
                valid_masks[d].append((start, mask))

    # unassigned_tasks: Danh sách các cặp (Lớp, Môn) cần xếp
    unassigned_tasks = []
    for c_idx, needs in enumerate(class_needs, 1):
        for m_id in needs:
            # Check range để tránh lỗi input sai
            if m_id < len(durations):
                unassigned_tasks.append({
                    'c': c_idx, 
                    'm': m_id, 
                    'dur': durations[m_id],
                    'eligible': subject_to_teachers[m_id] if m_id < len(subject_to_teachers) else []
                })

    class_masks = [0] * (N + 1)
    teacher_masks = [0] * (T + 1)
    final_solution = []

    # --- 3. VÒNG LẶP REGRET-BASED GREEDY ---
    while unassigned_tasks:
        best_task_idx = -1
        best_option = None # (start, teacher_id, mask)
        min_options_count = float('inf')
        max_regret_score = -1 # Tiêu chí phụ: Độ ưu tiên nếu options bằng nhau

        # Duyệt tất cả các task còn lại để tìm task "nguy kịch" nhất
        i = 0
        while i < len(unassigned_tasks):
            task = unassigned_tasks[i]
            c_idx = task['c']
            d = task['dur']
            
            # Đếm số lượng lựa chọn (Slot, Teacher) còn lại cho task này
            current_options = []
            c_mask = class_masks[c_idx]
            
            for t_id in task['eligible']:
                t_mask = teacher_masks[t_id]
                combined = c_mask | t_mask
                
                # Kiểm tra va chạm bằng Bitwise AND
                for start, msk in valid_masks[d]:
                    if not (combined & msk):
                        current_options.append((start, t_id, msk))
            
            num_opts = len(current_options)
            
            # Nếu môn này không còn cách nào để xếp, loại bỏ khỏi danh sách (Chấp nhận thất bại task này)
            if num_opts == 0:
                unassigned_tasks.pop(i)
                continue
            
            # Tính điểm ưu tiên bổ sung (Tie-breaker)
            # Ưu tiên môn dài hơn hoặc môn có tổng số giáo viên ít hơn
            regret_score = d * 100 - len(task['eligible'])
            
            # Chiến lược Regret: Chọn môn có ít lựa chọn nhất (Min-Remaining-Values)
            if num_opts < min_options_count:
                min_options_count = num_opts
                max_regret_score = regret_score
                best_task_idx = i
                # Heuristic chọn slot: Chọn slot sớm nhất (First Fit) trong các options
                best_option = current_options[0] 
            elif num_opts == min_options_count:
                if regret_score > max_regret_score:
                    max_regret_score = regret_score
                    best_task_idx = i
                    best_option = current_options[0]
            
            i += 1

        # Thực hiện gán task tốt nhất tìm được
        if best_task_idx != -1:
            task = unassigned_tasks.pop(best_task_idx)
            start, t_id, msk = best_option
            
            class_masks[task['c']] |= msk
            teacher_masks[t_id] |= msk
            
            final_solution.append((task['c'], task['m'], start, t_id))
        else:
            break

    # --- 4. XUẤT KẾT QUẢ ---
    # Chỉ in ra màn hình nếu đang ở chế độ Nộp bài (input_content is None)
    if input_content is None:
        print(len(final_solution))
        final_solution.sort(key=lambda x: (x[0], x[1]))
        for res in final_solution:
            print(f"{res[0]} {res[1]} {res[2]} {res[3]}")

    # QUAN TRỌNG: Trả về kết quả để Benchmark Runner ghi nhận
    return len(final_solution)

if __name__ == "__main__":
    solve()