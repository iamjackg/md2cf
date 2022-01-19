import tortilla
from requests.auth import HTTPBasicAuth


class MinimalConfluence:
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password

        self.api = tortilla.wrap(
            self.host, auth=HTTPBasicAuth(self.username, self.password)
        )

    def get_page(self, title=None, space_key=None, page_id=None):
        if page_id is not None:
            return self.api.content.get(page_id)
        elif title is not None:
            params = {"title": title}
            if space_key is not None:
                params["spaceKey"] = space_key

            response = self.api.content.get(params=params)

            try:
                # A search by title/space doesn't return full page objects, and since we don't support expansion in this implementation
                # just yet, we just retrieve the "full" page data using the page ID for the first search result
                return self.get_page(page_id=response.results[0].id)
            except IndexError:
                return None
        else:
            raise ValueError("At least one of title or page_id must not be None")

    def create_page(self, space, title, body, parent_id=None, update_message=None):
        """
        Create a new page in a space

        Args:
            space (str): the Confluence space for the page
            title (str): the title for the page
            body (str): the body of the page, in Confluence Storage Format
            parent_id (str or int): the ID of the parent page
            update_message (str): optional. A message that will appear in Confluence's history

        Returns:
            The response from the API

        """
        page_structure = {
            "title": title,
            "type": "page",
            "space": {"key": space},
            "body": {"storage": {"value": body, "representation": "storage"}},
        }

        if parent_id is not None:
            if type(parent_id) is str:
                parent_id = int(parent_id)
            page_structure["ancestors"] = [{"id": parent_id}]

        if update_message is not None:
            page_structure["version"] = {"message": update_message}

        return self.api.content.post(json=page_structure)

    def update_page(self, page, body, parent_id=None, update_message=None):
        update_structure = {
            "version": {
                "number": page.version.number + 1,
            },
            "title": page.title,
            "type": "page",
            "body": {"storage": {"value": body, "representation": "storage"}},
        }

        if parent_id is not None:
            if type(parent_id) is str:
                parent_id = int(parent_id)
            update_structure["ancestors"] = [{"id": parent_id}]

        if update_message is not None:
            update_structure["version"]["message"] = update_message

        return self.api.content.put(page.id, json=update_structure)

    def get_attachment(self, page, name):
        existing_attachments = self.api.content(page.id).child.get(
            "attachment",
            headers={"X-Atlassian-Token": "nocheck", "Accept": "application/json"},
            params={"filename": name, "expand": "version"},
        )

        if existing_attachments.size:
            return existing_attachments.results[0]

    def update_attachment(self, page, fp, existing_attachment, message=""):
        return (
            self.api.content(page.id)
            .child.attachment(existing_attachment.id)
            .post(
                "data",
                data={"comment": message} if message else None,
                format=(None, "json"),
                headers={"X-Atlassian-Token": "nocheck"},
                files={"file": fp},
            )
        )

    def create_attachment(self, page, fp, message=""):
        return self.api.content(page.id).child.post(
            "attachment",
            data={"comment": message} if message else None,
            format=(None, "json"),
            headers={"X-Atlassian-Token": "nocheck"},
            params={"allowDuplicated": "true"},
            files={"file": fp},
        )
