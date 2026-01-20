import random
import os

def generate_hard_testcase(filename, T, N, M, density=0.6, scarcity=0.8):
    """
    Sinh test case khó với nhiều cực tiểu địa phương.
    
    Args:
        filename: Đường dẫn file output.
        T: Số giáo viên.
        N: Số lớp học.
        M: Số môn học.
        density (0.0 - 1.0): Độ "đặc" của lịch học. Càng cao, lớp càng phải học nhiều môn.
        scarcity (0.0 - 1.0): Độ "hiếm" giáo viên. Càng cao, giáo viên càng ít đa năng (chuyên môn hóa hẹp).
    """
    
    # ---------------------------------------------------------
    # BƯỚC 1: SINH THỜI LƯỢNG (DURATIONS) - GÂY KHÓ XẾP
    # ---------------------------------------------------------
    # Thay vì random đều, ta ưu tiên môn 3 và 4 tiết. 
    # Lý do: Buổi học có 6 tiết. 
    # - Môn 3 tiết: Cần đúng 1/2 buổi.
    # - Môn 4 tiết: Cực khó chịu, vì dư 2 tiết chỉ nhét được môn ngắn.
    weights = [0.1, 0.1, 0.4, 0.4] # Tỉ lệ cho 1, 2, 3, 4 tiết
    duration_values = random.choices([1, 2, 3, 4], weights=weights, k=M)
    durations = {m: d for m, d in zip(range(1, M+1), duration_values)}

    # ---------------------------------------------------------
    # BƯỚC 2: SINH KỸ NĂNG GIÁO VIÊN (TEACHERS) - NÚT THẮT CỔ CHAI
    # ---------------------------------------------------------
    teacher_skills = [set() for _ in range(T)]
    
    # [QUAN TRỌNG] Đảm bảo tính khả thi: Mỗi môn phải có ít nhất 1 GV dạy
    # Phân đều mỗi môn cho 1 GV ngẫu nhiên trước
    all_subjects = list(range(1, M + 1))
    random.shuffle(all_subjects)
    
    for m_id in all_subjects:
        t_idx = random.randint(0, T - 1)
        teacher_skills[t_idx].add(m_id)
        
    # Sau đó phân thêm kỹ năng dựa trên độ khan hiếm (scarcity)
    # Scarcity cao -> GV biết ít môn -> Khó xếp
    avg_skills_per_teacher = max(1, int(M * (1 - scarcity))) 
    
    for t_idx in range(T):
        # Số môn GV này có thể dạy thêm (ngẫu nhiên quanh mức trung bình)
        num_extra = random.randint(0, avg_skills_per_teacher)
        potential_subjects = random.sample(range(1, M+1), min(num_extra, M))
        teacher_skills[t_idx].update(potential_subjects)

    # ---------------------------------------------------------
    # BƯỚC 3: SINH NHU CẦU LỚP HỌC (CLASSES) - MẬT ĐỘ CAO
    # ---------------------------------------------------------
    class_requirements = []
    
    # Số môn trung bình mỗi lớp phải học
    avg_subjects_per_class = int(M * density)
    if avg_subjects_per_class < 1: avg_subjects_per_class = 1
    
    for _ in range(N):
        # Biến thiên số lượng môn học để không lớp nào giống lớp nào
        num_subs = random.randint(avg_subjects_per_class - 2, avg_subjects_per_class + 2)
        num_subs = max(1, min(num_subs, M)) # Clamp trong khoảng [1, M]
        
        # Chọn môn học ngẫu nhiên
        reqs = random.sample(range(1, M+1), num_subs)
        class_requirements.append(reqs)

    # ---------------------------------------------------------
    # BƯỚC 4: GHI FILE THEO FORMAT ĐỀ BÀI
    # ---------------------------------------------------------
    with open(filename, 'w') as f:
        # Header
        f.write(f"{T} {N} {M}\n")
        
        # Danh sách môn lớp cần học
        for reqs in class_requirements:
            line = " ".join(map(str, reqs)) + " 0\n"
            f.write(line)
            
        # Danh sách môn GV có thể dạy
        for skills in teacher_skills:
            if not skills: # Phòng hờ (dù logic trên đã chặn)
                f.write("0\n")
            else:
                line = " ".join(map(str, skills)) + " 0\n"
                f.write(line)
                
        # Thời lượng môn học
        d_str = [str(durations[m]) for m in range(1, M+1)]
        f.write(" ".join(d_str))
        
    print(f"✅ Đã tạo: {filename} | T={T}, N={N}, M={M}")

# =========================================================
# CHẠY SINH DỮ LIỆU
# =========================================================

if not os.path.exists("datasets"):
    os.makedirs("datasets")

print("--- BẮT ĐẦU SINH TEST CASE ---")

# 1. Test nhỏ: Kiểm tra tính đúng đắn (Sanity Check)
generate_hard_testcase(
    "datasets/test_small.txt", 
    T=5, N=5, M=10, 
    density=0.4, scarcity=0.5
)

# 2. Test vừa: Mô phỏng bài toán thực tế (Standard)
# density=0.3: Mỗi lớp học khoảng 30% tổng số môn (khoảng 9-10 môn)
# scarcity=0.8: Giáo viên khá chuyên biệt (chỉ dạy được ít môn)
generate_hard_testcase(
    "datasets/test_medium.txt", 
    T=15, N=30, M=30, 
    density=0.3, scarcity=0.8
)

# 3. Test LỚN & KHÓ (Stress Test) - Dùng để đánh giá hiệu năng & tối ưu
# 50 GV, 100 Lớp, 50 Môn.
# Nhiều môn 3,4 tiết. GV rất ít. Lớp học nhiều.
generate_hard_testcase(
    "datasets/test_large_hard.txt", 
    T=50, N=100, M=50, 
    density=0.25, scarcity=0.85 
)

print("\nĐã xong! Kiểm tra thư mục 'datasets/'.")

generate_hard_testcase(
    "datasets/test_supper_large_hard.txt", 
    T=100, N=400, M=60, 
    density=0.25, scarcity=0.85 
)

print("\nĐã xong! Kiểm tra thư mục 'datasets/'.")