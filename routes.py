import os
import requests
import base64
import json
import datetime
import cv2
from flask import request, jsonify, send_from_directory, render_template

from config import FHIR_SERVER_URL, FACES_DIR 
from db_manager import register_or_update_patient, check_patient_exists, send_to_fhir_server
from face_recognizer import train_model_process, recognize_face, detect_and_crop_face

# ====================================================
# [유틸] 이미지 저장 함수
# ====================================================
def imwrite_safe(path, img):
    try:
        result, encoded_img = cv2.imencode('.jpg', img)
        if result:
            with open(path, mode='wb') as f:
                encoded_img.tofile(f)
            return True
        return False
    except Exception as e:
        print(f"❌ 저장 실패: {e}")
        return False

# ====================================================
# [유틸] 전각 숫자를 반각 숫자로 변환
# ====================================================
def normalize_patient_id(pid):
    """전각 숫자(１２３)를 반각 숫자(123)로 변환합니다."""
    if not pid:
        return pid
    return str(pid).translate(str.maketrans('０１２３４５６７８９', '0123456789')).strip()

# ====================================================
# [유틸] FHIR 환자 이름 추출 함수
# ====================================================
def extract_patient_name(fhir_data):
    """FHIR Patient 리소스에서 이름을 추출합니다."""
    try:
        if 'name' in fhir_data and fhir_data['name']:
            name_obj = fhir_data['name'][0]
            
            # text 필드가 있으면 그것을 사용
            if 'text' in name_obj and name_obj['text']:
                return name_obj['text']
            
            # 없으면 family + given 조합
            family = name_obj.get('family', '')
            given = name_obj.get('given', [])
            given_name = given[0] if given else ''
            
            # family와 given을 조합 (한국식 이름은 family가 성)
            full_name = f"{family} {given_name}".strip()
            return full_name if full_name else "Unknown"
    except Exception as e:
        print(f"⚠️ 이름 추출 오류: {e}")
    
    return "Unknown"

