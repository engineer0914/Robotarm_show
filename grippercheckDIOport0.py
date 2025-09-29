# 필요한 라이브러리 임포트
# import serial # 시리얼 통신은 사용하지 않으므로 주석 처리
import socket # 로봇 스크립트 명령 전송을 위한 소켓 통신
import rbpodo as rb # 레인보우 로보틱스 코봇 제어 라이브러리
import numpy as np # 수치 계산 (배열 등)
import time # 시간 지연 사용

# ======= 설정 부분 =======
ROBOT_IP = "192.168.0.21" # 로봇 제어기의 실제 IP 주소로 변경하세요. (예: "10.0.2.7" 등)
# 소켓 통신에 사용할 포트 (로봇 스크립트 인터페이스 포트일 가능성 높음)
# 로봇 매뉴얼에서 스크립트 인터페이스 포트를 확인하세요.
SOCKET_PORT = 5000 
# =======================

# 로봇 연결 (스크립트 시작 시 한 번 실행)
# rbpodo 라이브러리 연결
print(f"로봇에 연결 중... IP: {ROBOT_IP}")
robot = rb.Cobot(ROBOT_IP)
rc = rb.ResponseCollector()
print("로봇 연결 성공.")

# 작동 모드 설정 (스크립트 시작 시 한 번 실행)
# 로봇을 실제로 움직입니다! 주변 안전 확인 필수!
print("작동 모드를 Real으로 설정합니다. (로봇이 실제 움직입니다!)")
robot.set_operation_mode(rc, rb.OperationMode.Real)
#rc.error().throw_if_not_empty() # 에러 발생 시 스크립트 즉시 중단

# 전체 이동 속도 오버라이드 설정 (0.0 ~ 1.0) (스크립트 시작 시 한 번 실행)
# 실제 움직일 때는 낮은 값(예: 0.1 ~ 0.3)으로 시작하는 것이 안전합니다.
speed_override = 1
print(f"전체 속도 오버라이드 설정: {speed_override*100:.0f}%")
robot.set_speed_bar(rc, speed_override)
#rc.error().throw_if_not_empty() # 에러 발생 시 스크립트 즉시 중단

# 소켓 연결 (스크립트 시작 시 한 번 실행)
# 로봇 스크립트 명령 전송을 위한 소켓 연결
try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((ROBOT_IP, SOCKET_PORT))
    print(f"로봇 스크립트 서버에 소켓 연결되었습니다. IP: {ROBOT_IP}, Port: {SOCKET_PORT}")
except socket.error as e:
    print(f"로봇 스크립트 서버 소켓 연결 실패: {e}")
    print("move_l_relative 함수는 작동하지 않습니다.")
    client_socket = None # 연결 실패 시 None으로 설정

# 소켓을 통해 로봇 스크립트 명령 전송 함수
def send_command(command):
    """
    로봇 스크립트 명령어를 소켓을 통해 전송하고 응답을 받습니다.
    """
    if client_socket is None:
        print("소켓 연결이 활성화되지 않아 명령을 보낼 수 없습니다.")
        return "Error: Socket not connected"
        
    try:
        client_socket.sendall(command.encode())
        # TODO: 로봇 응답 크기를 정확히 확인하고 필요하다면 반복 수신
        # 현재는 최대 1024 바이트만 수신합니다.
        response = client_socket.recv(1024).decode()
        # print(f"Sent: {command.strip()}, Recv: {response.strip()}") # 디버깅용
        return response
    except socket.error as e:
        print(f"명령 전송/수신 중 소켓 오류 발생: {e}")
        #raise # 필요하다면 예외를 다시 발생
        return "Error: Socket communication failed"


