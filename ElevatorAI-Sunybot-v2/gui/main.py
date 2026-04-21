import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel
)

from backend.chatbot_engine import get_chatbot_response
from backend.employee_service import find_employee

class ChatbotGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SUNYBOT - Elevator AI")
        self.setGeometry(200, 200, 700, 500)

        layout = QVBoxLayout()

        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Nhap cau hoi...")

        send_btn = QPushButton("Gui")
        send_btn.clicked.connect(self.handle_send)

        layout.addWidget(QLabel("Chatbot"))
        layout.addWidget(self.chat_area)

        hbox = QHBoxLayout()
        hbox.addWidget(self.input_box)
        hbox.addWidget(send_btn)

        layout.addLayout(hbox)
        self.setLayout(layout)

    def handle_send(self):
        question = self.input_box.text().strip()
        if not question:
            return

        self.chat_area.append(f"Ban: {question}")

        # Chatbot router (DB + embedding + LLM)
        answer =  get_chatbot_response(question)

        self.chat_area.append(f"Bot: {answer}\n")
        self.input_box.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatbotGUI()
    window.show()
    sys.exit(app.exec_())

