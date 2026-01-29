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
    "use_model_test": "CP",             # Baseline
    "ga_test": "Genetic Algorithm",
    "pso_test": "PSO",
    "regret_based_test": "Regret-Based",
    "sa_test": "Simulated Annealing",
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
    """Hàm chạy trên từng process con"""
    dataset_path, algo_name, algo_file, t_limit, run_id = task_info
    
    solve_func = load_solver(algo_file)
    if not solve_func: return (algo_name, None, 0)

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
        return (algo_name, result, elapsed)
        
    except Exception as e:
        # print(f"Error in {algo_name}: {e}")
        return (algo_name, None, 0)

# --- 3. CHƯƠNG TRÌNH CHÍNH ---

def run_benchmark():
    valid_data_files = get_all_test_files(DATASET_DIR)
    if not valid_data_files:
        print(f"❌ Không tìm thấy dữ liệu trong '{DATASET_DIR}'.")
        return

    # --- CẤU HÌNH CPU 80% ---
    total_cores = multiprocessing.cpu_count()
    max_workers = max(1, math.floor(total_cores * 0.8))
    
    print(f"{'='*80}")
    print(f"🚀 BENCHMARK SYSTEM (Multi-core: {max_workers}/{total_cores})")
    print(f"   Metrics: Task Count (Primary) | Makespan (Secondary)")
    print(f"{'='*80}")

    all_tasks = []
    # Cấu trúc lưu trữ: keys -> list of raw results (dict or int)
    results_map = {} 

    for filepath in valid_data_files:
        filename = os.path.basename(filepath)
        for mode in TEST_MODES:
            key = (filename, mode["label"])
            results_map[key] = {name: {'raw_res': [], 'times': []} for name in ALGORITHMS.values()}
            
            for algo_file, algo_name in ALGORITHMS.items():
                for i in range(NUM_RUNS):
                    task = (filepath, algo_name, algo_file, mode["time_limit"], i)
                    all_tasks.append((key, task))

    total_tasks = len(all_tasks)
    print(f"∑ Total Tasks: {total_tasks}. Processing...")
    
    # CHẠY SONG SONG
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(run_single_task, task): key for key, task in all_tasks}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_map):
            key = future_map[future]
            try:
                name, raw_res, elapsed = future.result()
                if raw_res is not None:
                    results_map[key][name]['raw_res'].append(raw_res)
                    results_map[key][name]['times'].append(elapsed)
            except Exception: pass
            
            completed += 1
            if completed % 10 == 0 or completed == total_tasks:
                print(f"   -> Progress: {completed}/{total_tasks} ({completed/total_tasks:.0%})")

    # --- TỔNG HỢP VÀ XỬ LÝ SỐ LIỆU ---
    final_rows = []
    
    for (filename, t_label), algos_data in results_map.items():
        row = {"Dataset": filename, "Mode": t_label}
        
        # 1. Tìm Best Count để làm mốc so sánh (nếu cần)
        # best_count_in_group = 0
        # for name, metrics in algos_data.items():
        #     # Logic tìm max count... (tạm bỏ qua để giữ bảng đơn giản)
        #     pass

        for algo_name, metrics in algos_data.items():
            raw_list = metrics['raw_res']
            if not raw_list:
                row[algo_name] = "Err"
                continue

            # Tách Count và Makespan từ raw_list
            counts = []
            makespans = []
            
            for r in raw_list:
                if isinstance(r, dict):
                    counts.append(r.get('count', 0))
                    makespans.append(r.get('makespan', 0))
                elif isinstance(r, (int, float)):
                    counts.append(r)
                    makespans.append(0) # Không có thông tin makespan
            
            # Tính trung bình
            mean_cnt = np.mean(counts)
            std_cnt = np.std(counts)
            mean_mk = np.mean(makespans)
            
            # Format hiển thị: "Count (Std) | Time"
            # Ví dụ: "98 (1.2) | 540s"
            
            count_str = f"{mean_cnt:.0f}"
            if std_cnt > 0:
                count_str += f" (±{std_cnt:.1f})"
            
            mk_str = ""
            if mean_mk > 0:
                mk_str = f" | T:{mean_mk:.0f}"
            
            row[algo_name] = count_str + mk_str
            
        final_rows.append(row)

    df = pd.DataFrame(final_rows)
    # Sắp xếp cột
    cols = ["Dataset", "Mode"] + [c for c in df.columns if c not in ["Dataset", "Mode"]]
    df = df[cols]
    
    print("\n" + "="*100)
    print("🏆 BẢNG KẾT QUẢ: Số Lớp (Độ lệch) | Makespan (T)")
    print("="*100)
    try:
        print(df.to_markdown(index=False)) 
    except:
        print(df.to_string(index=False))
        
    df.to_csv("benchmark_final_result.csv", index=False)
    print("\n✅ Đã lưu kết quả vào: benchmark_final_result.csv")

if __name__ == "__main__":
    run_benchmark()