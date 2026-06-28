import socket
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LIVESPLIT_HOST = '127.0.0.1'
LIVESPLIT_PORT = 16834

@app.route('/api/bestpossibletime', methods=['GET'])
def get_best_possible_time():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect((LIVESPLIT_HOST, LIVESPLIT_PORT))
            s.send(b"getbestpossibletime\r\n")
            response = s.recv(1024).decode('utf-8').strip()

            if not response or "Unknown command" in response:
                return jsonify({"success": False, "error": "Commande inconnue par LiveSplit"}), 200

            return jsonify({"success": True, "time": response})

    except ConnectionRefusedError:
        print("LiveSplit Server n'est pas lancé.")
        return jsonify({"success": False, "error": "Serveur non démarré"}), 200
    except Exception as e:
        print(f"Erreur : {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8084)
