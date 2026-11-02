import os
import time
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

app = Flask(__name__)
STORE_DIR = "store"
NONCE = b"ICA BOSSSSSS"  # Exatamente 12 bytes compatíveis com o Go

if not os.path.exists(STORE_DIR):
    os.makedirs(STORE_DIR)

def encrypt(data: str, key: str) -> str:
    aesgcm = AESGCM(key.encode('utf-8'))
    encrypted = aesgcm.encrypt(NONCE, data.encode('utf-8'), None)
    return encrypted.hex()

def decrypt(encrypted_hex: str, key: str) -> str:
    aesgcm = AESGCM(key.encode('utf-8'))
    encrypted_bytes = bytes.fromhex(encrypted_hex)
    decrypted = aesgcm.decrypt(NONCE, encrypted_bytes, None)
    return decrypted.decode('utf-8')

@app.route('/files', methods=['GET', 'POST'])
def handle_files():
    total_start = time.perf_counter_ns() // 1000  # microssegundos
    
    if not os.path.exists(STORE_DIR):
        os.makedirs(STORE_DIR)
        
    try:
        fs = os.listdir(STORE_DIR)
    except Exception as e:
        return jsonify({"error": f"store folder error: {str(e)}"}), 500

    if request.method == 'GET':
        start = time.perf_counter_ns() // 1000
        files_list = [f for f in fs if os.path.isfile(os.path.join(STORE_DIR, f))]
        read_fs_time = (time.perf_counter_ns() // 1000) - start
        
        total_time = (time.perf_counter_ns() // 1000) - total_start
        return jsonify({
            "files": files_list,
            "metrics": {
                "total": total_time,
                "readFileSystemEntries": read_fs_time,
                "readFile": 0,
                "writeFile": 0,
                "generateFile": 0,
                "encryption": 0,
                "decryption": 0,
                "unit": "microseconds"
            }
        }), 200

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        key = data.get('key', '')
        length = data.get('length', 0)
        file_name = data.get('fileName', '')
        pattern = data.get('pattern', 'a')  # Padrão por omissão é 'a' se não for fornecido

        if len(key) != 16:
            return "Key must be 16 bytes length", 400

        # Gerar conteúdo (suporta o novo campo content ou o fallback por length)
        start = time.perf_counter_ns() // 1000
        if not pattern:
            pattern = 'a'
        
        # Repete o padrão o número de vezes necessário e corta exatamenteto no 'length'
        file_content = (pattern * (length // len(pattern) + 1))[:length]
        gen_time = (time.perf_counter_ns() // 1000) - start

        # Cifrar
        try:
            start = time.perf_counter_ns() // 1000
            encrypted_content = encrypt(file_content, key)
            enc_time = (time.perf_counter_ns() // 1000) - start
        except Exception as e:
            return f"Failed to encrypt data: {str(e)}", 400

        # --- CÁLCULO DO THROUGHPUT ---
        data_size_bytes = len(file_content.encode('utf-8'))
        # Evitar divisão por zero se o tempo for 0 microssegundos
        safe_enc_time = enc_time if enc_time > 0 else 1
        # Throughput em Bytes por microssegundo (que equivale a Megabytes por segundo - MB/s)
        encryption_throughput = round((data_size_bytes / safe_enc_time), 2)

        # Escrever no disco
        try:
            start = time.perf_counter_ns() // 1000
            file_path = os.path.join(STORE_DIR, file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(encrypted_content)
            write_time = (time.perf_counter_ns() // 1000) - start
        except Exception as e:
            return f"Failed to write to disk: {str(e)}", 500

        total_time = (time.perf_counter_ns() // 1000) - total_start
        return jsonify({
            "metrics": {
                "total": total_time,
                "readFileSystemEntries": 0,
                "readFile": 0,
                "writeFile": write_time,
                "generateFile": gen_time,
                "encryption": enc_time,
                "encryptionThroughput": encryption_throughput,
                "unit": "microseconds",
                "throughputUnit": "MB/s"    
            }
        }), 201

@app.route('/files/<file_id>', methods=['GET'])
def handle_file(file_id):
    total_start = time.perf_counter_ns() // 1000

    data = request.get_json(silent=True) or {}
    key = data.get('key', '')

    if len(key) != 16:
        return "Key must be 16 bytes length", 400

    file_path = os.path.join(STORE_DIR, file_id)
    if not os.path.exists(file_path):
        return "Failed to get file", 500

    try:
        start = time.perf_counter_ns() // 1000
        with open(file_path, 'r', encoding='utf-8') as f:
            encrypted_content = f.read()
        read_time = (time.perf_counter_ns() // 1000) - start
    except Exception as e:
        return "Failed to get file", 500

    try:
        start = time.perf_counter_ns() // 1000
        file_content = decrypt(encrypted_content, key)
        dec_time = (time.perf_counter_ns() // 1000) - start
    except Exception as e:
        return f"Failed to decrypt data: {str(e)}", 400

    total_time = (time.perf_counter_ns() // 1000) - total_start
    return jsonify({
        "text": file_content,
        "metrics": {
            "total": total_time,
            "readFileSystemEntries": 0,
            "readFile": read_time,
            "writeFile": 0,
            "generateFile": 0,
            "encryption": 0,
            "decryption": dec_time,
            "unit": "microseconds"
        }
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)