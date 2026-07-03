import socket
import threading
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LIVESPLIT_HOST = '127.0.0.1'
LIVESPLIT_PORT = 16834

# Connexion persistante à LiveSplit Server, réutilisée entre les requêtes.
# Ouvrir/fermer un socket à chaque appel (2x/s) fait timeout LiveSplit.
_sock = None
_lock = threading.Lock()


def _connect():
    global _sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    s.connect((LIVESPLIT_HOST, LIVESPLIT_PORT))
    _sock = s
    return s


def _close():
    global _sock
    if _sock is not None:
        try:
            _sock.close()
        finally:
            _sock = None


def _recv_line(s):
    """Lit jusqu'au retour-ligne renvoyé par LiveSplit Server."""
    buf = b""
    while b"\n" not in buf:
        chunk = s.recv(1024)
        if not chunk:
            raise ConnectionError("Connexion fermée par LiveSplit")
        buf += chunk
    return buf.decode('utf-8').strip()


def send_command(cmd):
    """Envoie une commande sur la connexion persistante, avec un réessai
    (reconnexion) si le socket a été coupé entre-temps."""
    global _sock
    with _lock:
        for attempt in range(2):
            try:
                s = _sock or _connect()
                s.send((cmd + "\r\n").encode('utf-8'))
                return _recv_line(s)
            except (OSError, ConnectionError):
                _close()
                if attempt == 1:
                    raise


@app.route('/api/bestpossibletime', methods=['GET'])
def get_best_possible_time():
    try:
        response = send_command("getbestpossibletime")

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
    # threaded=False : une seule connexion LiveSplit, sérialisée par _lock.
    app.run(host='127.0.0.1', port=8084)
