import sys
import socket
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog
from PyQt6 import uic
import google.generativeai as genai
import traceback

# Gemini API 키 설정
genai.configure(api_key="YOUR_API_KEY")


def get_ui_path(filename):
    """UI 파일 경로 반환"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def exception_hook(exctype, value, tb):
    """전역 예외 처리"""
    print("[FATAL ERROR] 프로그램 종료를 유발한 예외 발생:")
    traceback.print_exception(exctype, value, tb)
    sys.exit(1)


sys.excepthook = exception_hook  # 전역 예외 처리 설정


class FirstScreen(QDialog):
    def __init__(self, sock):
        super().__init__()
        try:
            uic.loadUi(get_ui_path('첫 화면.ui'), self)
            print("[DEBUG] 첫 화면 UI 로드 성공")
        except Exception as e:
            print(f"[ERROR] 첫 화면 UI 로드 실패: {str(e)}")
            raise
        self.sock = sock
        self.main_window = None
        self.init_ui()

    def init_ui(self):
        """초기 UI 설정 및 버튼 연결"""
        self.next_button.clicked.connect(self.start_main_window)  # 다음 버튼 연결
        self.random_button.clicked.connect(self.generate_random_setting)  # 랜덤 설정 버튼

    def start_main_window(self):
        """메인 창으로 전환"""
        genre = self.genre_input.text().strip()
        choice_limit = self.choice_input.text().strip()
        setting = self.setting_input.toPlainText().strip()

        print(f"[DEBUG] 장르 입력값: {genre}")
        print(f"[DEBUG] 선택 기회 입력값: {choice_limit}")
        print(f"[DEBUG] 초기 설정 입력값: {setting}")

        if not genre:
            self.setting_input.setPlainText("장르를 입력하세요!")
            return
        if not choice_limit.isdigit():
            self.setting_input.setPlainText("선택 기회는 숫자로 입력하세요!")
            return
        if not setting:
            self.setting_input.setPlainText("초기 설정을 입력하세요!")
            return

        try:
            request_data = f"INIT|{genre}|{setting}"
            print(f"[DEBUG] 서버로 요청 전송: {request_data}")
            self.sock.sendall(request_data.encode('utf-8'))

            response = self.sock.recv(4096).decode('utf-8')
            print(f"[DEBUG] 서버 응답: {response}")

            if not response:
                raise ConnectionError("서버로부터 응답이 없습니다.")

            status, content = response.split('|', 1)
            print(f"[DEBUG] 상태: {status}, 내용: {content}")

            if status == "OK":
                # MainWindow로 전환
                self.transition_to_main_window(genre, int(choice_limit), content)
            else:
                self.setting_input.setPlainText(f"서버 오류: {content}")
        except Exception as e:
            print(f"[ERROR] 서버 통신 중 문제 발생: {str(e)}")
            self.setting_input.setPlainText(f"서버와의 통신 중 오류 발생: {str(e)}")

    def transition_to_main_window(self, genre, choice_limit, content):
        """MainWindow로 전환"""
        try:
            print("[DEBUG] MainWindow 전환 준비 중...")
            self.main_window = MainWindow(self.sock, genre, choice_limit, content, self)  # FirstScreen 전달
            self.main_window.show()
            print("[DEBUG] MainWindow 표시 성공")
            self.hide()  # 첫 화면 숨기기
        except Exception as e:
            print(f"[ERROR] MainWindow 전환 중 문제 발생: {str(e)}")

    def generate_random_setting(self):
        """Gemini API로 랜덤 설정 생성"""
        try:
            print("[DEBUG] Gemini API 랜덤 설정 요청")
            model = genai.GenerativeModel("gemini-pro")
            chat = model.start_chat(history=[])

            # 프롬프트를 통해 랜덤 설정 요청
            response = chat.send_message(content="랜덤으로 1줄 정도 이야기의 초반 설정을 먼저 적어줘")
            random_setting = response.text.strip()
            print(f"[DEBUG] 랜덤 설정 성공: {random_setting}")
            self.setting_input.setPlainText(random_setting)
        except Exception as e:
            print(f"[ERROR] 랜덤 설정 생성 실패: {str(e)}")
            self.setting_input.setPlainText(f"랜덤 설정 생성 실패: {str(e)}")


class MainWindow(QMainWindow):
    def __init__(self, sock, genre, choice_limit, initial_story, first_screen):
        super().__init__()
        try:
            uic.loadUi(get_ui_path('메인.ui'), self)
            print("[DEBUG] 메인 화면 UI 로드 성공")
        except Exception as e:
            print(f"[ERROR] 메인 화면 UI 로드 실패: {str(e)}")
            raise

        self.sock = sock
        self.genre = genre
        self.choice_limit = choice_limit
        self.remaining_choices = choice_limit
        self.first_screen = first_screen  # 첫 화면 참조 저장

        # 전달받은 데이터를 UI에 표시
        self.genre_input.setText(genre)
        self.choice_input.setText(str(choice_limit))
        self.story_display.setPlainText(f"AI: {initial_story}\n")  # AI 텍스트와 구분을 위한 줄 바꿈 추가
        print("[DEBUG] 초기 이야기 출력 성공")

        self.next_button.clicked.connect(self.continue_story)
    def continue_story(self):
        """사용자 입력 처리 및 AI 응답"""
        try:
            user_input = self.user_text_input.toPlainText().strip()
            if user_input:
                # 사용자가 입력한 텍스트를 표시하고 줄 바꿈 추가
                self.story_display.appendPlainText(f"사용자: {user_input}\n")
                self.user_text_input.clear()

                # 선택 기회 감소 및 업데이트
                self.remaining_choices -= 1
                self.choice_input.setText(str(self.remaining_choices))

                # 서버에 사용자 입력 전송
                request_data = f"CONTINUE|{self.genre}|{user_input}"  # 장르 추가
                self.sock.sendall(request_data.encode('utf-8'))

                # 서버로부터 AI 응답 수신
                response = self.sock.recv(4096).decode('utf-8')
                print(f"[DEBUG] 서버 응답: {response}")

                if not response or '|' not in response:
                    self.story_display.appendPlainText("[ERROR] 서버 응답이 유효하지 않습니다.\n")
                    return

                status, content = response.split('|', 1)
                if status == "OK":
                    self.story_display.appendPlainText(f"AI: {content}\n")  # AI 응답 추가
                else:
                    self.story_display.appendPlainText(f"서버 오류: {content}\n")

            if self.remaining_choices <= 0:
                self.show_ending()  # 선택 기회가 0일 경우 엔딩 화면 표시
        except Exception as e:
            self.story_display.appendPlainText(f"[ERROR] 이야기 전송 중 문제 발생: {str(e)}\n")

    def show_ending(self):
        """엔딩 화면 표시"""
        self.ending_screen = EndingScreen(self.sock, self.genre, self.first_screen)
        self.ending_screen.show()
        self.close()


class EndingScreen(QDialog):
    def __init__(self, sock, genre, first_screen):
        super().__init__()
        try:
            uic.loadUi(get_ui_path('엔딩.ui'), self)
            print("[DEBUG] 엔딩 화면 UI 로드 성공")
        except Exception as e:
            print(f"[ERROR] 엔딩 화면 UI 로드 실패: {str(e)}")
            raise
        self.sock = sock
        self.genre = genre
        self.first_screen = first_screen  # 첫 화면 참조 저장
        self.init_ui()

    def init_ui(self):
        """엔딩 화면 초기화 및 버튼 동작 설정"""
        try:
            print("[DEBUG] 엔딩 생성 요청")
            model = genai.GenerativeModel("gemini-pro")
            chat = model.start_chat(history=[])
            response = chat.send_message(
                content=f"앞에 내용을 토대로 장르 '{self.genre}'에 맞춰 5줄로 이야기를 마무리해주세요."
            )
            ending_text = response.text.strip()
            self.ending_message.setPlainText(ending_text)
        except Exception as e:
            self.ending_message.setPlainText(f"[ERROR] 엔딩 생성 실패: {str(e)}")

        self.restart_button.clicked.connect(self.restart_program)
        self.close_button.clicked.connect(self.close_program)

    def restart_program(self):
        """프로그램 재시작"""
        print("[DEBUG] 프로그램 재시작")
        self.close()
        self.first_screen.show()  # 첫 화면 다시 표시

    def close_program(self):
        """프로그램 종료"""
        print("[DEBUG] 프로그램 종료")
        self.close()
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    HOST = '127.0.0.1'
    PORT = 5000

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((HOST, PORT))
        print("[DEBUG] 서버 연결 성공")
    except Exception as e:
        print(f"[ERROR] 서버 연결 실패: {str(e)}")
        sys.exit("서버에 연결할 수 없습니다.")

    try:
        first_screen = FirstScreen(client_socket)
        first_screen.show()
        print("[DEBUG] 첫 화면 표시 성공")
        app.exec()
    except Exception as e:
        print(f"[ERROR] 프로그램 실행 중 예외 발생: {str(e)}")
    finally:
        if client_socket:
            print("[DEBUG] 프로그램 종료 시 소켓 상태 확인")
            try:
                client_socket.close()
                print("[DEBUG] 소켓 닫힘 완료")
            except Exception as e:
                print(f"[ERROR] 소켓 닫기 중 문제 발생: {str(e)}")
