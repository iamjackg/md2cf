import tortilla
from requests.auth import HTTPBasicAuth


class MinimalConfluence:
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password

        self.api = tortilla.wrap(self.host, auth=HTTPBasicAuth(self.username, self.password))

    def get_page(self, title=None, space_key=None, page_id=None):
        if page_id is not None:
            return self.api.content.get(page_id)
        elif title is not None:
            params = {'title': title}
            if space_key is not None:
                params['spaceKey'] = space_key

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
        page_structure = {
            'title': title,
            'type': 'page',
            'space': {
                'key': space
            },
            'body': {
                'storage': {
                    'value': body,
                    'representation': 'storage'
                }
            }
        }

        if parent_id is not None:
            if type(parent_id) is str:
                parent_id = int(parent_id)
            page_structure['ancestors'] = [{'id': parent_id}]

        if update_message is not None:
            page_structure['version'] = {'message': update_message}

        return self.api.content.post(json=page_structure)

    def update_page(self, page, body, update_message=None):
        update_structure = {
            'version': {
                'number': page.version.number + 1,
            },
            'title': page.title,
            'type': 'page',
            'body': {
                'storage': {
                    'value': body,
                    'representation': 'storage'
                }
            }
        }

        if update_message is not None:
            update_structure['version']['message'] = update_message

        return self.api.content.put(page.id, json=update_structure)
