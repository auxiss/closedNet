from datetime import datetime, timezone
from distribution_layer import blake2b_wrapper as blake
import json
from distribution_layer import rsa_enryption as rsa

def create_payload(endpoint: str,
                    username: str,
                      wg_pk: str
                      ) -> dict:
    payload = {
        "endpoint": endpoint,
        "username": username,
        "wg_pk": wg_pk,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    return payload




def create_post(
    key_pair: tuple[bytes, bytes],
    group_key: bytes,
    payload: dict,
    
) -> str:
    
    """
    Creates a public post with encrypted and signed contents.
    """

    private_key = key_pair[0]  # Extract the private key from the key pair
    pub_key = key_pair[1]  # Extract the public key from the key pair



    byte_data = json.dumps(payload).encode()

    encrypted_payload = blake.encrypt(byte_data, group_key)

    signature = rsa.sign_message(private_key, byte_data)

    post = {
        "pub_key": pub_key.hex(),
        "signature": signature.hex(),
        "priv_info": encrypted_payload.hex(),
    }

    #serialize the post to a JSON string
    post = json.dumps(post)

    return post



def read_post(post: str, group_key: bytes) -> dict:
    """
    Reads a post and returns the decrypted contents.
    """
    try:
        post_data = json.loads(post)
    except json.JSONDecodeError:
        return None

    sender_pub_key = bytes.fromhex(post_data["pub_key"])
    signature = bytes.fromhex(post_data["signature"])
    encrypted_payload = bytes.fromhex(post_data["priv_info"])

    try:
        decrypted_payload = blake.decrypt(encrypted_payload, group_key)
    except Exception:
        return None

    valid_signature = rsa.verify_signature(sender_pub_key, decrypted_payload, signature)

    if not valid_signature: 
        return None

    post_data = {
        "sender_pub_key": sender_pub_key,
        "payload": json.loads(decrypted_payload.decode())
    }

    return post_data








if __name__ == "__main__":

    grup_key = b'some_group_key_1234567890'  # Example group key (must be bytes)

    rsa_key_pair = rsa.generate_rsa_keys()

    payload = create_payload(
        endpoint='peer_endpoint',
        username='example_user',
        wg_pk='example_wg_pk'
    )

    psot = create_post(
            key_pair=rsa_key_pair,
            group_key=grup_key,
            payload=payload
        )



    print(psot)
    print('\n\n\n\n')
    readed_post = read_post(psot, grup_key)
    print(readed_post)


    