import os

# [설정] DB 및 경로
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Hanyoon1*',
    'database': 'heal_id'
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACES_DIR = os.path.join(BASE_DIR, 'Faces')
MODEL_FILE = os.path.join(BASE_DIR, 'desa.yml')

FHIR_SERVER_URL = "http://cpslab.jejunu.ac.kr:10002/hapi-fhirstarters-simple-server"

if not os.path.exists(FACES_DIR):
    os.makedirs(FACES_DIR)