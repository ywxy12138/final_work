import sys
import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class CodePlagiarismChecker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python 代码查重工具")
        self.setGeometry(100, 100, 1200, 800)

        # 初始化数据库
        # self.init_db()
        self.files={}

        # 创建UI
        self.CreateUI()

        # 显示登录时间
        self.show_login_time()


    def CreateUI(self):
        # 主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)


        # 顶部控制栏
        control_layout = QHBoxLayout()
        self.btn_import = QPushButton("导入文件")
        self.btn_import.clicked.connect(self.import_files)
        self.btn_check = QPushButton("开始查重")
        self.btn_check.clicked.connect(self.run_plagiarism_check)
        control_layout.addWidget(self.btn_import)
        control_layout.addWidget(self.btn_check)
        main_layout.addLayout(control_layout)


        # 分割视图
        splitter = QSplitter(Qt.Horizontal)


        # 左侧：文件列表
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(1)
        self.file_table.setHorizontalHeaderLabels(["文件名称"])
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)


        # 中间：结果列表
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(["文件1", "重复率", "抄袭标记"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.cellDoubleClicked.connect(self.show_code_comparison)


        # 右侧：代码对比区域
        self.code_tabs = QTabWidget()
        self.code_view1 = QTextEdit()
        self.code_view2 = QTextEdit()
        self.code_view1.setReadOnly(True)
        self.code_view2.setReadOnly(True)


        # 添加高亮器
        # self.highlighter1 = CodeHighlighter(self.code_view1.document())
        # self.highlighter2 = CodeHighlighter(self.code_view2.document())


        # 组合分割视图
        splitter.addWidget(self.file_table)
        splitter.addWidget(self.result_table)
        splitter.addWidget(self.code_tabs)
        splitter.setSizes([200, 400, 400])
        main_layout.addWidget(splitter)


        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)


        # 创建菜单
        self.create_menus()


    def create_menus(self):
        # 文件菜单
        file_menu = self.menuBar().addMenu("文件")

        import_action = QAction("导入文件", self)
        import_action.triggered.connect(self.import_files)
        file_menu.addAction(import_action)

        export_action = QAction("导出结果", self)
        # export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)


        # 历史记录菜单
        history_menu = self.menuBar().addMenu("历史记录")
        # self.load_history_menu(history_menu)


        # 查看菜单
        view_menu = self.menuBar().addMenu("查看")
        group_action = QAction("群体自查模式", self)
        # group_action.triggered.connect(self.switch_to_group_mode)
        view_menu.addAction(group_action)


    def init_db(self):
        # 初始化数据库需要的操作
        pass


    def show_login_time(self):
        # 在状态栏显示登录时间
        login_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.status_bar.showMessage(f"登录时间: {login_time}")


    def import_files(self):
        """导入文件夹中的所有Python文件"""
        # 获取文件夹路径
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择包含Python文件的文件夹",
            "",
            QFileDialog.ShowDirsOnly
        )

        if not folder_path:
            return

        # 遍历文件夹中的所有Python文件
        imported_count = 0
        for root, _, filenames in os.walk(folder_path):
            for filename in filenames:
                if filename.endswith('.py'):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # 存储文件数据
                        self.files[filename] = {
                            'path': file_path,
                            'content': content
                        }
                        imported_count += 1
                    except Exception as e:
                        QMessageBox.warning(
                            self,
                            "读取错误",
                            f"无法读取文件 {file_path}:\n{str(e)}"
                        )

        if imported_count > 0:
            # 更新文件列表显示
            self.display_files()
            # 更新状态栏
            self.status_bar.showMessage(
                f"成功导入 {imported_count} 个Python文件",
                3000
            )
        else:
            QMessageBox.information(
                self,
                "无Python文件",
                "所选文件夹中没有找到Python文件"
            )


    def display_files(self):
        # 在文件列表中显示文件需要的操作
        self.file_table.setRowCount(len(self.files))

        for row, file_name in enumerate(self.files.keys()):
            item = QTableWidgetItem(file_name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)  # 设置为不可编辑
            self.file_table.setItem(row, 0, item)
        pass


    def run_plagiarism_check(self):
        if not self.files:
            QMessageBox.warning(self, "警告", "请先导入 Python 文件夹！")
            return

        files = list(self.files.keys())
        directory = os.path.dirname(self.files[files[0]]['path'])
        raw_codes = {f: self.files[f]['content'] for f in files}
        processed_codes = {f: preprocess_code(self.files[f]['content']) for f in files}

        n = len(files)
        similarity_matrix = [[0.0] * n for _ in range(n)]

        self.result_table.setRowCount(0)  # 清空表格

        for i in range(n):
            for j in range(i + 1, n):
                sim = compare_similarity(processed_codes[files[i]], processed_codes[files[j]])
                similarity_matrix[i][j] = sim
                similarity_matrix[j][i] = sim

                # 更新结果表格
                row_pos = self.result_table.rowCount()
                self.result_table.insertRow(row_pos)
                self.result_table.setItem(row_pos, 0, QTableWidgetItem(f"{files[i]} ⟷ {files[j]}"))
                self.result_table.setItem(row_pos, 1, QTableWidgetItem(f"{sim * 100:.2f}%"))
                self.result_table.setItem(row_pos, 2, QTableWidgetItem("查看报告"))

                # 生成 HTML 报告
                subdir = os.path.join(directory, os.path.splitext(files[i])[0])
                os.makedirs(subdir, exist_ok=True)
                html_path = os.path.join(subdir, f"{files[j]}.html")
                generate_html_report(
                    raw_codes[files[i]], raw_codes[files[j]],
                    files[i], files[j],
                    html_path
                )
        self.result_table.sortItems(1, Qt.DescendingOrder)

        # 保存 CSV 文件
        csv_path = os.path.join(directory, "similarity_matrix.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([""] + files)
            for i in range(n):
                row = [files[i]] + [f"{similarity_matrix[i][j] * 100:.2f}%" for j in range(n)]
                writer.writerow(row)

        self.status_bar.showMessage(f"查重完成！结果已保存到 {csv_path}", 5000)

    def show_code_comparison(self, row, column):
        if not hasattr(self, "current_file") or not self.current_file:
            return

        file_pair_item = self.result_table.item(row, 0)
        if not file_pair_item:
            return

        # 文件1是当前选中的文件，文件2来自 middle 表格
        _, file2 = file_pair_item.text().split("⟷")
        file2 = file2.strip()
        file1 = self.current_file

        html_path = os.path.join(
            os.path.dirname(self.files[file1]['path']),
            os.path.splitext(file1)[0],
            f"{file2}.html"
        )

        if not os.path.exists(html_path):
            QMessageBox.warning(self, "报告未生成", f"找不到报告文件：\n{html_path}")
            return

        from PyQt5.QtWebEngineWidgets import QWebEngineView
        view = QWebEngineView()
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        view.setHtml(html_content)
        self.code_tabs.addTab(view, f"{file1} ⟷ {file2}")
        self.code_tabs.setCurrentWidget(view)

    def calculate_similarity(self, file1, file2):
        # 计算两个文件的代码相似度需要的操作
        pass

    def display_similarity_for_file(self, row, column):
        file_clicked = self.file_table.item(row, 0).text()
        self.current_file = file_clicked

        self.result_table.setRowCount(0)

        results = []
        for other_file in self.files:
            if other_file == file_clicked:
                continue
            key = (file_clicked, other_file)
            if key in self.similarity:
                sim = self.similarity[key]
                results.append((other_file, sim))

        # 按相似度降序排列
        results.sort(key=lambda x: x[1], reverse=True)

        for other_file, sim in results:
            row_pos = self.result_table.rowCount()
            self.result_table.insertRow(row_pos)
            self.result_table.setItem(row_pos, 0, QTableWidgetItem(f"{file_clicked} ⟷ {other_file}"))
            self.result_table.setItem(row_pos, 1, QTableWidgetItem(f"{sim * 100:.2f}%"))
            self.result_table.setItem(row_pos, 2, QTableWidgetItem("查看报告"))

    def highlight_similar_code(self, code1, code2):
        # 高亮显示相似代码段需要的操作
        pass


    def save_to_history(self, files):
        # 保存到历史记录需要的操作
        pass


    def load_history_menu(self, menu):
        # 加载历史记录菜单需要的操作
        pass


    def switch_to_group_mode(self):
        # 切换到群体自查模式需要的操作
        pass


    def export_results(self):
        # 导出结果需要的操作
        pass


def main():
    app = QApplication(sys.argv)
    ex = CodePlagiarismChecker()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
