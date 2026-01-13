import random
import os

def generate_valid_dataset(filename, T, N, M):
    """
    T: Số giáo viên
    N: Số lớp
    M: Số môn học
    """
    with open(filename, 'w') as f:
        # 1. HEADER
        f.write(f"{T} {N} {M}\n")
        
        # --- SINH DỮ LIỆU LOGIC ---
        
        # Bước 1: Sinh thời lượng cho M môn (1 đến 4 tiết)
        # Tỉ lệ: 10% môn 4 tiết, 20% môn 3 tiết, còn lại 1-2 tiết (cho dễ xếp)
        durations = []
        for _ in range(M):
            r = random.random()
            if r < 0.1: dur = 4
            elif r < 0.3: dur = 3
            elif r < 0.7: dur = 2
            else: dur = 1
            durations.append(str(dur))

        # Bước 2: Phân công chuyên môn cho Giáo viên
        # Đảm bảo mỗi môn học đều có ÍT NHẤT 1 giáo viên dạy
        teacher_skills = [set() for _ in range(T)]
        
        # Gán mỗi môn cho 1 giáo viên ngẫu nhiên trước (để đảm bảo không môn nào bị bỏ rơi)
        for m_id in range(1, M + 1):
            t_idx = random.randint(0, T - 1)
            teacher_skills[t_idx].add(m_id)
            
        # Sau đó random thêm kỹ năng cho giáo viên (mỗi GV dạy khoảng 2-5 môn)
        for t_idx in range(T):
            num_extra = random.randint(1, 5)
            for _ in range(num_extra):
                m_id = random.randint(1, M)
                teacher_skills[t_idx].add(m_id)

        # Bước 3: Sinh nhu cầu học cho từng Lớp
        # Mỗi lớp học khoảng 5-10 môn
        class_courses = []
        for _ in range(N):
            num_subjects = random.randint(5, 10) 
            # Chọn ngẫu nhiên các môn (không trùng lặp trong 1 lớp)
            subjects = random.sample(range(1, M + 1), min(num_subjects, M))
            class_courses.append(subjects)

        # --- GHI FILE THEO ĐÚNG ĐỊNH DẠNG ---
        
        # 2. Ghi Classes (Kết thúc bằng 0)
        for courses in class_courses:
            line = " ".join(map(str, courses)) + " 0\n"
            f.write(line)
            
        # 3. Ghi Teachers (Kết thúc bằng 0)
        for skills in teacher_skills:
            # Nếu giáo viên không dạy môn nào (hiếm), vẫn phải ghi số 0
            if not skills:
                f.write("0\n")
            else:
                line = " ".join(map(str, skills)) + " 0\n"
                f.write(line)
        
        # 4. Ghi Durations
        f.write(" ".join(durations))

# --- CẤU HÌNH BỘ TEST ---
# Tạo thư mục data nếu chưa có
if not os.path.exists("data"):
    os.makedirs("data")

print("Đang sinh dữ liệu...")

# Bộ 1: Nhỏ (Dễ test nhanh)
generate_valid_dataset("data/input_small.txt", T=5, N=10, M=10)
print("- Đã tạo input_small.txt (10 lớp)")

# Bộ 2: Vừa (Tương đương đề bài mẫu)
generate_valid_dataset("data/input_medium.txt", T=20, N=50, M=30)
print("- Đã tạo input_medium.txt (50 lớp)")

# Bộ 3: Lớn (Stress test thuật toán)
generate_valid_dataset("data/input_large.txt", T=50, N=200, M=100)
print("- Đã tạo input_large.txt (200 lớp)")

print("Hoàn tất! Hãy dùng các file trong thư mục 'data/' để chạy Benchmark.")