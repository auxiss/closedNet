import requests
from typing import Optional, List


class GitHubGistUserStore:
    BASE_URL = "https://api.github.com"
    FILENAME = "user_data.txt"

    def __init__(
        self,
        token: str,
        owner: str,
        group: str,
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
        self.group = group
        self.gist_id = gist_id
        self.public = public

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



if __name__ == "__main__":

    store = GitHubGistUserStore(
        token="your_github_token_here",   #place your GitHub token here
        owner="your-username",
        group="backend-team",
        public=True
    )

    '''# Automatically creates on first call
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
