import os
import re
import difflib
import chardet
import csv


def preprocess_code(code):
    code = re.sub(r'//.*?$|/\*.*?\*/|#.*?$|\'\'\'.*?\'\'\'|\"\"\".*?\"\"\"', '', code, flags=re.DOTALL | re.MULTILINE)
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


def compare_codes(code1, code2):
    html_diff=difflib.HtmlDiff()
    html_output=html_diff.make_file(code1,code2)
    with open('diff_output.html','w') as f:
        f.write(html_output)
    return difflib.SequenceMatcher(None, code1, code2).ratio()


def batch_check(directory):
    files = [f for f in os.listdir(directory) if f.endswith(('.c', '.cpp', '.py', '.java'))]
    filepaths = [os.path.join(directory, f) for f in files]

    print(f"📂 共检测到 {len(files)} 个代码文件。")

    processed = [read_and_process(fp) for fp in filepaths]
    n = len(files)

    # 构建相似度矩阵
    similarity_matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            if i == j:
                similarity = 1.0
            else:
                similarity = compare_codes(processed[i], processed[j])
            similarity_matrix[i][j] = similarity
            similarity_matrix[j][i] = similarity

    # 输出为CSV
    output_path = os.path.join(directory, "similarity_matrix.csv")
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([''] + files)
        for i in range(n):
            writer.writerow([files[i]] + [f"{similarity_matrix[i][j] * 100:.2f}%" for j in range(n)])

    print(f"\n✅ 相似度矩阵已保存至: {output_path}")


if __name__ == "__main__":
    directory = input("请输入包含代码文件的目录路径: ").strip()
    if os.path.isdir(directory):
        batch_check(directory)
    else:
        print("目录不存在，请检查路径。")
