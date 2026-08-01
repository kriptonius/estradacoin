"""
EstradaCoin (ESC) - Blockchain real, a lo Satoshi.
Proof of Work + validación de cadena + transacciones firmadas.
"""
import hashlib
import json
import time
from wallet import verify_signature

COINBASE_REWARD = 50.0
DIFFICULTY = 4  # número de ceros iniciales requeridos en el hash


class Transaction:
    def __init__(self, sender, recipient, amount, public_key_hex=None, signature=None, tx_type="transfer", timestamp=None):
        self.sender = sender          # dirección, o "COINBASE" para recompensa de minería
        self.recipient = recipient
        self.amount = amount
        self.public_key_hex = public_key_hex
        self.signature = signature
        self.tx_type = tx_type
        self.timestamp = timestamp if timestamp is not None else time.time()

    def to_dict(self, include_signature=True):
        d = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "tx_type": self.tx_type,
            "timestamp": self.timestamp,
        }
        if include_signature:
            d["public_key_hex"] = self.public_key_hex
            d["signature"] = self.signature
        return d

    def message(self):
        """Lo que se firma: todo menos la firma misma."""
        return json.dumps(self.to_dict(include_signature=False), sort_keys=True)

    def is_valid(self):
        if self.tx_type == "coinbase":
            return self.sender == "COINBASE" and self.amount == COINBASE_REWARD
        if self.amount <= 0:
            return False
        if not self.public_key_hex or not self.signature:
            return False
        return verify_signature(self.public_key_hex, self.message(), self.signature)

    @staticmethod
    def from_dict(d):
        tx = Transaction(d["sender"], d["recipient"], d["amount"],
                          d.get("public_key_hex"), d.get("signature"), d.get("tx_type", "transfer"))
        tx.timestamp = d["timestamp"]
        return tx


class Block:
    def __init__(self, index, transactions, previous_hash, timestamp=None, nonce=0):
        self.index = index
        self.transactions = transactions  # lista de Transaction
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @staticmethod
    def from_dict(d):
        txs = [Transaction.from_dict(t) for t in d["transactions"]]
        block = Block(d["index"], txs, d["previous_hash"], d["timestamp"], d["nonce"])
        block.hash = d["hash"]
        return block


class Blockchain:
    def __init__(self, difficulty=DIFFICULTY):
        self.chain = []
        self.pending_transactions = []
        self.difficulty = difficulty
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(0, [], "0" * 64, timestamp=0, nonce=0)
        genesis.hash = genesis.compute_hash()
        self.chain.append(genesis)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_transaction(self, tx: Transaction):
        if not tx.is_valid():
            raise ValueError("Transacción inválida: firma incorrecta o datos corruptos")
        if tx.tx_type != "coinbase":
            balance = self.get_balance(tx.sender)
            if balance < tx.amount:
                raise ValueError(f"Fondos insuficientes: balance {balance}, intenta enviar {tx.amount}")
        self.pending_transactions.append(tx)
        return True

    def proof_of_work(self, block: Block):
        target = "0" * self.difficulty
        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash = block.compute_hash()
        return block

    def mine_pending_transactions(self, miner_address):
        coinbase = Transaction("COINBASE", miner_address, COINBASE_REWARD, tx_type="coinbase")
        transactions = [coinbase] + self.pending_transactions

        new_block = Block(
            index=self.last_block.index + 1,
            transactions=transactions,
            previous_hash=self.last_block.hash,
        )
        self.proof_of_work(new_block)
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block

    def get_balance(self, address):
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == address:
                    balance += tx.amount
                if tx.sender == address:
                    balance -= tx.amount
        return balance

    def is_chain_valid(self, chain=None):
        chain = chain or self.chain
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]

            if current.hash != current.compute_hash():
                return False, f"Bloque {i}: hash no coincide con el contenido"
            if current.previous_hash != previous.hash:
                return False, f"Bloque {i}: previous_hash roto"
            if not current.hash.startswith("0" * self.difficulty):
                return False, f"Bloque {i}: no cumple la dificultad de PoW"
            for tx in current.transactions:
                if not tx.is_valid():
                    return False, f"Bloque {i}: transacción inválida"
        return True, "OK"

    def replace_chain(self, new_chain_dicts):
        """Regla de consenso: la cadena más larga válida gana (longest chain rule)."""
        new_chain = [Block.from_dict(b) for b in new_chain_dicts]
        if len(new_chain) <= len(self.chain):
            return False, "La cadena recibida no es más larga"
        valid, reason = self.is_chain_valid(new_chain)
        if not valid:
            return False, f"Cadena recibida inválida: {reason}"
        self.chain = new_chain
        return True, "Cadena reemplazada por una más larga y válida"

    def to_dict(self):
        return [b.to_dict() for b in self.chain]
