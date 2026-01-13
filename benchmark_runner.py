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

# Danh sách file dữ liệu test
TEST_FILES = [
    "data/input_small.txt",
    "data/input_medium.txt", 
    "data/input_large.txt"
]

# Các mốc thời gian giới hạn cần test (Giây)
TIME_CONFIGS = [1.0, 2.0] 

# Số lần chạy lại mỗi thuật toán
NUM_RUNS = 5 

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
    """Gọi hàm solve an toàn, kiểm tra xem nó có nhận time_limit không"""
    try:
        sig = inspect.signature(func)
        if 'time_limit' in sig.parameters:
            return func(input_content, time_limit=limit)
        else:
            # Nếu hàm không có tham số time_limit (như Greedy thuần), gọi bình thường
            return func(input_content)
    except Exception as e:
        # print(f"Lỗi runtime: {e}") 
        return 0

# --- 3. CHƯƠNG TRÌNH CHÍNH ---

def run_benchmark():
    # Kiểm tra thư mục data
    valid_data_files = [f for f in TEST_FILES if os.path.exists(f)]
    if not valid_data_files:
        print("❌ LỖI: Không tìm thấy file dữ liệu nào trong thư mục 'data/'.")
        return

    # Nạp các thuật toán
    solvers = {}
    print(f"{'='*70}")
    print(f"📦 ĐANG NẠP CÁC THUẬT TOÁN...")
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
    
    print(f"🚀 BẮT ĐẦU CHẠY BENCHMARK ({NUM_RUNS} lần x {len(TIME_CONFIGS)} cấu hình)...")
    
    for filepath in valid_data_files:
        filename = os.path.basename(filepath)
        print(f"\n📂 Dataset: {filename}")
        
        # Đọc nội dung file input
        with open(filepath, 'r') as f:
            input_content = f.read()
            
        # Vòng lặp qua các mốc thời gian (1s, 2s)
        for t_limit in TIME_CONFIGS:
            t_label = f"{int(t_limit * 1000)}ms"
            print(f"   ⏱️  Time Limit: {t_label}")
            print("-" * 70)
            
            row = {
                "Dataset": filename,
                "Time Limit": t_label
            }
            
            for name, solve_func in solvers.items():
                scores = []
                times = []
                
                # Chạy lặp lại NUM_RUNS lần
                for i in range(NUM_RUNS):
                    start = time.time()
                    
                    # Gọi hàm giải với giới hạn thời gian
                    score = call_solver_safe(solve_func, input_content, t_limit)
                    
                    end = time.time()
                    
                    scores.append(score)
                    times.append(end - start)
                
                # Tính thống kê
                mean_score = np.mean(scores)
                std_score = np.std(scores)
                
                # Format kết quả: "Mean (Std)"
                if std_score == 0:
                    res_str = f"{mean_score:.0f}"
                else:
                    res_str = f"{mean_score:.1f} ({std_score:.1f})"
                
                row[name] = res_str
                
                # In ra màn hình để theo dõi
                # print(f"      🔹 {name:<25}: Score = {res_str}")

            results.append(row)

    # --- 4. XUẤT KẾT QUẢ ---
    df = pd.DataFrame(results)
    
    # Sắp xếp cột cho đẹp: Dataset -> Time Limit -> Các thuật toán
    cols = ["Dataset", "Time Limit"] + [c for c in df.columns if c not in ["Dataset", "Time Limit"]]
    df = df[cols]
    
    print("\n" + "="*90)
    print("🏆 BẢNG TỔNG HỢP KẾT QUẢ (Mean & Std Dev)")
    print("="*90)
    
    try:
        print(df.to_markdown(index=False)) 
    except:
        print(df.to_string(index=False))
        
    print("="*90)
    
    # Lưu ra file CSV
    df.to_csv("benchmark_final_result.csv", index=False)
    print(f"✅ Đã lưu kết quả chi tiết vào 'benchmark_final_result.csv'")

if __name__ == "__main__":
    run_benchmark()