# 로봇 스크립트 명령 실행 완료 대기 함수 (모션 변경 감지)
# 이 함수는 로봇이 움직임을 시작하거나 멈출 때 보내는 특정 메시지를 감지합니다.
# 모든 명령의 실행 완료를 보장하지 않을 수 있으며, 로봇 스크립트 인터페이스의
# 응답 방식에 따라 더 견고한 대기/완료 확인 로직이 필요할 수 있습니다.
def wait_for_motion(timeout=10.0):
    """
    로봇의 모션 상태 변경 메시지를 수신할 때까지 대기합니다.
    
    Args:
        timeout (float): 대기할 최대 시간 (초).
    Returns:
        bool: 모션 변경 메시지를 감지했으면 True, 타임아웃되면 False.
    """
    if client_socket is None:
        print("소켓 연결이 활성화되지 않아 모션 완료를 대기할 수 없습니다.")
        return False

    print("[wait_for_motion] 로봇 모션 완료 대기...")
    # 소켓 수신에 타임아웃 설정 (무한 대기 방지)
    client_socket.settimeout(timeout)
    start_time = time.time()

    try:
        # TODO: 더 견고한 파싱 로직 필요. 현재는 문자열 포함 여부만 확인.
        while time.time() - start_time < timeout:
            data = client_socket.recv(1024).decode()
            if "info[motion_changed][0]" in data:
                #print("[wait_for_motion] 모션 변경 감지.") # 디버깅용
                client_socket.settimeout(None) # 타임아웃 설정 해제
                return True
            # print(f"[wait_for_motion] 수신 데이터: {data.strip()}") # 디버깅용
        
        print(f"[wait_for_motion] 타임아웃 ({timeout}s)으로 모션 변경 감지 실패.")
        client_socket.settimeout(None) # 타임아웃 설정 해제
        return False # 타임아웃

    except socket.timeout:
        print(f"[wait_for_motion] 소켓 수신 타임아웃 ({timeout}s).")
        client_socket.settimeout(None) # 타임아웃 설정 해제
        return False
    except socket.error as e:
        print(f"[wait_for_motion] 수신 중 소켓 오류 발생: {e}")
        client_socket.settimeout(None) # 타임아웃 설정 해제
        #raise # 필요하다면 예외 다시 발생
        return False


# 관절 공간 이동 함수 (rbpodo 사용)
def mmove_j(angles_j, speed_j, acceleration_j):
    """
    로봇을 목표 관절 각도로 이동시키는 함수.

    Args:
        angles_j (np.array): 목표 관절 각도 리스트 (6개 요소, 도 단위).
        speed_j (float): 이동 속도 (deg/s).
        acceleration_j (float): 가속도 (deg/s^2).
    Raises:
        Exception: 로봇 명령 실행 중 오류 발생 시.
    """
    print(f"\n--- [mmove_j] 로봇을 목표 관절 위치로 이동 ---")
    print(f"  목표 각도: {angles_j}")
    print(f"  속도: {speed_j} deg/s, 가속도: {acceleration_j} deg/s^2")

    try:
        # 관절 공간 이동 명령 전송
        robot.move_j(rc, angles_j, speed_j, acceleration_j)

        # 명령 버퍼 플러시 및 에러 확인
        # move_j 명령은 버퍼에 담길 수 있으므로 플러시하여 즉시 전송
        robot.flush(rc)
        rc.error().throw_if_not_empty()
        rc.clear() # 응답 수집기 초기화

        # 이동 시작 및 완료 대기
        print("  로봇 이동 시작 대기...")
        # 로봇이 움직이기 시작할 때까지 대기 (타임아웃 설정)
        if robot.wait_for_move_started(rc, 5.0).is_success(): # 5초 안에 시작 안 하면 실패
            print("  로봇 이동 시작 감지.")
            print("  로봇 이동 완료 대기...")
            # 로봇이 움직임을 마칠 때까지 대기
            robot.wait_for_move_finished(rc)
            print("--- [mmove_j] 로봇 이동 완료 ---")
        else:
            print("--- [mmove_j] 로봇 이동 시작 실패 또는 타임아웃 ---")
            rc.error().throw_if_not_empty() # 이동 시작 실패 시 에러 확인 (raise 발생)

    except Exception as e:
        print(f"--- [mmove_j] 이동 중 오류 발생: {e} ---")
        raise # 예외를 다시 발생시켜 호출자에서 처리하도록 함


