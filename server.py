import socket
import threading
import google.generativeai as genai
import re  # 응답 필터링용

# Gemini API 키 설정
GOOGLE_API_KEY = "YOUR_API_KEY"
genai.configure(api_key=GOOGLE_API_KEY)


def clean_ai_response(response):
    """AI 응답에서 불필요한 문구 제거"""
    # "또 다른 문장", "선택지", "다른 경우" 등과 관련된 표현 필터링
    cleaned_response = re.sub(r"(또 다른 문장:|선택지:|다른 경우:).*", "", response)
    return cleaned_response.strip()


def handle_client(client_socket, addr):
    print(f"[DEBUG] 클라이언트 연결됨: {addr}")

    try:
        # Gemini 모델 초기화 및 대화 시작
        model = genai.GenerativeModel("gemini-pro")
        chat = model.start_chat(history=[])

        while True:
            try:
                # 클라이언트로부터 메시지 받기
                data = client_socket.recv(1024).decode('utf-8')
                print(f"[DEBUG] 클라이언트 요청 수신: {data}")

                if not data or data.lower() == "exit":
                    print(f"[DEBUG] 클라이언트 연결 종료: {addr}")
                    break

                # 요청 처리
                request_type, content = data.split('|', 1)
                if request_type == "INIT":
                    genre, initial_setting = content.split('|', 1)
                    print(f"[DEBUG] INIT 요청 - 장르: {genre}, 초기 설정: {initial_setting}")
                    prompt = (
                        f"장르: {genre}\n"
                        f"초기 설정: {initial_setting}\n"
                        f"3줄 이내로 하나의 연속적인 이야기를 작성하세요. "
                        f"선택지나 여러 가지 경우를 제안하지 마세요."
                    )
                elif request_type == "CONTINUE":
                    genre, user_input = content.split('|', 1)
                    print(f"[DEBUG] CONTINUE 요청 - 장르: {genre}, 사용자 입력: {user_input}")
                    prompt = (
                        f"장르: {genre}\n"
                        f"사용자가 작성한 내용: {user_input}\n"
                        f"3줄 이내로 후속 이야기를 작성하세요. "
                        f"선택지나 여러 가지 경우를 제안하지 마세요."
                    )
                else:
                    client_socket.send("ERROR|잘못된 요청 유형입니다.".encode('utf-8'))
                    continue

                print(f"[DEBUG] 생성할 프롬프트: {prompt}")

                # Gemini API로 응답 생성
                try:
                    print(f"[DEBUG] Gemini API 호출 시작")
                    response = chat.send_message(prompt)
                    story = response.text.strip()

                    # 응답이 비어 있거나 None일 경우 처리
                    if not story:
                        print("[ERROR] AI 응답이 비어 있습니다.")
                        client_socket.send("ERROR|AI 응답이 비어 있습니다.".encode('utf-8'))
                        continue

                    cleaned_story = clean_ai_response(story)  # 응답 필터링
                    print(f"[DEBUG] AI 생성 성공: {cleaned_story}")
                    client_socket.send(f"OK|{cleaned_story}".encode('utf-8'))
                except Exception as e:
                    print(f"[ERROR] Gemini API 호출 실패: {str(e)}")
                    client_socket.send(f"ERROR|AI 생성 실패: {str(e)}".encode('utf-8'))

            except ValueError as ve:
                print(f"[ERROR] 잘못된 요청 데이터 형식: {ve}")
                client_socket.send("ERROR|잘못된 요청 데이터 형식입니다.".encode('utf-8'))
            except ConnectionResetError:
                print(f"[DEBUG] 클라이언트 연결 종료: {addr} (ConnectionResetError)")
                break
            except Exception as e:
                print(f"[ERROR] 요청 처리 중 오류 발생: {str(e)}")
                break
    except Exception as e:
        print(f"[ERROR] 클라이언트 처리 중 오류 발생: {str(e)}")
    finally:
        client_socket.close()
        print(f"[DEBUG] 클라이언트 연결 종료: {addr}")


def start_server():
    HOST = '127.0.0.1'  # 서버 IP
    PORT = 5000  # 포트 번호

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"[DEBUG] 서버 시작됨: {HOST}:{PORT}에서 대기 중...")

    try:
        while True:
            client_socket, addr = server_socket.accept()
            print(f"[DEBUG] 클라이언트 연결 수락: {addr}")
            client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            client_thread.start()
    except KeyboardInterrupt:
        print("\n[DEBUG] 서버 종료 중...")
    finally:
        server_socket.close()


if __name__ == "__main__":
    start_server()
