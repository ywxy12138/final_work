import os
import re
import difflib
import chardet
import csv
import requests
import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import QWebEngineView

from urllib.parse import urlsplit


def preprocess_code(code):
    code = re.sub(r'#.*?$|\'\'\'.*?\'\'\'|""".*?"""', '', code, flags=re.DOTALL | re.MULTILINE)
    code = re.sub(r'\s+', ' ', code)
    return code.strip()

def compare_similarity(code1, code2):
    return difflib.SequenceMatcher(None, code1, code2).ratio()

class CodePlagiarismChecker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python 代码查重工具")
        self.setGeometry(100, 100, 1200, 800)

        self.files = {}
        self.current_file = None
        self.mode = 0
        self.task_count = 0
        self.threshold = 10.0  # 新增：默认重复率阈值
        self.suspected_pairs = []  # 新增：用于记录可导出的抄袭文件对

        self.CreateUI()
        self.show_login_time()

    def CreateUI(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        control_layout = QHBoxLayout()
        self.btn_import = QPushButton("导入文件")
        self.btn_import.clicked.connect(self.import_files)
        self.btn_check = QPushButton("开始查重")
        self.btn_check.clicked.connect(self.run_plagiarism_check)
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0, 100)
        self.threshold_spin.setValue(self.threshold)
        self.threshold_spin.setSuffix("% 阈值")
        self.threshold_spin.valueChanged.connect(lambda val: setattr(self, 'threshold', val))

        self.btn_export = QPushButton("导出抄袭文件")
        self.btn_export.clicked.connect(self.export_suspected_files)

        control_layout.addWidget(self.btn_import)
        control_layout.addWidget(self.btn_check)
        control_layout.addWidget(self.threshold_spin)
        control_layout.addWidget(self.btn_export)
        main_layout.addLayout(control_layout)

        splitter = QSplitter(Qt.Horizontal)

        self.file_table = QTableWidget()
        self.file_table.setColumnCount(1)
        self.file_table.setHorizontalHeaderLabels(["文件名称"])
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.file_table.cellClicked.connect(self.display_similarity_for_file)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["对比文件", "重复率", "抄袭标记", "人工审核"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.cellDoubleClicked.connect(self.show_code_comparison)

        self.code_tabs = QTabWidget()
        self.code_tabs.setTabsClosable(True)
        self.code_tabs.tabCloseRequested.connect(self.code_tabs.removeTab)

        splitter.addWidget(self.file_table)
        splitter.addWidget(self.result_table)
        splitter.addWidget(self.code_tabs)
        splitter.setSizes([200, 400, 600])
        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.create_menus()

    def create_menus(self):
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        import_action = QAction("导入文件", self)
        import_action.triggered.connect(self.import_files)
        file_menu.addAction(import_action)

        # 历史记录菜单（一级）
        history_menu = self.menuBar().addMenu("历史记录")
        query_action = QAction("查询历史任务", self)
        query_action.triggered.connect(self.query_history)
        history_menu.addAction(query_action)

        # 模式菜单
        mode_menu = menu_bar.addMenu("模式切换")
        self.one_to_many_action = QAction("一对多模式", self, checkable=True)
        self.group_action = QAction("群体自查模式", self, checkable=True)

        self.one_to_many_action.triggered.connect(lambda: self.switch_mode(0))
        self.group_action.triggered.connect(lambda: self.switch_mode(1))

        mode_menu.addAction(self.one_to_many_action)
        mode_menu.addAction(self.group_action)

        self.update_mode_checkmark()

    def check_history(self):
        pass

    def update_mode_checkmark(self):
        if hasattr(self, 'one_to_many_action') and hasattr(self, 'group_action'):
            self.one_to_many_action.setChecked(self.mode == 0)
            self.group_action.setChecked(self.mode == 1)

    def switch_mode(self, mode):
        self.mode = mode
        self.update_mode_checkmark()
        self.status_bar.showMessage(f"已切换到 {'一对多' if mode == 0 else '群体自查'} 模式")

    def show_login_time(self):
        login_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.status_bar.showMessage(f"登录时间: {login_time}")

    def import_files(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择包含Python文件的文件夹", "", QFileDialog.ShowDirsOnly)
        if not folder_path:
            return

        imported_files = []
        errors = []

        for root, _, filenames in os.walk(folder_path):
            for filename in filenames:
                if filename.endswith('.py'):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        imported_files.append(('files', (filename, file_content, 'text/x-python')))
                        self.files[filename] = {
                            'path': file_path,
                            'content': file_content.decode('utf-8', errors='ignore'),
                            'file_id': None
                        }
                    except Exception as e:
                        errors.append(f"文件 {filename}: {str(e)}")

        if not imported_files:
            QMessageBox.information(self, "无Python文件", "所选文件夹中没有找到Python文件")
            return

        data = {
            'uploader_id': 0,
            'uploader_name': 'user'
        }
        headers = {
            'Authorization': 'Bearer xxx'
        }
        api_url = "http://101.201.83.112:8080/api/plagiarism/CodeUpload/batch/"

        try:
            response = requests.post(api_url, data=data, files=imported_files, headers=headers, timeout=20)
            if response.status_code == 200:
                response_data = response.json()
                for item in response_data.get('results', []):
                    name = item['filename']
                    file_id = item['file_id']
                    if name in self.files:
                        self.files[name]['file_id'] = file_id
                self.status_bar.showMessage(f"成功上传 {len(imported_files)} 个Python文件到服务器", 10000)
                self.display_files()
            else:
                QMessageBox.warning(self, "上传失败", f"服务器返回错误: {response.status_code}\n{response.text}")
        except Exception as e:
            QMessageBox.critical(self, "连接错误", f"无法连接到服务器:\n{str(e)}")

        if errors:
            error_msg = "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n...及其他{len(errors) - 5}个错误"
            QMessageBox.warning(self, "部分文件读取失败", f"以下文件读取时出错:\n{error_msg}")

        print('import success')

    def display_files(self):
        self.file_table.setRowCount(len(self.files))
        self.current_file = None
        self.result_table.setRowCount(0)
        self.code_tabs.clear()

        for row, file_name in enumerate(self.files.keys()):
            item = QTableWidgetItem(file_name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.file_table.setItem(row, 0, item)

    def display_similarity_for_file(self, row, column):
        file_clicked = self.file_table.item(row, 0).text()
        self.current_file = file_clicked
        self.result_table.setRowCount(0)

        results = []
        for other_file in self.files:
            if other_file == file_clicked:
                continue
            sim = compare_similarity(
                preprocess_code(self.files[file_clicked]['content']),
                preprocess_code(self.files[other_file]['content'])
            )
            results.append((other_file, sim))

        results.sort(key=lambda x: x[1], reverse=True)

        for row_pos, (other_file, sim) in enumerate(results):
            self.result_table.insertRow(row_pos)
            self.result_table.setItem(row_pos, 0, QTableWidgetItem(other_file))
            self.result_table.setItem(row_pos, 1, QTableWidgetItem(f"{sim * 100:.2f}%"))
            self.result_table.setItem(row_pos, 2, QTableWidgetItem("查看报告"))
            self.result_table.setItem(row_pos, 3, QTableWidgetItem("待审核"))

    def show_code_comparison(self, row, column):
        if not hasattr(self, "current_file") or not self.current_file:
            return

        file1 = self.current_file
        file2 = self.result_table.item(row, 0).text()

        file1_id = self.files[file1].get("file_id")
        file2_id = self.files[file2].get("file_id")
        if not file1_id or not file2_id:
            QMessageBox.warning(self, "文件ID缺失", f"{file1} 或 {file2} 缺少 file_id")
            return

        try:
            api_url = "http://101.201.83.112:8080/api/plagiarism/query/fileresult/"
            payload = {
                "file_id_list": [
                    {
                        "main_file_id": file1_id,
                        "sub_file_id": file2_id
                    }
                ]
            }
            response = requests.post(api_url, json=payload, timeout=10)
            if response.status_code == 200:
                result_data = response.json()
                print(result_data)
                if result_data.get("success") and result_data.get("results"):
                    result_url = result_data["results"][0].get("result_url")
                    if result_url:
                        html_content = requests.get(result_url).text
                    else:
                        QMessageBox.warning(self, "无返回报告", "后端未返回 result_url")
                        return
                else:
                    QMessageBox.warning(self, "后端返回异常", f"数据格式错误或为空：{result_data}")
                    return
            else:
                QMessageBox.warning(self, "后端错误", f"状态码: {response.status_code}\n{response.text}")
                return
        except Exception as e:
            QMessageBox.critical(self, "网络错误", str(e))
            return

        view = QWebEngineView()
        view.setHtml(html_content)
        self.code_tabs.addTab(view, f"{file1} ⟷ {file2}")
        self.code_tabs.setCurrentWidget(view)

    def run_plagiarism_check(self):
        file_ids = [info["file_id"] for info in self.files.values() if info["file_id"]]
        if not file_ids:
            QMessageBox.warning(self, "缺少文件ID", "请先上传并获取文件ID")
            return

        payload = {
            "user_id": 123,
            "user_name": "user",
            "task_name": "查重任务",
            "mode": self.mode
        }

        if self.mode == 0:
            print(f'self.files is {self.files}')
            payload["file_id_list"] = [file_info["file_id"] for file_info in self.files.values()]
        print(f'payload is {payload}')
        try:
            url = "http://101.201.83.112:8080/api/plagiarism/check/"
            response = requests.post(url, json=payload, timeout=1000, proxies={})
            if response.status_code == 200:
                QMessageBox.information(self, "任务已提交", "查重任务已提交成功！")
            else:
                print('error')
                QMessageBox.warning(self, "提交失败", f"后端返回: {response.status_code}\n{response.text}")
        except Exception as e:
            QMessageBox.critical(self, "提交错误", str(e))

        self.suspected_pairs.clear()
        self.result_table.setRowCount(0)
        files = list(self.files.items())
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                name1, info1 = files[i]
                name2, info2 = files[j]
                sim = compare_similarity(
                    preprocess_code(info1['content']),
                    preprocess_code(info2['content'])
                )
                tag = "是" if sim * 100 >= self.threshold else "否"
                if tag == "是" and info1['file_id'] and info2['file_id']:
                    self.suspected_pairs.append({
                        "main_file_id": info1['file_id'],
                        "sub_file_id": info2['file_id']
                    })

                row_pos = self.result_table.rowCount()
                self.result_table.insertRow(row_pos)
                self.result_table.setItem(row_pos, 0, QTableWidgetItem(f"{name1} ⟷ {name2}"))
                self.result_table.setItem(row_pos, 1, QTableWidgetItem(f"{sim*100:.2f}%"))
                self.result_table.setItem(row_pos, 2, QTableWidgetItem(tag))
                self.result_table.setItem(row_pos, 3, QTableWidgetItem("待审核"))

        self.status_bar.showMessage(f"查重完成，共检测出 {len(self.suspected_pairs)} 对疑似抄袭")

    def query_history(self):
        api_url = "http://101.201.83.112:8080/api/plagiarism/his/query/list/"
        payload = {
            "user_id": 123,
            "category": self.mode,
            "sort_time": 0,
            "sort_check": 0,
            "task_name": "",
            "file_name": ""
        }
        try:
            response = requests.post(api_url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    task_list = data.get("data", [])
                    menu = QMenu()
                    for task in task_list:
                        task_id = task["task_name"]
                        task_name = task.get("task_name", "无名任务")
                        create_time = task.get("create_time", "")
                        display_text = f"任务 {task_name} (ID: {task_id}) ({create_time})"
                        action = QAction(display_text, self)
                        action.triggered.connect(lambda checked, tid=task_id: self.load_task_by_id(tid))
                        menu.addAction(action)
                    menu.exec_(QCursor.pos())
                else:
                    QMessageBox.warning(self, "查询失败", f"后端未返回成功: {data}")
            else:
                QMessageBox.warning(self, "网络错误", f"状态码: {response.status_code}\n{response.text}")
        except Exception as e:
            QMessageBox.critical(self, "异常", str(e))

    def load_task_by_id(self, task_id):
        api_url = f"http://101.201.83.112:8080/api/plagiarism/his/query/{task_id}"
        try:
            response = requests.get(api_url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    task_data = data["data"]
                    self.files.clear()
                    for group in task_data.get("all_result", []):
                        main_id = group.get("main_file_id")
                        filename = str(main_id)
                        self.files[filename] = {"file_id": main_id, "content": "历史内容"}
                    self.display_files()
                else:
                    QMessageBox.warning(self, "加载失败", "后端返回失败标志")
            else:
                QMessageBox.warning(self, "请求失败", f"状态码: {response.status_code}\n{response.text}")
        except Exception as e:
            QMessageBox.critical(self, "网络错误", str(e))

    def export_suspected_files(self):
        if not self.suspected_pairs:
            QMessageBox.information(self, "无抄袭记录", "当前没有可导出的抄袭文件对")
            return

        # 获取用户保存路径
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if not save_dir:
            return

        # 发送 POST 请求到后端
        api_url = "http://101.201.83.112:8080/api/plagiarism/output/file/"
        payload = {
            "file_id_list": self.suspected_pairs
        }

        try:
            print("=== 开始导出 ===")
            print(f'api_url:{payload}')

            response = requests.post(api_url, json=payload, timeout=30)
            print("响应状态码:", response.status_code)
            print("响应内容:", response.text)

            data = response.json()
            print("解析结果:", data)

            for item in data.get("results", []):
                print("单项数据:", item)
            if response.status_code == 200:
                data = response.json()
                if not data.get("success"):
                    QMessageBox.warning(self, "后端返回失败", data.get("message", "未知错误"))
                    return

                results = data.get("results", [])
                count = 0

                for item in results:
                    if not item.get("success"):
                        continue

                    html_url = item["comparison_result"].get("html_url")
                    main_name = item["main_file"]["name"]
                    sub_name = item["sub_file"]["name"]
                    filename = f"{main_name}_{sub_name}.html"

                    try:
                        html_data = requests.get(html_url, timeout=10).text
                        file_path = os.path.join(save_dir, filename)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(html_data)
                        count += 1
                    except Exception as e:
                        print(f"下载失败：{html_url}，错误：{e}")
                        continue

                QMessageBox.information(self, "导出成功", f"已成功导出 {count} 个HTML报告文件")
            else:
                QMessageBox.warning(self, "请求失败", f"状态码: {response.status_code}\n{response.text}")
        except Exception as e:
            QMessageBox.critical(self, "导出异常", str(e))

    def start_check(self):
        pass




def main():
    app = QApplication(sys.argv)
    window = CodePlagiarismChecker()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
