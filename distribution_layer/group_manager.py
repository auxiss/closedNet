import postMaker
import gist_wrapper
import rsa_enryption as rsa


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
        print(f"Found {len(gists)} gists with '{self.group_name}' in description.")
        
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
         





def test1():
    import conf_loader
    file_name = 'auxiss_closednet.json'
    config = conf_loader.load_config_file(file_name)
    rsa_key_pair = (config["PEM_private_key"].encode(), config["PEM_public_key"].encode())

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

    members = group.get_members()
    for member in members:
        pub_key = member['sender_pub_key']
        payload = member['payload']
        print(f"Member with pub key:\n {pub_key.hex()} \n has payload: {payload}")









if __name__ == '__main__':
    test1()