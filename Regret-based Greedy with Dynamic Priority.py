import sys

def solve():
    # --- 1. ĐỌC DỮ LIỆU ---
    input_data = sys.stdin.read().split()
    if not input_data: return
    ptr = 0
    
    T = int(input_data[ptr]); ptr += 1
    N = int(input_data[ptr]); ptr += 1
    M = int(input_data[ptr]); ptr += 1

    class_needs = []
    for _ in range(N):
        curr = []
        while True:
            v = int(input_data[ptr]); ptr += 1
            if v == 0: break
            curr.append(v)
        class_needs.append(curr)

    # subject_to_teachers: Lưu danh sách ID giáo viên dạy được môn m
    subject_to_teachers = [[] for _ in range(M + 1)]
    for t_idx in range(1, T + 1):
        while True:
            v = int(input_data[ptr]); ptr += 1
            if v == 0: break
            if v <= M: subject_to_teachers[v].append(t_idx)

    durations = [0] + [int(x) for x in input_data[ptr:ptr+M]]

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
            unassigned_tasks.append({
                'c': c_idx, 
                'm': m_id, 
                'dur': durations[m_id],
                'eligible': subject_to_teachers[m_id]
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
                
                for start, msk in valid_masks[d]:
                    if not (combined & msk):
                        current_options.append((start, t_id, msk))
            
            num_opts = len(current_options)
            
            # Nếu môn này không còn cách nào để xếp, loại bỏ khỏi danh sách
            if num_opts == 0:
                unassigned_tasks.pop(i)
                continue
            
            # Tính điểm ưu tiên bổ sung (Tie-breaker)
            # Ưu tiên môn dài hơn hoặc môn có tổng số giáo viên ít hơn
            regret_score = d * 100 - len(task['eligible'])
            
            # Chiến lược Regret: Chọn môn có ít lựa chọn nhất
            if num_opts < min_options_count:
                min_options_count = num_opts
                max_regret_score = regret_score
                best_task_idx = i
                best_option = current_options[0] # Chọn slot rảnh sớm nhất
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
    print(len(final_solution))
    # Sắp xếp theo Class ID và Subject ID để khớp với yêu cầu format
    final_solution.sort(key=lambda x: (x[0], x[1]))
    for res in final_solution:
        print(f"{res[0]} {res[1]} {res[2]} {res[3]}")

if __name__ == "__main__":
    solve()