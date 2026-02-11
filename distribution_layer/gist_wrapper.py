import requests
from typing import Optional, List


class GitHubGistUserStore:
    

    def __init__(
        self,
        token: str,
        owner: str,
        group_name: str,
        gist_id: Optional[str] = None,
        public: bool = False,
    ):
        """
        :param token: GitHub personal access token
        :param owner: GitHub username that owns the gists
        :param group: Group name stored in gist description
        :param gist_id: Existing gist ID (optional)
        :param public: Whether created gists should be public
        """
        self.owner = owner
        self.group = group_name
        self.gist_id = gist_id
        self.public = public

        self.BASE_URL = "https://api.github.com"
        self.FILENAME = "user_data.txt"


        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        })

    # -------------------------
    # Internal helpers
    # -------------------------

    def _description(self) -> str:
        return f"[group:{self.group}]-[owner:{self.owner}]"

    def _create_gist(self, content: str) -> str:
        payload = {
            "description": self._description(),
            "public": self.public,
            "files": {
                self.FILENAME: {
                    "content": content
                }
            }
        }

        response = self.session.post(
            f"{self.BASE_URL}/gists",
            json=payload
        )
        response.raise_for_status()

        gist_id = response.json()["id"]
        self.gist_id = gist_id
        return gist_id

    def _update_gist(self, content: str) -> None:
        if not self.gist_id:
            raise RuntimeError("Cannot update gist without gist_id")

        payload = {
            "description": self._description(),
            "files": {
                self.FILENAME: {
                    "content": content
                }
            }
        }

        response = self.session.patch(
            f"{self.BASE_URL}/gists/{self.gist_id}",
            json=payload
        )
        response.raise_for_status()

    # -------------------------
    # Public API
    # -------------------------

    def upsert_user(self, content: str) -> str:
        """
        Automatically creates or updates the user gist.

        - If no gist_id exists -> create
        - If gist_id exists -> update

        :return: gist_id
        """
        if self.gist_id is None:
            return self._create_gist(content)

        self._update_gist(content)
        return self.gist_id

    def get_user_content(self) -> str:
        """
        Fetch the contents of this user's gist.
        """
        if not self.gist_id:
            raise RuntimeError("No gist_id set on this instance")

        response = self.session.get(
            f"{self.BASE_URL}/gists/{self.gist_id}"
        )
        response.raise_for_status()

        files = response.json()["files"]
        return files[self.FILENAME]["content"]

    def get_group_users(self) -> List[dict]:
        """
        Get all gists that have this group name in their description, and contain the expected filename.
        """
        gists = []
        page = 1
        while True:
            response = self.session.get(
                f"{self.BASE_URL}/gists",
                params={"per_page": 30, "page": page}
            )
            response.raise_for_status()
            page_gists = response.json()

            if not page_gists:
                break

            for gist in page_gists:
                if self._description() in gist.get("description", "") and self.FILENAME in gist.get("files", {}):
                    gists.append(gist)

            page += 1

        return gists

    def get_group_user_contents(self) -> List[str]:
        """
        Convenience method to fetch contents of all group gists.
        """
        contents = []

        for gist in self.get_group_users():
            files = gist.get("files", {})
            if self.FILENAME in files:
                file_obj = files[self.FILENAME]
                content = file_obj.get("content")
                if content is None:
                    # Fetch via raw_url if content is not available
                    raw_url = file_obj.get("raw_url")
                    if raw_url:
                        resp = self.session.get(raw_url)
                        resp.raise_for_status()
                        content = resp.text
                if content is not None:
                    contents.append(content)

        return contents


    def get_gists_by_key_discription(self, key: str) -> List[dict]:
        """
        Get all gists that have a specific key in their description.
        """
        gists = []
        page = 1
        while True:
            response = self.session.get(
                f"{self.BASE_URL}/gists",
                params={"per_page": 30, "page": page}
            )
            response.raise_for_status()
            page_gists = response.json()

            if not page_gists:
                break

            for gist in page_gists:
                if key in gist.get("description", ""):
                    gists.append(gist)

            page += 1

        return gists
    


    def get_gist_contents(self, gist: dict) -> dict:
        """
        Fetch the contents of a specific gist.
        """

        files = gist.get("files", {})
        contents = {}
        for self.FILENAME, file_obj in files.items():
            content = file_obj.get("content")
            if content is None:
                # Fetch via raw_url if content is not available
                raw_url = file_obj.get("raw_url")
                if raw_url:
                    resp = self.session.get(raw_url)
                    resp.raise_for_status()
                    content = resp.text
            contents[self.FILENAME] = content
        return contents
    

    def get_gist_id(self, gist: dict) -> int:
        """
        Extract the gist ID from a gist object.
        """
        return gist.get("id")
    



##tests



def test1(token: str):
    store = GitHubGistUserStore(
        token=token,
        owner="your-username",
        group_name="backend-team",
        public=True
    )

    # Automatically creates on first call
    gist_id = store.upsert_user(
        "user_id=42\nendpoint=/prs\nactive=true"
    )

    # Automatically updates on second call
    store.upsert_user(
        "user_id=48\nendpoint=/prs\nactive=TRUE\nlast_updated=2024-06-01"
    )#'''

    # Fetch len of gists in this group
    print(f"Total users in group: {len(store.get_group_users())}")

    # Fetch this user's data
    #print(store.get_user_content())

    # Fetch all users in the group
    for content in store.get_group_user_contents():
        print('---')
        print(content)



def test2(token: str):
    store = GitHubGistUserStore(
        token=token,
        owner="your-username",
        group_name="backend-team",
        public=True
    )

    # Fetch gists by key in description
    key = "backend-team"
    gists = store.get_gists_by_key_discription(key)
    print(f"Found {len(gists)} gists with '{key}' in description.")

     # Fetch contents of the first gist
    for gist in gists:
        contents = store.get_gist_contents(gist)
        print(f"Gist ID: {store.get_gist_id(gist)}")
        print(f"Contents: {contents}")


if __name__ == "__main__":
    token = '' #  <----- add token hire

    test2(token)