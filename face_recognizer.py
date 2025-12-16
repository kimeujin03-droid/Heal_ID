import cv2
import os
import numpy as np
from config import FACES_DIR, MODEL_FILE
import db_manager 

# ========================================================
# [최적화] 전역 변수 초기화 (서버 시작 시 1회만 로드하여 속도 향상)
# ========================================================
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
recognizer = cv2.face.LBPHFaceRecognizer_create()

# 서버 시작 시, 기존에 학습된 모델 파일이 있다면 미리 메모리에 올립니다.
if os.path.exists(MODEL_FILE):
    try:
        recognizer.read(MODEL_FILE)
        print(f"[INIT] 기존 모델 로드 완료: {MODEL_FILE}")
    except Exception as e:
        print(f"[INIT] 모델 로드 실패 (재학습 필요): {e}")


def get_label_id_map():
    """DB에서 '모델 라벨(숫자)'과 '환자 ID' 매핑 정보를 가져옵니다."""
    conn, cursor = db_manager.get_db_connection()
    if not conn: return {}
    try:
        cursor.execute("SELECT id, model_label FROM patients WHERE model_label IS NOT NULL")
        mapping = {row['model_label']: row['id'] for row in cursor.fetchall()}
        return mapping
    except: return {}
    finally:
        if conn: conn.close()

def imread_safe(path):
    """한글 경로 등에서 이미지를 안전하게 읽어오는 함수"""
    try:
        stream = open(path, "rb")
        bytes = bytearray(stream.read())
        numpyarray = np.asarray(bytes, dtype=np.uint8)
        return cv2.imdecode(numpyarray, cv2.IMREAD_GRAYSCALE)
    except Exception as e:
        print(f"❌ 이미지 읽기 실패 ({path}): {e}")
        return None

def train_model_process():
    """DB에 등록된 환자들의 얼굴 이미지를 읽어 모델을 학습시킵니다."""
    faces = []
    labels = []
    
    # [수정 완료] count 변수 초기화 (중요)
    count = 0 

    if not os.path.exists(FACES_DIR):
        return False, "Faces 폴더가 없습니다."

    conn, cursor = db_manager.get_db_connection()
    if not conn: return False, "DB 연결 실패"

    try:
        # 1. 기존 라벨 초기화 (충돌 방지용)
        cursor.execute("UPDATE patients SET model_label = NULL")
        conn.commit()

        # 2. 환자 목록 가져오기
        cursor.execute("SELECT id FROM patients ORDER BY id ASC")
        patients = cursor.fetchall()
        
        print("[INFO] 학습 데이터 스캔 중... (라벨 = 환자ID)")
        
        for patient in patients:
            pid = patient['id']
            
            # 환자 ID를 그대로 라벨로 사용 (숫자만 가능)
            model_label = int(pid) 
            
            # 해당 ID로 시작하는 파일 찾기
            patient_imgs = [f for f in os.listdir(FACES_DIR) if f.startswith(f"{pid}_")]
            
            has_images = False
            for file_name in patient_imgs:
                path = os.path.join(FACES_DIR, file_name)
                img_numpy = imread_safe(path)
                
                if img_numpy is not None:
                    faces.append(img_numpy)
                    labels.append(model_label)
                    count += 1
                    has_images = True
            
            # 이미지가 있는 경우에만 DB에 라벨(ID와 동일) 저장
            if has_images:
                cursor.execute("UPDATE patients SET model_label = %s WHERE id = %s", (model_label, pid))
        
        conn.commit()
        
        if count == 0:
            return False, "학습할 유효한 이미지가 없습니다."

        # 3. 모델 학습
        recognizer.train(faces, np.array(labels))
        
        # 파일로 저장
        recognizer.write(MODEL_FILE)
        
        print(f"✅ 모델 학습 완료: 총 {count}장 (라벨=ID 동기화됨)")
        return True, f"총 {count}장 학습 완료"

    except Exception as e:
        print(f"❌ 학습 중 에러: {e}")
        return False, str(e)
    finally:
        if conn: conn.close()

def recognize_face(face_img):
    """입력된 얼굴 이미지로 환자를 식별합니다."""
    try:
        # [최적화] 매번 파일을 읽지 않고, 전역 변수 recognizer를 사용합니다.
        
        # 아직 모델이 학습되지 않았거나 로드되지 않은 경우 예외 처리
        try:
            label, conf = recognizer.predict(face_img)
        except cv2.error:
            return None, "모델이 학습되지 않음"
        
        # 신뢰도 체크 (낮을수록 정확, 보통 50~80 사이를 임계값으로 잡음)
        if conf < 100:
            # 라벨 -> 환자 ID 매핑 확인
            mapping = get_label_id_map()
            patient_id = mapping.get(label)
            
            if patient_id:
                return patient_id, conf
            else:
                # 매핑 정보가 없으면 라벨(ID) 그대로 리턴
                return str(label), conf
        else:
            return None, "Low Confidence"
    except Exception as e:
        print(f"Recognize Error: {e}")
        return None, "Error"

def detect_and_crop_face(image_data):
    """이미지 바이너리 데이터에서 얼굴을 찾아 크롭하여 반환합니다."""
    try:
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    except:
        return None, None

    # [최적화] 전역 변수로 로드된 face_cascade 사용
    faces = face_cascade.detectMultiScale(img, 1.1, 5, minSize=(30, 30))

    if len(faces) > 0:
        # 가장 큰 얼굴 영역을 선택
        x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
        face_roi = img[y:y+h, x:x+w]
        return face_roi, img
    
    return None, img