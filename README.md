# EstradaCoin (ESC) — blockchain real a lo Satoshi

Blockchain con Proof of Work, wallets ECDSA (secp256k1, la misma curva de Bitcoin)
y nodos P2P con regla de consenso "longest chain".

## Correr un nodo localmente

```
pip install -r requirements.txt
python3 node.py 5000
```

Esto levanta un nodo en http://localhost:5000

## Levantar una red de varios nodos

```
python3 node.py 5001
python3 node.py 5002
python3 node.py 5003
```

Luego registralos como peers entre sí:

```
curl -X POST http://localhost:5001/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"nodes": ["http://localhost:5002", "http://localhost:5003"]}'
```

## Endpoints principales

- `GET  /chain` — ver la cadena completa
- `GET  /mine?address=TU_DIRECCION` — minar un bloque (PoW real, dificultad 4 ceros)
- `POST /transactions/new` — enviar una transacción firmada
- `GET  /balance/<address>` — consultar saldo
- `GET  /wallet/new` — generar un par de claves nuevo (address, public_key, private_key_pem)
- `POST /nodes/register` — registrar peers
- `GET  /nodes/resolve` — correr el algoritmo de consenso (adopta la cadena más larga válida)
- `GET  /validate` — validar la integridad de la cadena completa

## Firmar una transacción (Python)

```python
from wallet import Wallet
w = Wallet()
mensaje = '{"sender": "...", "recipient": "...", "amount": 10.0, ...}'  # mismo JSON que arma Transaction.message()
firma = w.sign(mensaje)
```

## Deploy en Render (paso a paso)

Cada nodo es una app Flask normal. Vamos a levantar 2 nodos para tener una red real.

**1. Sube el código a GitHub**
Crea un repo (puede ser desde la app de GitHub en el celular o github.com) y sube
estos archivos: `blockchain.py`, `wallet.py`, `node.py`, `requirements.txt`, `Procfile`.

**2. En Render (render.com), crea el primer Web Service**
- New → Web Service → conecta el repo.
- Runtime: Python 3.
- Build command: `pip install -r requirements.txt`
- Start command: `python3 node.py` (Render ya inyecta el puerto solo, no hace falta ponerlo)
- Nombre sugerido: `estradacoin-node-1`
- Deploy. Cuando termine, Render te da una URL tipo `https://estradacoin-node-1.onrender.com`

**3. Repite para el segundo nodo**
- New → Web Service → mismo repo.
- Nombre sugerido: `estradacoin-node-2`
- Deploy. Te da otra URL, `https://estradacoin-node-2.onrender.com`

**4. Conéctalos como peers**
En cada servicio, ve a **Environment** y agrega la variable:
- En `estradacoin-node-1`: `PEER_URLS = https://estradacoin-node-2.onrender.com`
- En `estradacoin-node-2`: `PEER_URLS = https://estradacoin-node-1.onrender.com`

Guarda — Render redeploya solo. Al reiniciar, cada nodo se auto-registra con su peer.

**5. Prueba que la red funciona**
Desde el navegador o con curl:
- `https://estradacoin-node-1.onrender.com/` → estado del nodo
- `https://estradacoin-node-1.onrender.com/mine` → mina un bloque
- `https://estradacoin-node-2.onrender.com/nodes/resolve` → debería adoptar la cadena de node-1

**Nota sobre el plan gratuito de Render:** los servicios free "duermen" tras un rato sin uso
y al despertar pierden la cadena en memoria (no hay disco persistente). Para una demo o pruebas
está perfecto; para producción real hace falta persistencia en disco/DB y probablemente
un plan pago (o Railway, que tiene un modelo distinto).

## Notas de diseño

- Dificultad de minería ajustable (`Blockchain(difficulty=N)`), por defecto 4 ceros iniciales.
- Recompensa de minería (coinbase): 50 ESC por bloque.
- Las direcciones empiezan con "EST" + hash de la clave pública.
- Esto es un proyecto educativo/funcional de un solo nodo lógico por proceso;
  para producción real faltaría: persistencia en disco, ajuste dinámico de dificultad,
  mempool con fees, y manejo de forks concurrentes más robusto.
