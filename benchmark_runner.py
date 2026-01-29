import time
import numpy as np
import pandas as pd
import os
import glob
import importlib.util
import inspect
import concurrent.futures
import multiprocessing
import math

# --- 1. CẤU HÌNH BENCHMARK ---

ALGORITHMS = {
    "ga_test": "Genetic Algorithm",
    "pso_test": "PSO",
    "regret_based_test": "Regret-Based",
    "sa_test": "Simulated Annealing",
    "use_model_test": "CP",
    "tabu_search_test": "Tabu Search"
}

DATASET_DIR = "test_case"

TEST_MODES = [
    {"label": "Limit 1 Min",  "time_limit": 60.0},
    {"label": "Limit 5 Mins", "time_limit": 300.0} 
]

NUM_RUNS = 3 

# --- 2. HÀM HỖ TRỢ ---

def get_all_test_files(directory):
    if not os.path.exists(directory):
        return []
    files = glob.glob(os.path.join(directory, "*.txt"))
    files.sort()
    return files

def load_solver(module_name):
    file_path = f"{module_name}.py"
    if not os.path.exists(file_path): return None
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "solve"): return module.solve
    except: return None
    return None

def run_single_task(task_info):
    """Hàm chạy trên từng tiến trình con"""
    dataset_path, algo_name, algo_file, t_limit, run_id = task_info
    
    # Nạp lại module trong process con để đảm bảo sạch sẽ
    solve_func = load_solver(algo_file)
    if not solve_func:
        return (algo_name, 0, 0)

    try:
        with open(dataset_path, 'r') as f:
            input_content = f.read()
            
        start_time = time.time()
        
        # Gọi hàm solve
        sig = inspect.signature(solve_func)
        if 'time_limit' in sig.parameters:
            result = solve_func(input_content, time_limit=t_limit)
        else:
            result = solve_func(input_content)
            
        elapsed = time.time() - start_time
        
        # --- KIỂM TRA KẾT QUẢ > 100 ---
        # Nếu result trả về > 1000 (khả năng là Cost), ta gán cờ cảnh báo
        if isinstance(result, (int, float)) and result > 500: 
            # Đây chỉ là heuristic để phát hiện lỗi unit
            # Bạn có thể bỏ qua nếu bài toán của bạn có > 500 lớp
            pass 

        return (algo_name, result, elapsed)
        
    except Exception as e:
        return (algo_name, 0, 0)

# --- 3. CHƯƠNG TRÌNH CHÍNH ---

def run_benchmark():
    valid_data_files = get_all_test_files(DATASET_DIR)
    if not valid_data_files:
        print(f"❌ Không tìm thấy file dữ liệu trong thư mục '{DATASET_DIR}'.")
        return

    # --- CẤU HÌNH CPU 80% ---
    total_cores = multiprocessing.cpu_count()
    # Lấy 80% số nhân, tối thiểu là 1
    max_workers = max(1, math.floor(total_cores * 0.8))
    
    print(f"{'='*70}")
    print(f"🚀 CẤU HÌNH CHẠY SONG SONG")
    print(f"   - Tổng số nhân CPU: {total_cores}")
    print(f"   - Số nhân sử dụng (80%): {max_workers}")
    print(f"   - Số thuật toán: {len(ALGORITHMS)}")
    print(f"   - Số file dữ liệu: {len(valid_data_files)}")
    print(f"{'='*70}")

    all_tasks = []
    results_map = {} 

    # Tạo danh sách công việc
    for filepath in valid_data_files:
        filename = os.path.basename(filepath)
        for mode in TEST_MODES:
            t_label = mode["label"]
            t_limit = mode["time_limit"]
            
            key = (filename, t_label)
            results_map[key] = {name: {'scores': [], 'times': []} for name in ALGORITHMS.values()}
            
            for algo_file, algo_name in ALGORITHMS.items():
                for i in range(NUM_RUNS):
                    task = (filepath, algo_name, algo_file, t_limit, i)
                    all_tasks.append((key, task))

    total_tasks = len(all_tasks)
    print(f"∑ Tổng số lượt chạy: {total_tasks}")
    print("⏳ Đang xử lý... (Máy sẽ mượt hơn so với chạy 100%)")
    
    # CHẠY PROCESS POOL
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_key = {executor.submit(run_single_task, task_data): key for key, task_data in all_tasks}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                algo_name, score, elapsed = future.result()
                results_map[key][algo_name]['scores'].append(score)
                results_map[key][algo_name]['times'].append(elapsed)
            except Exception as exc:
                print(f"⚠️ Lỗi task: {exc}")
            
            completed += 1
            if completed % 5 == 0 or completed == total_tasks:
                percent = (completed/total_tasks) * 100
                print(f"   ...Hoàn thành {completed}/{total_tasks} ({percent:.1f}%)")

    # --- TỔNG HỢP ---
    final_rows = []
    for (filename, t_label), algos_data in results_map.items():
        row = {"Dataset": filename, "Time Limit": t_label}
        
        for algo_name, metrics in algos_data.items():
            scores = metrics['scores']
            times = metrics['times']
            
            if not scores:
                row[algo_name] = "Err"
                continue

            mean_score = np.mean(scores)
            std_score = np.std(scores)
            
            # Format kết quả
            if std_score == 0:
                res_str = f"{mean_score:.0f}"
            else:
                res_str = f"{mean_score:.1f} ({std_score:.1f})"
            row[algo_name] = res_str
            
        final_rows.append(row)

    df = pd.DataFrame(final_rows)
    first_cols = ["Dataset", "Time Limit"]
    other_cols = [c for c in df.columns if c not in first_cols]
    df = df[first_cols + other_cols]
    
    print("\n" + "="*90)
    print("🏆 KẾT QUẢ ĐÁNH GIÁ (Mean & Std)")
    print("="*90)
    try:
        print(df.to_markdown(index=False)) 
    except:
        print(df.to_string(index=False))
        
    df.to_csv("benchmark_80_percent_cpu.csv", index=False)
    print("\n✅ Đã lưu kết quả vào file: benchmark_80_percent_cpu.csv")

if __name__ == "__main__":
    run_benchmark()