# ====================================================
# [Flask 라우트 정의]
# ====================================================
def init_routes(app):
    
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/view/patient/<int:pid>')
    def view_patient_from_fhir(pid):
        return render_template('patient_view.html', pid=pid, target_url=f"{FHIR_SERVER_URL}/Patient/{pid}")

    @app.route('/check_patient_id', methods=['POST'])
    def check_patient_id_route():
        try:
            pid = normalize_patient_id(request.json.get('patient_id', ''))
            
            if not pid:
                return jsonify({"status": "error", "exists": False, "message": "ID가 입력되지 않았습니다."})

            exists, last_updated = check_patient_exists(pid)
            name = "Unknown"

            # 1. 로컬 DB에 존재하면 FHIR에서 이름 가져오기
            if exists:
                try:
                    r = requests.get(f"{FHIR_SERVER_URL}/Patient/{pid}", timeout=3)
                    if r.status_code == 200:
                        fhir_data = r.json()
                        name = extract_patient_name(fhir_data)
                        print(f"[DEBUG] 환자 {pid} 이름: {name}")
                except Exception as e:
                    print(f"⚠️ FHIR 서버 연결 실패: {e}")
                    pass  # FHIR 서버 연결 실패해도 로컬에 있으니 일단 진행
                
                return jsonify({
                    "status": "success", 
                    "exists": True, 
                    "name": name, 
                    "last_updated": str(last_updated)
                })

            # 2. 로컬 DB에 없으면 FHIR 서버에 조회
            try:
                r = requests.get(f"{FHIR_SERVER_URL}/Patient/{pid}", timeout=3)
                if r.status_code == 200:
                    # FHIR 서버에 존재하면, 로컬 DB에 자동 등록하고 성공 처리
                    register_or_update_patient(pid)
                    fhir_data = r.json()
                    name = extract_patient_name(fhir_data)
                    print(f"[DEBUG] 신규 등록 환자 {pid} 이름: {name}")
                    
                    return jsonify({
                        "status": "success", 
                        "exists": True, 
                        "name": name, 
                        "last_updated": str(datetime.datetime.now())
                    })
            except Exception as e:
                print(f"⚠️ FHIR 서버 조회 실패: {e}")

            # 3. 두 곳 모두 없으면 최종적으로 실패 처리
            return jsonify({"status": "error", "exists": False, "message": "ID 없음"})
            
        except Exception as e:
            print(f"❌ check_patient_id 오류: {e}")
            return jsonify({"status": "error", "message": str(e)})

    @app.route('/create_fhir_patient', methods=['POST'])
    def create_fhir_patient():
        try:
            data = request.json 
            input_name = data.get('name', 'Unknown')
            input_city = data.get('city', 'Unknown')
            if not input_city: input_city = "Unknown"

            fhir_template = {
                "resourceType": "Patient", "active": True,
                "name": [{"use": "official", "family": input_name, "given": ["NFN"]}],
                "gender": data.get('gender', 'unknown'),
                "birthDate": data.get('birthDate', '1900-01-01'),
                "address": [{"use": "home", "line": ["Unknown"], "city": input_city}],
                "telecom": [{"system": "phone", "value": "000-0000-0000", "use": "mobile"}],
                "extension": []
            }
            
            def add_ext(url_suffix, val):
                if val: fhir_template["extension"].append({"url": f"http://hospital.org/{url_suffix}", "valueString": val})
            
            add_ext("blood-type", data.get('bloodType'))
            add_ext("pregnancy", data.get('pregnancyStatus'))
            add_ext("allergy-summary", data.get('allergies'))
            add_ext("medication-summary", data.get('medications'))
            add_ext("condition-summary", data.get('diagnosis'))

            success, result = send_to_fhir_server(fhir_template)
            
            if success:
                pid = result.get('id')
                register_or_update_patient(pid)
                return jsonify({"status": "success", "patient_id": pid})
            
            return jsonify({"status": "error", "message": str(result)}), 500
        except Exception as e: 
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/proxy/patient/<pid>')
    def proxy_patient_data(pid):
        try:
            r = requests.get(f"{FHIR_SERVER_URL}/Patient/{pid}", timeout=5)
            return (r.content, r.status_code, {'Content-Type': 'application/json'})
        except: return jsonify({"error": "FHIR Server Error"}), 500

    @app.route('/register_face', methods=['POST'])
    def register_face_route():
        try:
            d = request.json
            img_data = base64.b64decode(d['image'].split(',')[1])
            pid = normalize_patient_id(d.get('id'))
            register_or_update_patient(pid)
            face, _ = detect_and_crop_face(img_data)
            if face is not None:
                os.makedirs(FACES_DIR, exist_ok=True)
                count = len([f for f in os.listdir(FACES_DIR) if f.startswith(f"{pid}_")])
                save_path = os.path.join(FACES_DIR, f"{pid}_{count}.jpg")
                imwrite_safe(save_path, face)
                return jsonify({"status": "ok", "msg": f"Saved {count}"})
            return jsonify({"status": "fail", "message": "No face"})
        except Exception as e: return jsonify({"status": "error", "message": str(e)})

    @app.route('/train_model', methods=['POST'])
    def train_model_route():
        print("[SERVER] 모델 학습 시작")
        success, msg = train_model_process()
        return jsonify({"status": "success" if success else "fail", "message": msg})

    @app.route('/identify_face', methods=['POST'])
    def identify_face_route():
        try:
            d = request.json
            img_data = base64.b64decode(d['image'].split(',')[1])
            
            face_roi, rect = detect_and_crop_face(img_data)
            
            if face_roi is None:
                return jsonify({"status": "searching", "message": "얼굴 탐색 중..."})
            
            identified_id, conf = recognize_face(face_roi)
            
            if identified_id:
                return jsonify({
                    "status": "ok",
                    "action": "redirect",
                    "patient_id": identified_id,
                    "message": f"Found {identified_id}",
                    "confidence": conf
                })
            else:
                return jsonify({"status": "searching", "message": "Unknown"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    @app.route('/face_image/<int:pid>')
    def get_face_image(pid):
        if not os.path.exists(FACES_DIR): return '', 404
        fs = [f for f in os.listdir(FACES_DIR) if f.startswith(f"{pid}_")]
        if fs:
            fs.sort() 
            return send_from_directory(FACES_DIR, fs[0])
        return ('', 404)