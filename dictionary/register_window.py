from PyQt5.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QVBoxLayout, QMessageBox, QHBoxLayout
)
import requests

class RegisterWindow(QWidget):
    def __init__(self, return_to_login_callback):
        super().__init__()
        self.return_to_login_callback = return_to_login_callback
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("注册")
        self.setFixedSize(320, 340)

        layout = QVBoxLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        layout.addWidget(self.username_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("邮箱")
        layout.addWidget(self.email_input)

        # 邮箱验证码发送区域（输入框 + 按钮）
        code_layout = QHBoxLayout()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("验证码")
        code_layout.addWidget(self.code_input)

        self.send_code_button = QPushButton("获取验证码")
        self.send_code_button.setFixedWidth(100)
        self.send_code_button.clicked.connect(self.send_code)
        code_layout.addWidget(self.send_code_button)

        layout.addLayout(code_layout)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("确认密码")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.confirm_input)

        self.register_button = QPushButton("注册")
        self.register_button.clicked.connect(self.handle_register)
        layout.addWidget(self.register_button)

        self.back_button = QPushButton("返回登录")
        self.back_button.clicked.connect(self.handle_back_to_login)
        layout.addWidget(self.back_button)

        self.setLayout(layout)

    def send_code(self):
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.warning(self, "错误", "请输入邮箱以发送验证码")
            return

        try:
            response = requests.post(
                "http://101.201.83.112:8080/api/user/sendcode/",
                json={"email": email}
            )
            if response.status_code == 200:
                QMessageBox.information(self, "发送成功", "验证码已发送到邮箱")
            else:
                QMessageBox.critical(
                    self, "发送失败",
                    f"HTTP {response.status_code}\n{response.text}"
                )
        except Exception as e:
            QMessageBox.critical(self, "网络错误", str(e))

    def handle_register(self):
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        code = self.code_input.text().strip()
        password = self.password_input.text().strip()
        confirm = self.confirm_input.text().strip()

        if not all([username, email, code, password, confirm]):
            QMessageBox.warning(self, "错误", "所有字段都是必填的")
            return
        if password != confirm:
            QMessageBox.warning(self, "错误", "两次输入密码不一致")
            return

        try:
            response = requests.post(
                "http://101.201.83.112:8080/api/user/register/",
                json={
                    "username": username,
                    "email": email,
                    "code": code,
                    "password": password
                }
            )
            if response.status_code == 200:
                QMessageBox.information(self, "注册成功", "请返回登录界面登录")
                self.close()
                self.return_to_login_callback()
            else:
                QMessageBox.critical(
                    self, "注册失败",
                    f"HTTP {response.status_code}\n{response.text}"
                )
        except Exception as e:
            QMessageBox.critical(self, "网络错误", str(e))

    def handle_back_to_login(self):
        self.close()
        self.return_to_login_callback()
