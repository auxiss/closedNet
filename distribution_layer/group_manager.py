from distribution_layer import postMaker
from distribution_layer import gist_wrapper
from distribution_layer import rsa_enryption as rsa

# For robust public-key comparisons
import hashlib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64
from cryptography.hazmat.primitives.asymmetric import rsa as crypto_rsa


class Group:

    def __init__(
        self,
        token: str,
        owner: str,
        group: str,
        group_key: bytes,
        key_pair: tuple[bytes, bytes],
        public: bool = False,
    ):
        self.gist_wrapper = gist_wrapper.GitHubGistUserStore(
            token=token,
            owner=owner,
            group_name=group,
            public=public,
            gist_id=None
        )

        self.username = owner

        self.group_name = group
        self.group_key = group_key
        self.key_pair = key_pair

    def create_and_post(self, endpoint: str, wg_pk: str):
        payload = postMaker.create_payload(endpoint, self.username, wg_pk)
        post = postMaker.create_post(self.key_pair, self.group_key, payload)
        id = self.gist_wrapper.upsert_user(post)


    def get_members(self) -> list[dict]:
        members = []

        gists = self.gist_wrapper.get_gists_by_key_discription(self.group_name)
        #print(f"Found {len(gists)} gists with '{self.group_name}' in description.")
        
        for gist in gists:
            contents = self.gist_wrapper.get_gist_contents(gist)
            id = gist["id"]
            #print(f"\n\n ---------{id}----->")

            info = contents['user_data.txt']
            #print(info)

            post_data = postMaker.read_post(info, self.group_key)
            if post_data is None: continue

            #print(post_data)
            members.append(post_data)
            
        return members

    def get_known_members(self, known_members: list[dict]) -> list[dict]:
        members_gists = self.get_members()
        print(f'\nfaound: {len(members_gists)} gists with the group name')
        known_members_gists = []

        for member in members_gists:
            pub_key = member['sender_pub_key']
            payload = member['payload']
            member_name = payload['username']

            #print(member_name)


            for known_member in known_members:
                #print('\n\n\n\n------------------')
                if known_member['name'] == member_name:

                    #print(f'faound mach in name {member_name}')

                    # Safe printing (avoid mismatched quoting) and normalize keys
                    #print("data base rsa key :\n" + str(known_member.get('rsa_public_key')))
                    try:
                        remote_key_str = pub_key.decode() if isinstance(pub_key, (bytes, bytearray)) else str(pub_key)
                    except Exception:
                        remote_key_str = str(pub_key)
                    #print("qury rsa kay      :\n" + remote_key_str)

                    # Parse both sides into public-key objects (if possible) and compare key material
                    
                    local_obj = _to_public_key_obj(known_member.get('rsa_public_key'))
                    remote_obj = _to_public_key_obj(pub_key)

                    matched = False
                    # If both parsed to RSA public keys, compare numeric values
                    if local_obj is not None and remote_obj is not None:
                        try:
                            if isinstance(local_obj, crypto_rsa.RSAPublicKey) and isinstance(remote_obj, crypto_rsa.RSAPublicKey):
                                ln = local_obj.public_numbers()
                                rn = remote_obj.public_numbers()
                                if ln.n == rn.n and ln.e == rn.e:
                                    matched = True
                        except Exception:
                            matched = False

                    if not matched:
                        # Fallback: compare DER sha256 fingerprints (tolerant to formatting differences)
                        def _fingerprint(obj_or_raw):
                            if obj_or_raw is None:
                                return None
                            if hasattr(obj_or_raw, 'public_bytes'):
                                try:
                                    der = obj_or_raw.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
                                    return hashlib.sha256(der).hexdigest()
                                except Exception:
                                    pass
                            raw = obj_or_raw
                            if not isinstance(raw, (bytes, bytearray)):
                                raw = str(raw).encode()
                            cleaned = raw.decode(errors='ignore').strip().replace(' ', '').replace('\r', '').replace('\n', '')
                            try:
                                decoded = base64.b64decode(cleaned)
                                return hashlib.sha256(decoded).hexdigest()
                            except Exception:
                                return hashlib.sha256(cleaned.encode()).hexdigest()

                        local_fp = _fingerprint(local_obj if local_obj is not None else known_member.get('rsa_public_key'))
                        remote_fp = _fingerprint(remote_obj if remote_obj is not None else pub_key)
                        if local_fp is not None and remote_fp is not None and local_fp == remote_fp:
                            matched = True

                    if matched:
                        known_members_gists.append({
                            "name": member_name,
                            "pub_key": pub_key,
                            "payload": payload
                        })
                        break
                    else:
                        print(f"Public key mismatch for member '{member_name}'. Skipping.")
                        pass
                
        print(f'{len(known_members_gists)}/{len(members_gists)} whare known')
        return known_members_gists
         

def _to_public_key_obj(maybe_pem):
                        if maybe_pem is None:
                            return None
                        data = maybe_pem
                        if isinstance(data, str):
                            data = data.encode()

                        # Try PEM
                        try:
                            return serialization.load_pem_public_key(data, backend=default_backend())
                        except Exception:
                            pass

                        # Try raw DER (base64)
                        try:
                            b = data.strip()
                            b = b.replace(b"\n", b"").replace(b" ", b"")
                            der = base64.b64decode(b)
                            return serialization.load_der_public_key(der, backend=default_backend())
                        except Exception:
                            pass

                        # Try extracting base64 body from PEM-like text
                        try:
                            text = data.decode(errors='ignore')
                            lines = [l.strip() for l in text.splitlines() if l.strip() and 'BEGIN' not in l and 'END' not in l]
                            if lines:
                                b64 = ''.join(lines).encode()
                                der = base64.b64decode(b64)
                                return serialization.load_der_public_key(der, backend=default_backend())
                        except Exception:
                            pass

                        return None





def test1():
    from distribution_layer  import conf_loader
    file_name = 'auxiss_closednet.json'
    config = conf_loader.load_config_file()

    rsa_key_pair = (config["PEM_private_key"].encode(), config["PEM_public_key"].encode())
    known_members = config["members"]

    group = Group(
        token=config["token"],
        owner=config["username"],
        group=config["group_name"],
        group_key=config["group_key"].encode(),
        key_pair=rsa_key_pair,
        public=True
    )

    '''group.create_and_post(
        endpoint='peer_endpoint',
        wg_pk='example_wg_pk'
    )#'''

    members = group.get_known_members(known_members)
    for member in members:
        print(f"Member Name: {member['payload']['username']}")
        print(f"Member Public Key: {member['pub_key'].decode()}")
        print(f"Member Endpoint: {member['payload']['endpoint']}")









if __name__ == '__main__':
    test1()