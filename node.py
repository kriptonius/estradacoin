"""
Nodo de la red EstradaCoin. Cada nodo corre esta app en un puerto distinto
y se comunican entre sí vía HTTP (P2P simplificado sobre REST).
"""
import os
import sys
import requests
from flask import Flask, jsonify, request
from blockchain import Blockchain, Transaction
from wallet import Wallet, address_from_public_key

app = Flask(__name__)

blockchain = Blockchain()
peers = set()
node_wallet = Wallet()  # wallet propia del nodo (para minar y recibir recompensas)

print(f"[Nodo] Dirección de minería: {node_wallet.address}")

# En Render/Railway se puede pasar PEER_URLS="https://otro-nodo.onrender.com,https://tercero.onrender.com"
# para que el nodo se auto-registre con sus peers apenas arranca.
_peer_env = os.environ.get("PEER_URLS", "")
for _p in _peer_env.split(","):
    _p = _p.strip().rstrip("/")
    if _p:
        peers.add(_p)


@app.route("/wallet/new", methods=["GET"])
def new_wallet():
    w = Wallet()
    return jsonify({
        "address": w.address,
        "public_key": w.public_key_hex,
        "private_key_pem": w.export_private_key(),
    })


@app.route("/chain", methods=["GET"])
def get_chain():
    return jsonify({"length": len(blockchain.chain), "chain": blockchain.to_dict()})


@app.route("/mine", methods=["GET"])
def mine():
    miner = request.args.get("address", node_wallet.address)
    block = blockchain.mine_pending_transactions(miner)
    return jsonify({"message": "Bloque minado", "block": block.to_dict()})


@app.route("/transactions/new", methods=["POST"])
def new_transaction():
    values = request.get_json()
    required = ["sender", "recipient", "amount", "public_key_hex", "signature"]
    if not all(k in values for k in required):
        return jsonify({"error": "Faltan campos"}), 400

    tx = Transaction(values["sender"], values["recipient"], values["amount"],
                      values["public_key_hex"], values["signature"])
    try:
        blockchain.add_transaction(tx)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"message": "Transacción añadida al pool", "tx": tx.to_dict()}), 201


@app.route("/transactions/pending", methods=["GET"])
def pending():
    return jsonify([tx.to_dict() for tx in blockchain.pending_transactions])


@app.route("/balance/<address>", methods=["GET"])
def balance(address):
    return jsonify({"address": address, "balance": blockchain.get_balance(address)})


@app.route("/nodes/register", methods=["POST"])
def register_nodes():
    values = request.get_json()
    nodes = values.get("nodes", [])
    for node in nodes:
        peers.add(node)
    return jsonify({"message": "Nodos registrados", "total_peers": list(peers)}), 201


@app.route("/nodes/resolve", methods=["GET"])
def consensus():
    """Consulta a todos los peers y adopta la cadena válida más larga."""
    replaced = False
    reason = "Nuestra cadena ya era la más larga"
    for peer in peers:
        try:
            resp = requests.get(f"{peer}/chain", timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                ok, msg = blockchain.replace_chain(data["chain"])
                if ok:
                    replaced = True
                    reason = msg
        except requests.exceptions.RequestException:
            continue

    return jsonify({
        "replaced": replaced,
        "reason": reason,
        "chain": blockchain.to_dict(),
    })


@app.route("/validate", methods=["GET"])
def validate():
    valid, reason = blockchain.is_chain_valid()
    return jsonify({"valid": valid, "reason": reason})


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "node_address": node_wallet.address,
        "chain_length": len(blockchain.chain),
        "peers": list(peers),
    })


if __name__ == "__main__":
    # Render/Railway inyectan PORT como variable de entorno; localmente se puede pasar por argv.
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