# 직교 공간 상대 직선 이동 함수 (로봇 스크립트 move_l_rel 사용)
# 이 함수는 소켓 통신 (send_command, wait_for_motion)을 사용합니다.
def mmove_l_relative(displacement_vector, speed_l, acceleration_l, coordinate_system_index):
    """
    로봇 TCP를 현재 위치에서 지정된 좌표계 기준으로 상대 직선 이동시키는 함수.
    로봇 스크립트 명령어 move_l_rel을 소켓 통신으로 전송합니다.

    Args:
        displacement_vector (list or np.array): 상대 이동 변위 [dx, dy, dz, drx, dry, drz] (mm, degree 단위).
        speed_l (float): 이동 속도 (mm/s).
        acceleration_l (float): 가속도 (mm/s^2).
        coordinate_system_index (int): 상대 이동의 기준이 될 좌표계 인덱스 (예: 0: Base, 1: Tool, 2: User 0... 등).
                                       로봇 매뉴얼에서 move_l_rel 명령어 설명을 반드시 확인하세요.
    Raises:
        Exception: 명령 전송 또는 실행 중 오류 발생 시 (소켓 오류 포함).
    """
    print(f"\n--- [mmove_l_relative] 로봇 TCP 상대 이동 ---")
    print(f"  변위: {displacement_vector}")
    print(f"  기준 좌표계 인덱스: {coordinate_system_index}")
    print(f"  속도: {speed_l} mm/s, 가속도: {acceleration_l} mm/s^2")

    try:
        # 스크립트 명령어 형식으로 변위 벡터 문자열 생성
        disp_str = ", ".join(map(str, displacement_vector))
        command = f'move_l_rel(pnt[{disp_str}], {speed_l}, {acceleration_l}, {coordinate_system_index})'

        # 로봇 스크립트 인터페이스로 명령 전송 (소켓 통신)
        response = send_command(command)
        print(f"  Command sent: {command}")
        print(f"  Response: {response.strip()}") # 로봇 응답 확인 (성공/실패 등)

        # TODO: 로봇 응답(response)을 분석하여 명령이 성공적으로 받아들여졌는지 확인하는 로직 추가
        # send_command의 응답은 명령 수신 확인일 수 있으며, 실제 실행 성공을 의미하지 않을 수 있습니다.

        # 이동 완료 대기 (소켓 통신으로 모션 완료 메시지 감지)
        # wait_for_motion 함수는 소켓으로부터 "info[motion_changed][0]"를 기다립니다.
        # 이 메시지가 항상 이동 완료를 정확히 의미하는지 로봇 매뉴얼 확인 필요.
        if not wait_for_motion():
             # 타임아웃 등으로 모션 완료 감지 실패 시
             print("--- [mmove_l_relative] 모션 완료 감지 실패 또는 타임아웃 ---")
             # 필요하다면 여기서 에러 처리 또는 예외 발생
             # raise Exception("Motion completion not detected") # 예: 강제 예외 발생

        print("--- [mmove_l_relative] 로봇 상대 이동 완료 ---")

    except Exception as e:
        print(f"--- [mmove_l_relative] 상대 이동 중 오류 발생: {e} ---")
        # 소켓 통신 에러, send_command/wait_for_motion 에러 등을 포함
        raise # 예외를 다시 발생시켜 호출자에서 처리하도록 함

def grip(ord):
    if(ord == "release"):
        robot.set_dout_bit_combination(rc, 0, 3, 1, rb.Endian.LittleEndian)
        # time.sleep(0.1)
        # robot.set_dout_bit_combination(rc, 0, 3, 0, rb.Endian.LittleEndian)

    elif(ord == "grab"):
        robot.set_dout_bit_combination(rc, 0, 3, 2, rb.Endian.LittleEndian)
        time.sleep(0.1)
        robot.set_dout_bit_combination(rc, 0, 3, 0, rb.Endian.LittleEndian)
        
    else:
        return

