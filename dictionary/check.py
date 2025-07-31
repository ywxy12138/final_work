import os
import re
import difflib
import chardet
import csv

def preprocess_code(code):
    code = re.sub(r'#.*?$|\'\'\'.*?\'\'\'|\"\"\".*?\"\"\"', '', code, flags=re.DOTALL | re.MULTILINE)
    code = re.sub(r'\s+', ' ', code)
    return code.strip()

def read_and_process(filepath):
    with open(filepath, 'rb') as f:
        raw_bytes = f.read()
    result = chardet.detect(raw_bytes)
    encoding = result['encoding'] or 'utf-8'
    try:
        raw_code = raw_bytes.decode(encoding)
    except Exception as e:
        print(f"读取 {filepath} 失败，编码为 {encoding}：{e}")
        return ""
    return preprocess_code(raw_code)

def read_raw(filepath):
    with open(filepath, 'rb') as f:
        raw_bytes = f.read()
    result = chardet.detect(raw_bytes)
    encoding = result['encoding'] or 'utf-8'
    try:
        raw_code = raw_bytes.decode(encoding)
    except:
        return ""
    return raw_code

def generate_html_report(code1, code2, file1_name, file2_name, output_path):
    differ = difflib.HtmlDiff(tabsize=4, wrapcolumn=80)
    html_content = differ.make_file(
        code1.splitlines(), code2.splitlines(),
        fromdesc=file1_name,
        todesc=file2_name
    )
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

def compare_similarity(code1, code2):
    return difflib.SequenceMatcher(None, code1, code2).ratio()

def batch_html_and_csv(directory):
    files = [f for f in os.listdir(directory) if f.endswith('.py')]
    filepaths = [os.path.join(directory, f) for f in files]

    print(f"共 {len(files)} 个 Python 文件。")

    # 预处理和原始读取
    raw_codes = {f: read_raw(os.path.join(directory, f)) for f in files}
    processed_codes = {f: read_and_process(os.path.join(directory, f)) for f in files}

    n = len(files)
    similarity_matrix = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(i, n):
            if i == j:
                sim = 1.0
            else:
                sim = compare_similarity(processed_codes[files[i]], processed_codes[files[j]])
            similarity_matrix[i][j] = sim
            similarity_matrix[j][i] = sim

    # 生成每个 HTML 文件
    for i in range(n):
        file1 = files[i]
        code1 = raw_codes[file1]
        if not code1:
            continue

        subdir = os.path.join(directory, os.path.splitext(file1)[0])
        os.makedirs(subdir, exist_ok=True)

        for j in range(n):
            if i == j:
                continue
            file2 = files[j]
            code2 = raw_codes[file2]
            if not code2:
                continue
            output_html_path = os.path.join(subdir, f"{file2}.html")
            generate_html_report(code1, code2, file1, file2, output_html_path)

    # 生成 CSV
    csv_path = os.path.join(directory, "similarity_matrix.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([""] + files)
        for i in range(n):
            row = [files[i]] + [f"{similarity_matrix[i][j]*100:.2f}%" for j in range(n)]
            writer.writerow(row)

    print(f"\n相似度矩阵已保存为：{csv_path}")

if __name__ == "__main__":
    directory = input("请输入包含 Python 文件的目录路径: ").strip()
    if os.path.isdir(directory):
        batch_html_and_csv(directory)
    else:
        print("目录不存在，检查路径。")
