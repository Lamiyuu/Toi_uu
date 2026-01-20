import time
import numpy as np
import pandas as pd
import os
import glob
import importlib.util
import inspect

# --- 1. CẤU HÌNH BENCHMARK ---

# Danh sách các file code thuật toán (Tên file .py : Tên hiển thị)
ALGORITHMS = {
    # "ga_test": "Genetic Algorithm",
    "pso_test": "PSO",
    "regret_based_test": "Regret-Based",
    "sa_test": "Simulated Annealing",
    "use_model_test": "CP",
    "tabu_search_test": "Tabu Search"
}

# Thư mục chứa file dữ liệu test (đổi tên nếu thư mục của bạn khác)
DATASET_DIR = "test_case"

# Cấu hình các chế độ test (1 phút và 3 phút)
TEST_MODES = [
    {"label": "Limit 1 Min",  "time_limit": 60.0},
    {"label": "Limit 5 Mins", "time_limit": 180.0}
]

# Số lần chạy lại mỗi thuật toán để tính trung bình
NUM_RUNS = 3

# --- 2. HÀM HỖ TRỢ ---

def get_all_test_files(directory):
    """Quét toàn bộ file .txt trong thư mục"""
    if not os.path.exists(directory):
        print(f"⚠️  Cảnh báo: Thư mục '{directory}' không tồn tại.")
        return []
    
    # Lấy đường dẫn tất cả file .txt
    files = glob.glob(os.path.join(directory, "*.txt"))
    files.sort() # Sắp xếp để chạy theo thứ tự
    return files

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
    - Truyền time_limit nếu hàm hỗ trợ.
    """
    try:
        sig = inspect.signature(func)
        
        # Kiểm tra xem hàm solve có nhận tham số time_limit không
        if 'time_limit' in sig.parameters:
            return func(input_content, time_limit=limit)
        else:
            # Nếu hàm không hỗ trợ time_limit, gọi bình thường
            # (Lưu ý: Các thuật toán meta-heuristic CẦN hỗ trợ time_limit để dừng đúng lúc)
            return func(input_content)
            
    except Exception as e:
        print(f"❌ Runtime Error: {e}")
        return 0

# --- 3. CHƯƠNG TRÌNH CHÍNH ---

def run_benchmark():
    # 1. Quét file dữ liệu
    print(f"{'='*70}")
    print(f"📂 ĐANG QUÉT DỮ LIỆU TỪ THƯ MỤC: {DATASET_DIR} ...")
    valid_data_files = get_all_test_files(DATASET_DIR)
            
    if not valid_data_files:
        print(f"❌ LỖI: Không tìm thấy file .txt nào trong thư mục '{DATASET_DIR}'.")
        return
    else:
        print(f"   Tìm thấy {len(valid_data_files)} file:")
        for f in valid_data_files:
            print(f"   - {os.path.basename(f)}")

    # 2. Nạp các thuật toán
    solvers = {}
    print(f"\n📦 ĐANG NẠP CÁC THUẬT TOÁN...")
    for filename, display_name in ALGORITHMS.items():
        solver_func = load_solver(filename)
        if solver_func:
            solvers[display_name] = solver_func
            print(f"   ✅ Đã nạp: {display_name:<20} ({filename}.py)")
        else:
            print(f"   ⚠️  Bỏ qua:  {filename}.py (Không tìm thấy)")
    print(f"{'='*70}\n")

    if not solvers:
        print("❌ LỖI: Không tìm thấy bất kỳ thuật toán nào để chạy.")
        return

    results = []
    
    print(f"🚀 BẮT ĐẦU CHẠY BENCHMARK...")
    
    # Duyệt qua từng file dữ liệu
    for filepath in valid_data_files:
        filename = os.path.basename(filepath)
        print(f"\n📂 Dataset: {filename}")
        
        # Đọc nội dung file 1 lần
        try:
            with open(filepath, 'r') as f:
                input_content = f.read()
        except Exception as e:
            print(f"❌ Lỗi đọc file {filename}: {e}")
            continue
            
        # Duyệt qua các chế độ thời gian (1 phút, 5 phút)
        for mode in TEST_MODES:
            t_label = mode["label"]
            t_limit = mode["time_limit"]
            
            print(f"   ⏱️  Mode: {t_label}")
            print("-" * 70)
            
            row = {
                "Dataset": filename,
                "Time Limit": t_label
            }
            
            # Chạy từng thuật toán
            for name, solve_func in solvers.items():
                scores = []
                times = []
                
                # Chạy lặp lại NUM_RUNS lần để lấy trung bình
                for i in range(NUM_RUNS):
                    start_time = time.time()
                    
                    # Gọi hàm giải
                    score = call_solver_safe(solve_func, input_content, t_limit)
                    
                    end_time = time.time()
                    elapsed = end_time - start_time
                    
                    scores.append(score)
                    times.append(elapsed)
                
                # Tính toán thống kê
                mean_score = np.mean(scores)
                std_score = np.std(scores)
                mean_time = np.mean(times)
                
                # Format kết quả: "Điểm TB (Độ lệch chuẩn)"
                if std_score == 0:
                    res_str = f"{mean_score:.0f}"
                else:
                    res_str = f"{mean_score:.1f} ({std_score:.1f})"
                
                row[name] = res_str
                
                # In kết quả từng dòng
                print(f"      🔹 {name:<20}: Score = {res_str:<15} | Avg Time: {mean_time:.2f}s")

            results.append(row)

    # --- 4. XUẤT KẾT QUẢ ---
    if not results:
        print("\n❌ Không có kết quả nào được ghi nhận.")
        return

    df = pd.DataFrame(results)
    
    # Sắp xếp cột hiển thị cho đẹp
    first_cols = ["Dataset", "Time Limit"]
    other_cols = [c for c in df.columns if c not in first_cols]
    df = df[first_cols + other_cols]
    
    print("\n" + "="*90)
    print("🏆 BẢNG TỔNG HỢP KẾT QUẢ (Score Mean & Std Dev)")
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