import nacl.utils
from nacl.secret import SecretBox
from nacl.hash import blake2b
from nacl.encoding import RawEncoder


# -----------------------------
# Key derivation
# -----------------------------

def _derive_key(group_key: bytes, salt: bytes) -> bytes:
    """
    Derive a fixed-size symmetric key from an arbitrary group key.
    """
    return blake2b(
        group_key,
        salt=salt,
        digest_size=SecretBox.KEY_SIZE,  # 32 bytes
        encoder=RawEncoder,
        person=b"wg-grp-enc-v1",
    )


# -----------------------------
# Encrypt
# -----------------------------

def encrypt(data: bytes, group_key: bytes) -> bytes:
    """
    Encrypts data using a group key.
    Returns a single opaque blob.
    """

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if not isinstance(group_key, bytes):
        raise TypeError("group_key must be bytes")

    salt = nacl.utils.random(16)
    key = _derive_key(group_key, salt)

    box = SecretBox(key)
    nonce = nacl.utils.random(SecretBox.NONCE_SIZE)

    ciphertext = box.encrypt(data, nonce)

    # Final blob: salt || ciphertext
    return salt + ciphertext


# -----------------------------
# Decrypt
# -----------------------------

def decrypt(encrypted_data: bytes, group_key: bytes) -> bytes:
    """
    Decrypts data using a group key.
    Raises if authentication fails.
    """

    if not isinstance(encrypted_data, bytes):
        raise TypeError("encrypted_data must be bytes")
    if not isinstance(group_key, bytes):
        raise TypeError("group_key must be bytes")

    salt = encrypted_data[:16]
    ciphertext = encrypted_data[16:]

    key = _derive_key(group_key, salt)
    box = SecretBox(key)

    return box.decrypt(ciphertext)
