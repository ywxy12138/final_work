import sys
from PyQt5.QtWidgets import QApplication
from login_window import LoginWindow
from CodePlagiarismChecker import CodePlagiarismChecker

# 用全局变量保持主窗口引用
main_win = None

def main():
    app = QApplication(sys.argv)

    def show_main_window():
        global main_win
        main_win = CodePlagiarismChecker()
        main_win.show()

    login = LoginWindow(on_success=show_main_window)
    login.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
