import time
import numpy as np
import pandas as pd
import os
import importlib.util
import inspect

# --- 1. CẤU HÌNH BENCHMARK ---

# Danh sách các file code thuật toán
ALGORITHMS = {
    "greedy_heuristic_test": "Greedy Constructive",
    "greedy_time_test": "Randomized Greedy",
    "local_search_test": "Local Search",
    "regret_based_test": "Regret-Based",
    "sa_test": "Simulated Annealing",
    "ga_test": "Genetic Algorithm"
}

# --- CẬP NHẬT DANH SÁCH FILE TEST TẠI ĐÂY ---
TEST_FILES = [
    "datasets/test_small.txt",
    "datasets/test_medium.txt", 
    "datasets/test_large_hard.txt",
    "datasets/test_supper_large_hard.txt"  # ✅ Đã thêm file mới (Lưu ý: Để file này vào thư mục data)
]

# Cấu hình các chế độ test
TEST_MODES = [
    {"label": "Limit 1 Min", "time_limit": 60.0},  # Giới hạn 60 giây
    {"label": "No Limit",    "time_limit": None}    # Chạy tự do (tối đa hiệu năng)
]

# Số lần chạy lại mỗi thuật toán
NUM_RUNS = 3 

# --- 2. HÀM HỖ TRỢ ---

def load_solver(module_name):
    """Nạp hàm solve() từ file .py"""
    file_path = f"{module_name}.py"
    if not os.path.exists(file_path):
        return None
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, "solve"):
            return module.solve
        else:
            print(f"⚠️  Cảnh báo: File '{file_path}' không có hàm 'solve'")
            return None
    except Exception as e:
        print(f"❌ Lỗi khi nạp file '{file_path}': {e}")
        return None

def call_solver_safe(func, input_content, limit):
    """
    Gọi hàm solve an toàn.
    - Nếu limit có giá trị: cố gắng truyền time_limit.
    - Nếu limit là None: gọi hàm không tham số time_limit.
    """
    try:
        sig = inspect.signature(func)
        
        # Trường hợp 1: Có giới hạn thời gian và hàm chấp nhận tham số đó
        if limit is not None and 'time_limit' in sig.parameters:
            return func(input_content, time_limit=limit)
        
        # Trường hợp 2: Chế độ không giới hạn (None) HOẶC hàm không hỗ trợ time_limit
        else:
            return func(input_content)
            
    except Exception as e:
        return 0

# --- 3. CHƯƠNG TRÌNH CHÍNH ---

def run_benchmark():
    # Kiểm tra thư mục data
    valid_data_files = []
    print(f"{'='*70}")
    print("📂 KIỂM TRA DỮ LIỆU INPUT...")
    for f in TEST_FILES:
        if os.path.exists(f):
            valid_data_files.append(f)
        else:
            print(f"⚠️  Không tìm thấy file: {f} (Vui lòng kiểm tra đường dẫn)")
            
    if not valid_data_files:
        print("❌ LỖI: Không tìm thấy file dữ liệu nào hợp lệ.")
        return

    # Nạp các thuật toán
    solvers = {}
    print(f"\n📦 ĐANG NẠP CÁC THUẬT TOÁN...")
    for filename, display_name in ALGORITHMS.items():
        solver_func = load_solver(filename)
        if solver_func:
            solvers[display_name] = solver_func
            print(f"   ✅ Đã nạp: {display_name:<25} ({filename}.py)")
        else:
            print(f"   ⚠️  Bỏ qua:  {filename}.py (Không tìm thấy)")
    print(f"{'='*70}\n")

    if not solvers:
        print("❌ LỖI: Không tìm thấy bất kỳ thuật toán nào.")
        return

    results = []
    
    print(f"🚀 BẮT ĐẦU CHẠY BENCHMARK...")
    print(f"👉 Chế độ: {[mode['label'] for mode in TEST_MODES]}")
    
    for filepath in valid_data_files:
        filename = os.path.basename(filepath)
        print(f"\n📂 Dataset: {filename}")
        
        # Đọc nội dung file input
        try:
            with open(filepath, 'r') as f:
                input_content = f.read()
        except Exception as e:
            print(f"❌ Lỗi đọc file {filename}: {e}")
            continue
            
        # Vòng lặp qua các chế độ test (1 phút vs No Limit)
        for mode in TEST_MODES:
            t_label = mode["label"]
            t_limit = mode["time_limit"]
            
            print(f"   ⏱️  Mode: {t_label}")
            print("-" * 70)
            
            row = {
                "Dataset": filename,
                "Mode": t_label
            }
            
            for name, solve_func in solvers.items():
                scores = []
                times = []
                
                # Chạy lặp lại NUM_RUNS lần
                for i in range(NUM_RUNS):
                    start = time.time()
                    
                    # Gọi hàm giải
                    score = call_solver_safe(solve_func, input_content, t_limit)
                    
                    end = time.time()
                    
                    scores.append(score)
                    times.append(end - start)
                
                # Tính thống kê
                mean_score = np.mean(scores)
                std_score = np.std(scores)
                mean_time = np.mean(times)
                
                # Format kết quả Score: "Mean (Std)"
                if std_score == 0:
                    res_str = f"{mean_score:.0f}"
                else:
                    res_str = f"{mean_score:.1f} ({std_score:.1f})"
                
                row[name] = res_str
                
                # In ra tiến độ
                print(f"      🔹 {name:<20}: Score = {res_str:<15} | Time avg: {mean_time:.2f}s")

            results.append(row)

    # --- 4. XUẤT KẾT QUẢ ---
    if not results:
        print("\n❌ Không có kết quả nào được ghi nhận.")
        return

    df = pd.DataFrame(results)
    
    # Sắp xếp cột cho đẹp
    first_cols = ["Dataset", "Mode"]
    other_cols = [c for c in df.columns if c not in first_cols]
    df = df[first_cols + other_cols]
    
    print("\n" + "="*90)
    print("🏆 BẢNG TỔNG HỢP KẾT QUẢ (Mean & Std Dev)")
    print("="*90)
    
    try:
        print(df.to_markdown(index=False)) 
    except:
        print(df.to_string(index=False))
        
    print("="*90)
    
    # Lưu ra file CSV
    output_file = "benchmark_final_result.csv"
    df.to_csv(output_file, index=False)
    print(f"✅ Đã lưu kết quả chi tiết vào '{output_file}'")

if __name__ == "__main__":
    run_benchmark()