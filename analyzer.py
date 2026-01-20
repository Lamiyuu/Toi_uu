import sys
import os
import statistics
from io import StringIO
# Import hàm tiền xử lý từ file utils.py cũ
from utils import load_and_preprocess, MAX_SLOTS

# Cấu hình folder chứa test case
INPUT_FOLDER = "test_case"  # <-- Đặt tên folder chứa test case của bạn ở đây

def analyze_single_file(file_path, file_name):
    """Phân tích một file và trả về các chỉ số"""
    
    # 1. Đọc nội dung file và giả lập stdin
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Mock sys.stdin để tái sử dụng hàm load_and_preprocess cũ
        sys.stdin = StringIO(content)
        data = load_and_preprocess()
        
        if data is None:
            return None
            
        T, N, tasks = data['T'], data['N'], data['tasks']
        
        # --- TÍNH TOÁN CHỈ SỐ ---
        
        # 1. Tải của Lớp (Class Load)
        class_loads = [0] * N
        for t in tasks:
            class_loads[t['c']] += t['d']
        max_c_load = max(class_loads)
        class_load_percent = (max_c_load / MAX_SLOTS) * 100
        
        # 2. Độ khan hiếm Giáo viên (Teacher Scarcity)
        # Tỷ lệ số task chỉ có đúng 1 giáo viên dạy được
        strict_tasks = sum(1 for t in tasks if t['num_eligible'] == 1)
        scarcity_percent = (strict_tasks / len(tasks)) * 100 if tasks else 0
        
        # 3. Môn học dài (Duration)
        max_duration = max(t['d'] for t in tasks) if tasks else 0
        
        # --- ĐÁNH GIÁ ĐỘ KHÓ ---
        difficulty = "EASY"
        reason = "Resource Open"
        
        # Logic xếp hạng Hard/Medium/Easy
        if class_load_percent > 90:
            difficulty = "HARD"
            reason = "Full Class Schedule"
        elif scarcity_percent > 50:
            difficulty = "HARD"
            reason = "Lack Teachers"
        elif class_load_percent > 75 or scarcity_percent > 20:
            difficulty = "MEDIUM"
            reason = "Constrained"
            
        return {
            "name": file_name,
            "N": N,
            "T": T,
            "Tasks": len(tasks),
            "MaxClassLoad": f"{max_c_load} ({class_load_percent:.0f}%)",
            "TeacherScarcity": f"{scarcity_percent:.0f}%",
            "MaxDur": max_duration,
            "Difficulty": difficulty,
            "Reason": reason
        }

    except Exception as e:
        print(f"Lỗi khi đọc file {file_name}: {e}")
        return None

def main():
    # Kiểm tra folder tồn tại không
    if not os.path.exists(INPUT_FOLDER):
        print(f"Lỗi: Folder '{INPUT_FOLDER}' không tồn tại. Hãy tạo folder và bỏ file txt vào.")
        return

    # Lấy danh sách file .txt
    files = sorted([f for f in os.listdir(INPUT_FOLDER) if f.endswith(".txt")])
    
    if not files:
        print(f"Không tìm thấy file .txt nào trong folder '{INPUT_FOLDER}'")
        return

    print(f"Đang phân tích {len(files)} file trong folder '{INPUT_FOLDER}'...\n")
    
    results = []
    
    # Header bảng
    header = f"{'FILE NAME':<15} | {'N':<4} {'T':<4} {'TASKS':<6} | {'CLASS LOAD':<12} | {'SCARCITY':<10} | {'RANK':<8} | {'REASON'}"
    print("-" * 90)
    print(header)
    print("-" * 90)

    for file_name in files:
        file_path = os.path.join(INPUT_FOLDER, file_name)
        res = analyze_single_file(file_path, file_name)
        
        if res:
            results.append(res)
            # In từng dòng kết quả
            print(f"{res['name']:<15} | {res['N']:<4} {res['T']:<4} {res['Tasks']:<6} | {res['MaxClassLoad']:<12} | {res['TeacherScarcity']:<10} | {res['Difficulty']:<8} | {res['Reason']}")

    print("-" * 90)
    
    # Thống kê nhanh
    hard_count = sum(1 for r in results if r['Difficulty'] == 'HARD')
    print(f"\nTỔNG KẾT: {len(results)} files.")
    print(f"- Số lượng HARD: {hard_count} (Cần SA/Tabu/ILP)")
    print(f"- Số lượng MEDIUM/EASY: {len(results) - hard_count} (GA/Greedy là đủ)")

if __name__ == "__main__":
    main()