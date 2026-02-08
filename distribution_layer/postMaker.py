import time
import blake2b_wrapper as blake
import json




def create_post(
    pub_key: str,
    endpoint: str,
    group_key: bytes,
) -> dict:
    
    """
    Creates a public post with encrypted contents.
    """

    payload = {
        "endpoint": endpoint,
        "issued_at": int(time.time()),
    }


    byte_data = json.dumps(payload).encode()

    encrypted_payload = blake.encrypt(
                                byte_data,
                                group_key,
                            )

    post = {
        "pub_key": pub_key,
        "priv_info": encrypted_payload,
    }

    return post











if __name__ == "__main__":

    grup_key = b'some_group_key_1234567890'  # Example group key (must be bytes)

    psot = create_post(
            pub_key='peer_public_key',
            endpoint='peer_endpoint',
            group_key=grup_key
        )



    print(psot)



    priv_info = blake.decrypt(psot["priv_info"], group_key=grup_key)
    print(priv_info)