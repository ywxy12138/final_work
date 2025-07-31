from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox
)
import requests
from register_window import RegisterWindow

class LoginWindow(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("登录")
        self.setFixedSize(300, 220)

        layout = QVBoxLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.handle_login)
        layout.addWidget(self.login_button)

        self.register_button = QPushButton("注册")
        self.register_button.clicked.connect(self.open_register)
        layout.addWidget(self.register_button)

        self.setLayout(layout)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "错误", "用户名和密码不能为空")
            return

        try:
            response = requests.post(
                "http://101.201.83.112:8080/api/user/login/",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                QMessageBox.information(self, "登录成功", "欢迎使用！")
                self.on_success()
                self.close()
            else:
                QMessageBox.critical(self, "登录失败", f"HTTP {response.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "网络错误", str(e))

    def open_register(self):
        self.register_window = RegisterWindow(return_to_login_callback=self.show_again)
        self.register_window.show()
        self.close()

    def show_again(self):
        # 重新显示登录界面
        self.show()
