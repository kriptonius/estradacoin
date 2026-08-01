"""
Wallet - Generación de claves ECDSA (secp256k1, misma curva que Bitcoin)
Firma y verificación de transacciones.
"""
import hashlib
import json
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature, decode_dss_signature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature


class Wallet:
    def __init__(self):
        self.private_key = ec.generate_private_key(ec.SECP256K1())
        self.public_key = self.private_key.public_key()

    @property
    def address(self):
        """Dirección = SHA256 de la clave pública comprimida, formato hex (como base de una address estilo Bitcoin)."""
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint
        )
        return "EST" + hashlib.sha256(pub_bytes).hexdigest()[:34]

    @property
    def public_key_hex(self):
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint
        )
        return pub_bytes.hex()

    def export_private_key(self):
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return pem.decode()

    def sign(self, message: str) -> str:
        signature = self.private_key.sign(message.encode(), ec.ECDSA(hashes.SHA256()))
        return signature.hex()


def verify_signature(public_key_hex: str, message: str, signature_hex: str) -> bool:
    try:
        pub_bytes = bytes.fromhex(public_key_hex)
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pub_bytes)
        signature = bytes.fromhex(signature_hex)
        public_key.verify(signature, message.encode(), ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, Exception):
        return False


def address_from_public_key(public_key_hex: str) -> str:
    pub_bytes = bytes.fromhex(public_key_hex)
    return "EST" + hashlib.sha256(pub_bytes).hexdigest()[:34]


if __name__ == "__main__":
    w = Wallet()
    print("Dirección:", w.address)
    print("Clave pública:", w.public_key_hex)
    msg = "hola mundo"
    sig = w.sign(msg)
    print("Firma válida:", verify_signature(w.public_key_hex, msg, sig))