pose_initiate = np.array([-135.0, 0.0, 90.0, 0.0, 90.0, 45.0])

pose_desk = {}

pose_desk[(0, 1)] = np.array([-166.67, 37.03, 94.11, -41.15, 89.96, 76.46]) # 1.1
pose_desk[(0, 2)] = np.array([-138.44, 51.74, 65.89, -27.64, 89.96, 48.44]) # 2.1
pose_desk[(0, 3)] = np.array([-88.57, 15.13, 131.94, -57.08, 89.96, -1.42]) # 3.1

pose_desk[(0, 4)] = np.array([-162.40, 25.28, 122.86, -58.15, 89.97, 72.86])

pose_desk[(0, 5)] = np.array([-129.54, 37.06, 94.07, -41.13, 89.96, 39.54]) # 2.3 middle

relative_coord_system_index = 2 # z axis move

md_distance = 40.0

def initiate_pose_set():
    # ======= 1. 초기 관절 위치로 이동 =======
    initial_angles_j = pose_initiate
    move_j_speed_init = 30 # 초기 이동 속도
    move_j_acceleration_init = 30 # 초기 이동 가속도
    # mmove_j(initial_angles_j, move_j_speed_init, move_j_acceleration_init)
    return

    grip("release")

    time.sleep(1)

    grip("grab")

def cycle_1():

    move_j_speed_init = 150 # 초기 이동 속도
    move_j_acceleration_init = 150 # 초기 이동 가속도

    relative_move_speed = 300 # 상대 이동 속도 (mm/s)
    relative_move_acceleration = 300 # 상대 이동 가속도 (mm/s^2)

    grip("release")


    # initial_angles_j = pose_desk[(0, 1)]
    # mmove_j(initial_angles_j, move_j_speed_init, move_j_acceleration_init)

    while True:

        grip("grab")

        time.sleep(5)
        
        grip("release")
        
        time.sleep(5)

    return  

def unitmove(num):

        move_j_speed_init = 150 # 초기 이동 속도
        move_j_acceleration_init = 150 # 초기 이동 가속도

        relative_move_speed = 300 # 상대 이동 속도 (mm/s)
        relative_move_acceleration = 300 # 상대 이동 가속도 (mm/s^2)

        relative_displacement_down_10cm = [0.0, 0.0, -md_distance, 0.0, 0.0, 0.0]
        mmove_l_relative(relative_displacement_down_10cm, relative_move_speed, relative_move_acceleration, relative_coord_system_index)

        grip("grab")

        relative_displacement_down_10cm = [0.0, 0.0, md_distance, 0.0, 0.0, 0.0]
        mmove_l_relative(relative_displacement_down_10cm, relative_move_speed, relative_move_acceleration, relative_coord_system_index)


        initial_angles_j = pose_desk[(0, num)]
        mmove_j(initial_angles_j, move_j_speed_init, move_j_acceleration_init)

        relative_displacement_down_10cm = [0.0, 0.0, -md_distance, 0.0, 0.0, 0.0]
        mmove_l_relative(relative_displacement_down_10cm, relative_move_speed, relative_move_acceleration, relative_coord_system_index)

        grip("release")

        relative_displacement_down_10cm = [0.0, 0.0, md_distance, 0.0, 0.0, 0.0]
        mmove_l_relative(relative_displacement_down_10cm, relative_move_speed, relative_move_acceleration, relative_coord_system_index)

        return




# 메인 실행 로직
def main():

    initiate_pose_set()
    print("=== 로봇 이동 스크립트 시작 ===")

    cycle_1()
    
    
    
    
    
    
if __name__ == "__main__":
    main()
