# 批量导入代码
import os

def import_files(directory_path):
    python_files = []
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                file_content = file.read()
                if file_content.strip():
                    # 若代码文件不为空
                    python_files.append({
                        "filename": filename,
                        "filepath": file_path,
                        "content": file_content
                    })
        except Exception as e:
            print(f"读取文件{filename}失败，异常为{e}")
    return python_files