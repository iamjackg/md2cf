from urllib.parse import urljoin

import requests
import requests.adapters
import requests.packages
import urllib3


def bunchify(obj):
    if isinstance(obj, (list, tuple)):
        return [bunchify(item) for item in obj]
    if isinstance(obj, dict):
        return Bunch(obj)
    return obj


class Bunch(dict):
    def __init__(self, kwargs=None):
        if kwargs is None:
            kwargs = {}
        for key, value in kwargs.items():
            kwargs[key] = bunchify(value)
        super(Bunch, self).__init__(kwargs)
        self.__dict__ = self


class MinimalConfluence:
    def __init__(
        self, host, username=None, password=None, token=None, verify=True, max_retries=4
    ):
        if token is None:
            if username is None and password is None:
                raise ValueError(
                    "Either a personal access token, "
                    "or username and password are required"
                )

        if not host.endswith("/"):
            self.host = host + "/"
        else:
            self.host = host
        self.api = requests.Session()
        self.api.verify = verify

        if token is not None:
            self.api.headers.update({"Authorization": f"Bearer {token}"})
        elif username is not None and password is not None:
            self.api.auth = (username, password)

        adapter = requests.adapters.HTTPAdapter(
            max_retries=urllib3.Retry(
                total=max_retries,
                backoff_factor=1,
                respect_retry_after_header=True,
                allowed_methods=None,
            )
        )
        self.api.mount("http://", adapter)
        self.api.mount("https://", adapter)

        if not verify:
            requests.packages.urllib3.disable_warnings(
                requests.packages.urllib3.exceptions.InsecureRequestWarning
            )

    def _request(self, method, path, **kwargs):
        r = self.api.request(method, urljoin(self.host, path), **kwargs)
        r.raise_for_status()
        return bunchify(r.json())

    def _get(self, path, **kwargs):
        return self._request("GET", path, **kwargs)

    def _post(self, path, **kwargs):
        return self._request("POST", path, **kwargs)

    def _put(self, path, **kwargs):
        return self._request("PUT", path, **kwargs)

    def get_page(
        self,
        title=None,
        space_key=None,
        page_id=None,
        content_type="page",
        additional_expansions=None,
    ):
        """
        Create a new page in a space

        Args:
            title (str): the title for the page
            space_key (str): the Confluence space for the page
            content_type (str): Content type. Default value: page.
              Valid values: page, blogpost.
            page_id (str or int): the ID of the page
            additional_expansions (list of str): Additional expansions that should be
              made when calling the api

        Returns:
            The response from the API

        """
        params = None
        if additional_expansions is not None:
            params = {"expand": ",".join(additional_expansions)}

        if page_id is not None:
            return self._get(f"content/{page_id}", params=params)
        elif title is not None:
            params = {"title": title, "type": content_type}
            if space_key is not None:
                params["spaceKey"] = space_key
            response = self._get("content", params=params)
            try:
                # A search by title/space doesn't return full page objects,
                # and since we don't support expansion in this implementation
                # just yet, we just retrieve the "full" page data using the page
                # ID for the first search result
                return self.get_page(
                    page_id=response.results[0].id,
                    additional_expansions=additional_expansions,
                )
            except IndexError:
                return None
        else:
            raise ValueError("At least one of title or page_id must not be None")

    def create_page(
        self,
        space,
        title,
        body,
        content_type="page",
        parent_id=None,
        update_message=None,
        labels=None,
    ):
        """
        Create a new page in a space

        Args:
            space (str): the Confluence space for the page
            title (str): the title for the page
            body (str): the body of the page, in Confluence Storage Format
            content_type (str): Content type. Default value: page.
              Valid values: page, blogpost.
            parent_id (str or int): the ID of the parent page
            update_message (str): optional. A message that will appear in Confluence's
              history
            labels (list(str)): optional. The set of labels the final page should have.
              None leaves existing labels unchanged

        Returns:
            The response from the API

        """
        page_structure = {
            "title": title,
            "type": content_type,
            "space": {"key": space},
            "body": {"storage": {"value": body, "representation": "storage"}},
        }

        if parent_id is not None:
            if type(parent_id) is str:
                parent_id = int(parent_id)
            page_structure["ancestors"] = [{"id": parent_id}]

        if update_message is not None:
            page_structure["version"] = {"message": update_message}

        if labels is not None:
            page_structure["metadata"] = {
                "labels": [{"name": label, "prefix": "global"} for label in labels]
            }

        return self._post("content", json=page_structure)

    def update_page(
        self,
        page,
        body,
        parent_id=None,
        content_type="page",
        update_message=None,
        labels=None,
        minor_edit=False,
    ):
        update_structure = {
            "version": {
                "number": page.version.number + 1,
                "minorEdit": minor_edit,
            },
            "title": page.title,
            "type": content_type,
            "body": {"storage": {"value": body, "representation": "storage"}},
        }

        if parent_id is not None:
            if type(parent_id) is str:
                parent_id = int(parent_id)
            update_structure["ancestors"] = [{"id": parent_id}]

        if update_message is not None:
            update_structure["version"]["message"] = update_message

        if labels is not None:
            update_structure["metadata"] = {
                "labels": [{"name": label, "prefix": "global"} for label in labels]
            }

        return self._put(f"content/{page.id}", json=update_structure)

    def get_attachment(self, confluence_page, name):
        existing_attachments = self._get(
            f"content/{confluence_page.id}/child/attachment",
            headers={"X-Atlassian-Token": "nocheck", "Accept": "application/json"},
            params={"filename": name, "expand": "version"},
        )

        if existing_attachments.size:
            return existing_attachments.results[0]

    def update_attachment(self, confluence_page, fp, existing_attachment, message=""):
        return self._post(
            f"content/{confluence_page.id}/child/attachment/{existing_attachment.id}/"
            f"data",
            headers={"X-Atlassian-Token": "nocheck"},
            files={"file": fp, "comment": message if message else None},
        )

    def create_attachment(self, confluence_page, fp, message=""):
        return self._post(
            f"content/{confluence_page.id}/child/attachment",
            json={"comment": message} if message else None,
            headers={"X-Atlassian-Token": "nocheck"},
            params={"allowDuplicated": "true"},
            files={"file": fp, "comment": message if message else None},
        )

    def add_labels(self, page, labels):
        # return self.api.content(page.id).post(
        return self._post(
            f"content/{page.id}/label",
            data=[{"name": label, "type": "global"} for label in labels],
        )

    def get_url(self, page):
        return f"{page._links.base}{page._links.webui}"

    def get_parent_id(self, page):
        return page.ancestors[-1].id

    def get_space(self, space, additional_expansions=None):
        params = None
        if additional_expansions is not None:
            params = {"expand": ",".join(additional_expansions)}
        return self._get(f"space/{space}", params=params)
