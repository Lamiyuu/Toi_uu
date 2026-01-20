import random
import os

def generate_testcase(filename, T, N, M, density, scarcity, mode='normal'):
    """
    Sinh test case với thuật toán gán giáo viên mới để đảm bảo Scarcity > 0.
    
    Args:
        scarcity (0.0 - 1.0): Tỷ lệ phần trăm số môn CHỈ CÓ 1 GV dạy.
            - 0.3 -> Analyzer sẽ báo Scarcity ~30%
            - 0.9 -> Analyzer sẽ báo Scarcity ~90%
    """
    
    MAX_SLOTS = 60
    
    # --- 1. SINH THỜI LƯỢNG (DURATIONS) ---
    durations = []
    for _ in range(M):
        if mode == 'stress':
            r = random.random()
            if r < 0.05: d = 1
            elif r < 0.25: d = 2
            elif r < 0.55: d = 3
            else: d = 4 
        else:
            r = random.random()
            if r < 0.1: d = 1
            elif r < 0.4: d = 2
            elif r < 0.8: d = 3
            else: d = 4
        durations.append(d)

    # --- 2. SINH NHU CẦU LỚP HỌC ---
    class_courses = []
    target_load = int(MAX_SLOTS * density) 
    
    for _ in range(N):
        current_load = 0
        courses = set()
        attempts = 0
        while current_load < target_load and attempts < 1000:
            m_id = random.randint(1, M)
            if m_id not in courses:
                d = durations[m_id-1]
                if current_load + d <= MAX_SLOTS:
                    courses.add(m_id)
                    current_load += d
            attempts += 1
        class_courses.append(list(courses))

    # --- 3. SINH KỸ NĂNG GIÁO VIÊN (THUẬT TOÁN MỚI) ---
    # Thay vì duyệt Teacher -> Subject (cũ), ta duyệt Subject -> Teacher
    teacher_abilities = [set() for _ in range(T)]
    
    all_teachers = list(range(T))
    
    for m in range(1, M + 1):
        # Quyết định xem môn này có bao nhiêu GV dạy dựa trên scarcity
        is_strict = random.random() < scarcity
        
        if is_strict:
            # Môn hiếm: Chỉ gán cho ĐÚNG 1 giáo viên ngẫu nhiên
            num_teachers = 1
        else:
            # Môn phổ thông: Gán cho 2 đến (T/3) giáo viên
            # Đảm bảo ít nhất 2 người để không bị tính là Scarcity
            max_t = max(2, int(T * 0.4)) 
            num_teachers = random.randint(2, max_t)
            # Giới hạn trần để không quá dễ
            if num_teachers > 5: num_teachers = 5
            if num_teachers > T: num_teachers = T

        # Chọn ngẫu nhiên num_teachers người để dạy môn m
        assigned_teachers = random.sample(all_teachers, num_teachers)
        
        for t_idx in assigned_teachers:
            teacher_abilities[t_idx].add(m)

    # Fix: Đảm bảo không có giáo viên nào thất nghiệp (Teacher abilities rỗng)
    # Nếu rỗng, gán đại cho 1 môn (có thể làm giảm nhẹ scarcity nhưng không đáng kể)
    for t in range(T):
        if not teacher_abilities[t]:
            # Chọn môn ngẫu nhiên, ưu tiên môn đang không phải là strict (nếu được)
            m = random.randint(1, M)
            teacher_abilities[t].add(m)

    # --- 4. GHI FILE ---
    output_folder = "test_case"
    os.makedirs(output_folder, exist_ok=True)
    full_path = os.path.join(output_folder, filename)
    
    with open(full_path, 'w') as f:
        f.write(f"{T} {N} {M}\n")
        for courses in class_courses:
            f.write(" ".join(map(str, courses)) + " 0\n")
        for abilities in teacher_abilities:
            f.write(" ".join(map(str, abilities)) + " 0\n")
        f.write(" ".join(map(str, durations)) + "\n")
        
    print(f"Gen: {filename:<25} | Density={density} | Scarcity (Target)={scarcity}")


if __name__ == "__main__":
    print("-" * 60)
    print("SINH LẠI 6 TEST CASE VỚI LOGIC SCARCITY MỚI")
    print("-" * 60)

    # --- CẶP 1: TEST NHỎ (T=5, 10) ---
    
    # 01. Medium (T=5)
    # Scarcity 0.3 -> Analyzer sẽ báo khoảng 30% (khác 0)
    generate_testcase(
        "01_small_medium.txt",
        T=5, N=10, M=15,
        density=0.8, scarcity=0.3, mode='normal'
    )

    # 02. Hard (T=10) - Full Class Schedule
    # Density cao (Hard), Scarcity thấp (0.1) để tập trung khó vào Lịch học
    generate_testcase(
        "02_small_hard.txt",
        T=10, N=20, M=25,
        density=0.96, scarcity=0.2, mode='stress'
    )

    print("-" * 30)

    # --- CẶP 2: TEST VỪA (T=20, 25) ---
    
    # 03. Medium (T=20)
    # Scarcity 0.3 -> Đảm bảo Analyzer hiện ~30%
    generate_testcase(
        "03_medium_medium.txt",
        T=20, N=40, M=40,
        density=0.75, scarcity=0.3, mode='normal'
    )

    # 04. Hard (T=25) - Lack Teachers
    # Scarcity 0.9 -> Analyzer hiện ~90% (HARD)
    generate_testcase(
        "04_medium_hard.txt",
        T=25, N=50, M=50,
        density=0.6, scarcity=0.9, mode='normal'
    )

    print("-" * 30)

    # --- CẶP 3: TEST LỚN (T=50) ---
    
    # 05. Medium (T=50)
    # Scarcity 0.25 -> Analyzer hiện ~25% (khác 0)
    generate_testcase(
        "05_large_medium.txt",
        T=50, N=100, M=80,
        density=0.82, scarcity=0.25, mode='normal'
    )

    # 06. Hard (T=50) - Nightmare
    # Scarcity 0.85 -> Analyzer hiện ~85%
    generate_testcase(
        "06_large_hard.txt",
        T=50, N=120, M=100,
        density=0.95, scarcity=0.85, mode='stress'
    )

    print("-" * 60)
    print("Xong! Chạy lại 'analyzer_folder.py' để thấy Scarcity > 0%.")