from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes

def generate_rsa_keys():
    """
    Generate RSA public and private keys and save them to PEM files.
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Get public key
    public_key = private_key.public_key()

    # Save private key to PEM file
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Save public key to PEM file
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return pem_private, pem_public

def load_rsa_public_key_key(pem_public: bytes):
    """
    Load RSA public key from PEM bytes.
    """

    public_key = serialization.load_pem_public_key(
        pem_public
    )

    return public_key

def load_rsa_private_key(pem_private: bytes):
    """
    Load RSA private key from PEM bytes.
    """

    private_key = serialization.load_pem_private_key(
        pem_private,
        password=None
    )

    return private_key









class RSAUser:
    def __init__(self, private_key, public_key, associate_public_key):
        """
        :param private_key: Your RSA private key
        :param public_key: Your RSA public key
        :param associate_public_key: The other party’s public key
        """
        self.private_key = private_key
        self.public_key = public_key
        self.associate_public_key = associate_public_key

    def authenticate(self, message: bytes) -> bytes:
        """
        Create a digital signature for the message using your private key.
        """
        signature = self.private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature

    def verify(self, message: bytes, signature: bytes) -> bool:
        """
        Verify the message's signature using the associate's public key.
        Returns True if valid, False otherwise.
        """
        try:
            self.associate_public_key.verify(
                signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

    def encrypt(self, message: bytes) -> bytes:
        """
        Encrypt message with the associate's public key.
        """
        ciphertext = self.associate_public_key.encrypt(
            message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext

    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypt message with your private key.
        """
        plaintext = self.private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext
    



if __name__ == "__main__":
    pem_private, pem_public = generate_rsa_keys()
    key_pair_1 = (pem_private, pem_public)
    print("set 1 of Keys generated successfully.")

    pem_private, pem_public = generate_rsa_keys()
    key_pair_2 = (pem_private, pem_public)
    print("set 2 of Keys generated successfully.")    




    user1 = RSAUser(
        private_key=load_rsa_private_key(key_pair_1[0]),
        public_key=load_rsa_public_key_key(key_pair_1[1]),
        associate_public_key=load_rsa_public_key_key(key_pair_2[1])
    )


    user2 = RSAUser(
        private_key=load_rsa_private_key(key_pair_2[0]),
        public_key=load_rsa_public_key_key(key_pair_2[1]),  
        associate_public_key=load_rsa_public_key_key(key_pair_1[1])
    )


    message = b"Hello, this is a secret message."
    print("Original message:", message)
    print()

    ciphertext = user1.encrypt(message)
    print("Encrypted message:", ciphertext)
    print()

    signature = user1.authenticate(message)
    print("Digital signature:", signature)
    print()



    decrypted_message = user2.decrypt(ciphertext)
    print("Decrypted message:", decrypted_message)
    print()

    is_valid = user2.verify(message, signature)
    print("Is the signature valid?", is_valid)

