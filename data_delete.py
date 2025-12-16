import os
import mysql.connector
import sys

# ========================================================
# 얼굴인식을 잘 못하는 경우 지워서 다시 학습시키기 위한 스크립트
# ========================================================

# DB 설정 (Manager.py와 동일)
DB_CONFIG = {
    
}

# 파일 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACES_DIR = os.path.join(BASE_DIR, 'Faces')
MODEL_FILE = os.path.join(BASE_DIR, 'desa.yml')  # 삭제할 모델 파일 경로 추가

# ========================================================
# 데이터 삭제 로직
# ========================================================

def delete_patient_data(patient_id):
    """데이터베이스, 파일 시스템, 그리고 학습 모델에서 관련 데이터를 삭제합니다."""
    print(f"\n🗑️ --- ID [{patient_id}] 환자 데이터 완전 삭제를 시작합니다. ---")

    # 1. 데이터베이스에서 환자 정보 삭제
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM patients WHERE id = %s", (patient_id,))
        if not cursor.fetchone():
            print(f"ℹ️ [DB] ID {patient_id} 환자는 데이터베이스에 없습니다.")
        else:
            cursor.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
            conn.commit()
            if cursor.rowcount > 0:
                print(f"✅ [DB] ID {patient_id} 환자 정보 삭제 완료.")

    except mysql.connector.Error as err:
        print(f"❌ [DB 오류] 데이터 삭제 중 오류 발생: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()

    # 2. 파일 시스템에서 얼굴 이미지 삭제
    if not os.path.exists(FACES_DIR):
        print(f"ℹ️ [파일] '{FACES_DIR}' 폴더가 존재하지 않습니다.")
    else:
        deleted_count = 0
        for filename in os.listdir(FACES_DIR):
            if filename.startswith(f"{patient_id}_"):
                try:
                    os.remove(os.path.join(FACES_DIR, filename))
                    deleted_count += 1
                except OSError as e:
                    print(f"❌ [파일 오류] '{filename}' 삭제 실패: {e}")
        
        if deleted_count > 0:
            print(f"✅ [파일] 얼굴 이미지 {deleted_count}장 삭제 완료.")
        else:
            print(f"ℹ️ [파일] 삭제할 얼굴 이미지가 없습니다.")

    # 3. 학습된 모델 파일(yml) 삭제 (추가된 부분)
    # 특정 환자만 모델에서 빼는 것은 어렵기 때문에, 모델 파일을 통째로 지워 재학습을 유도합니다.
    if os.path.exists(MODEL_FILE):
        try:
            os.remove(MODEL_FILE)
            print(f"⚠️ [모델] 기존 학습 파일('desa.yml')을 삭제했습니다.")
            print(f"   👉 중요: 'AI 모델 학습' 버튼을 다시 눌러주세요!")
        except OSError as e:
            print(f"❌ [모델 오류] 모델 파일 삭제 실패: {e}")
    else:
        print(f"ℹ️ [모델] 삭제할 모델 파일이 없습니다.")

    print(f"--- ID [{patient_id}] 삭제 작업 완료 ---\n")

if __name__ == "__main__":
    # 사용법 1 (인자 전달): python delete_patient_data.py 6 7 8
    # 사용법 2 (직접 입력): python delete_patient_data.py
    
    pids_to_delete = []

    if len(sys.argv) > 1:
        # 명령줄 인자로 ID 목록을 받은 경우
        try:
            pids_to_delete = [int(arg) for arg in sys.argv[1:]]
        except ValueError:
            print("❌ 오류: 모든 환자 ID는 숫자여야 합니다. 프로그램을 종료합니다.")
            sys.exit(1)
    else:
        # 인자가 없는 경우, 사용자에게 직접 입력을 받음
        print("💡 사용법: python delete_patient_data.py [ID1] [ID2] ...")
        id_input = input("👉 삭제할 환자 ID를 공백으로 구분하여 입력하세요 (예: 6 7 8) >> ")
        if id_input:
            try:
                pids_to_delete = [int(pid_str) for pid_str in id_input.split()]
            except ValueError:
                print("❌ 오류: 환자 ID는 숫자 형식이어야 합니다. 프로그램을 종료합니다.")
                sys.exit(1)

    if pids_to_delete:
        for pid in pids_to_delete:
            delete_patient_data(pid)
    else:

        print("ℹ️ 삭제할 ID가 입력되지 않았습니다. 프로그램을 종료합니다.")
