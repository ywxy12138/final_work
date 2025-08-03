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
        self.mode = 0  # 默认为一对多模式

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
        control_layout.addWidget(self.btn_import)
        control_layout.addWidget(self.btn_check)
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
        file_menu = self.menuBar().addMenu("文件")

        import_action = QAction("导入文件", self)
        import_action.triggered.connect(self.import_files)
        file_menu.addAction(import_action)

        export_action = QAction("导出结果", self)
        file_menu.addAction(export_action)

        history_menu = self.menuBar().addMenu("历史记录")

        view_menu = self.menuBar().addMenu("查看")
        self.mode_label = QLabel("当前: 一对多模式")
        mode_widget_action = QWidgetAction(self)
        mode_widget_action.setDefaultWidget(self.mode_label)
        view_menu.addAction(mode_widget_action)

        one_to_many_action = QAction("一对多模式", self)
        one_to_many_action.triggered.connect(lambda: self.switch_mode(0))
        group_action = QAction("群体自查模式", self)
        group_action.triggered.connect(lambda: self.switch_mode(1))
        view_menu.addAction(one_to_many_action)
        view_menu.addAction(group_action)

    def switch_mode(self, mode):
        self.mode = mode
        self.mode_label.setText("当前: 一对多模式" if mode == 0 else "当前: 群体自查模式")

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
            response = requests.post(url, json=payload, timeout=10, proxies={})
            if response.status_code == 200:
                QMessageBox.information(self, "任务已提交", "查重任务已提交成功！")
            else:
                print('error')
                QMessageBox.warning(self, "提交失败", f"后端返回: {response.status_code}\n{response.text}")
        except Exception as e:
            QMessageBox.critical(self, "提交错误", str(e))

def main():
    app = QApplication(sys.argv)
    window = CodePlagiarismChecker()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
