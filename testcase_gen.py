import random
import os

def generate_testcase(filename, T, N, M, density, scarcity, mode='normal'):
    """
    Sinh test case ép xung để đạt ngưỡng HARD của analyzer.py
    
    Args:
        density (0.0 - 1.0): 
            - Đặt > 0.92 để ép ra HARD (Full Class Schedule).
            - Đặt 0.78 - 0.85 để ra MEDIUM.
        scarcity (0.0 - 1.0): 
            - Đặt > 0.95 để ép ra HARD (Lack Teachers - Hầu hết môn chỉ có 1 GV).
            - Đặt 0.6 - 0.8 để ra MEDIUM.
    """
    
    MAX_SLOTS = 60
    
    # --- 1. SINH THỜI LƯỢNG (DURATIONS) ---
    durations = []
    for _ in range(M):
        if mode == 'stress':
            # Chế độ Stress: Tăng môn 3, 4 tiết để khó xếp slot
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

    # --- 2. SINH NHU CẦU LỚP HỌC (CLASS REQUIREMENTS) ---
    class_courses = []
    target_load = int(MAX_SLOTS * density) 
    
    for _ in range(N):
        current_load = 0
        courses = set()
        attempts = 0
        
        # Cố gắng nhồi môn đến khi đạt target density
        # Tăng số attempts để đảm bảo đạt được độ đặc mong muốn
        while current_load < target_load and attempts < 1000:
            m_id = random.randint(1, M)
            if m_id not in courses:
                d = durations[m_id-1]
                # Nếu density yêu cầu cao (>90%), cho phép nhồi gần full
                if current_load + d <= MAX_SLOTS:
                    courses.add(m_id)
                    current_load += d
            attempts += 1
        class_courses.append(list(courses))

    # --- 3. SINH KỸ NĂNG GIÁO VIÊN ---
    teacher_abilities = [set() for _ in range(T)]
    
    # Tính xác suất GV biết môn.
    # Nếu scarcity cực cao (Hard), prob_know phải cực thấp
    prob_know = 1.0 - scarcity
    
    # Nếu muốn Hard Scarcity (>50% task có 1 GV), prob_know phải gần như bằng 0
    # để logic "lucky_teacher" bên dưới chịu trách nhiệm chính.
    if scarcity > 0.9: 
        prob_know = 0.01 
    elif prob_know < 0.05: 
        prob_know = 0.05
    
    for t in range(T):
        for m in range(1, M + 1):
            if random.random() < prob_know:
                teacher_abilities[t].add(m)

    # Đảm bảo môn nào cũng có người dạy
    for m in range(1, M + 1):
        # Kiểm tra xem môn này đã có ai dạy chưa
        count = sum(1 for t in range(T) if m in teacher_abilities[t])
        
        # Nếu chưa có ai HOẶC (Scarcity cao VÀ số người dạy < 1), gán cho đúng 1 người
        if count == 0:
            lucky_teacher = random.randint(0, T - 1)
            teacher_abilities[lucky_teacher].add(m)

    # Đảm bảo ai cũng có việc (để tránh lãng phí T)
    for t in range(T):
        if not teacher_abilities[t]:
            random_subject = random.randint(1, M)
            teacher_abilities[t].add(random_subject)

    # --- 4. GHI FILE ---
    output_folder = "test_case" # Sửa lại tên folder cho khớp với analyzer của bạn
    os.makedirs(output_folder, exist_ok=True)
    full_path = os.path.join(output_folder, filename)
    
    with open(full_path, 'w') as f:
        f.write(f"{T} {N} {M}\n")
        for courses in class_courses:
            f.write(" ".join(map(str, courses)) + " 0\n")
        for abilities in teacher_abilities:
            f.write(" ".join(map(str, abilities)) + " 0\n")
        f.write(" ".join(map(str, durations)) + "\n")
        
    print(f"Gen: {filename:<25} | Density={density} | Scarcity={scarcity}")

# =========================================================
# CẤU HÌNH ĐỂ ĐẠT MEDIUM / HARD TRÊN ANALYZER
# =========================================================

if __name__ == "__main__":
    print("-" * 60)
    print("SINH 6 TEST CASE (1 MEDIUM - 1 HARD CHO MỖI CẶP)")
    print("-" * 60)

    # --- CẶP 1: TEST NHỎ (T=5, 10) ---
    
    # 1.1. Medium (T=5)
    # Density 0.8 -> Class Load ~80% (>75% -> MEDIUM)
    generate_testcase(
        "01_small_medium.txt",
        T=5, N=10, M=15,
        density=0.8, scarcity=0.3, mode='normal'
    )

    # 1.2. Hard (T=10)
    # Density 0.96 -> Class Load > 90% (-> HARD: Full Class Schedule)
    generate_testcase(
        "02_small_hard.txt",
        T=10, N=20, M=25,
        density=0.96, scarcity=0.4, mode='stress'
    )

    print("-" * 30)

    # --- CẶP 2: TEST VỪA (T=20, 25) ---
    
    # 2.1. Medium (T=20)
    # Scarcity 0.4 -> ~30-40% task hiếm (>20% -> MEDIUM)
    # Density 0.75 -> Mấp mé Medium
    generate_testcase(
        "03_medium_medium.txt",
        T=20, N=40, M=40,
        density=0.75, scarcity=0.4, mode='normal'
    )

    # 2.2. Hard (T=25)
    # Scarcity 0.98 -> Ép hầu hết môn chỉ có 1 GV (>50% -> HARD: Lack Teachers)
    generate_testcase(
        "04_medium_hard.txt",
        T=25, N=50, M=50,
        density=0.6, scarcity=0.98, mode='normal'
    )

    print("-" * 30)

    # --- CẶP 3: TEST LỚN (T=50) ---
    
    # 3.1. Medium (T=50)
    # Density 0.82 -> Class Load > 75% (-> MEDIUM)
    generate_testcase(
        "05_large_medium.txt",
        T=50, N=100, M=80,
        density=0.82, scarcity=0.2, mode='normal'
    )

    # 3.2. Hard (T=50) - Nightmare
    # Density 0.95 (HARD) VÀ Scarcity 0.95 (HARD) -> Double HARD
    generate_testcase(
        "06_large_hard.txt",
        T=50, N=120, M=100,
        density=0.95, scarcity=0.95, mode='stress'
    )

    print("-" * 60)
    print("Xong! Hãy chạy lại 'analyzer_folder.py' để kiểm tra Rank.")