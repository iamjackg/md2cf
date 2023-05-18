import urllib.parse as urlparse
import uuid
from pathlib import Path
from typing import List, NamedTuple

import mistune
from mistune.util import safe_entity


class RelativeLink(NamedTuple):
    path: str
    replacement: str
    original: str
    escaped_original: str


class ConfluenceTag(object):
    def __init__(self, name, text="", attrib=None, namespace="ac", cdata=False):
        self.name = name
        self.text = text
        self.namespace = namespace
        if attrib is None:
            attrib = {}
        self.attrib = attrib
        self.children = []
        self.cdata = cdata

    def render(self):
        namespaced_name = self.add_namespace(self.name, namespace=self.namespace)
        namespaced_attribs = {
            self.add_namespace(
                attribute_name, namespace=self.namespace
            ): attribute_value
            for attribute_name, attribute_value in self.attrib.items()
        }

        content = "<{}{}>{}{}</{}>".format(
            namespaced_name,
            " {}".format(
                " ".join(
                    [
                        '{}="{}"'.format(name, value)
                        for name, value in sorted(namespaced_attribs.items())
                    ]
                )
            )
            if namespaced_attribs
            else "",
            "".join([child.render() for child in self.children]),
            "<![CDATA[{}]]>".format(self.text) if self.cdata else self.text,
            namespaced_name,
        )
        return "{}\n".format(content)

    @staticmethod
    def add_namespace(tag, namespace):
        return "{}:{}".format(namespace, tag)

    def append(self, child):
        self.children.append(child)


class ConfluenceRenderer(mistune.HTMLRenderer):
    def __init__(
        self,
        strip_header=False,
        enable_relative_links=False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.strip_header = strip_header
        self.attachments = list()
        self.title = None
        self.enable_relative_links = enable_relative_links
        self.relative_links: List[RelativeLink] = list()

    def reinit(self):
        self.attachments = list()
        self.relative_links = list()
        self.title = None

    def heading(self, text, level, **attrs):
        if self.title is None and level == 1:
            self.title = text
            # Don't duplicate page title as a header
            if self.strip_header:
                return ""

        return super(ConfluenceRenderer, self).heading(text, level, **attrs)

    def structured_macro(self, name):
        return ConfluenceTag("structured-macro", attrib={"name": name})

    def parameter(self, name, value):
        parameter_tag = ConfluenceTag("parameter", attrib={"name": name})
        parameter_tag.text = value
        return parameter_tag

    def plain_text_body(self, text):
        body_tag = ConfluenceTag("plain-text-body", cdata=True)
        body_tag.text = text
        return body_tag

    def link(self, text, url, title=None):
        parsed_link = urlparse.urlparse(url)
        if self.enable_relative_links and (
            not parsed_link.scheme
            and not parsed_link.netloc
            and not parsed_link.fragment
        ):
            # relative link
            replacement_link = f"md2cf-internal-link-{uuid.uuid4()}"
            self.relative_links.append(
                RelativeLink(
                    path=parsed_link.path,
                    replacement=replacement_link,
                    original=url,
                    escaped_original=mistune.escape_link(url),
                )
            )
            url = replacement_link
        return super(ConfluenceRenderer, self).link(text, url, title)

    def block_code(self, code, info=None):
        root_element = self.structured_macro("code")
        if info is not None:
            info = safe_entity(info.strip())
        if info:
            lang = info.split(None, 1)[0]
            lang_parameter = self.parameter(name="language", value=lang)
            root_element.append(lang_parameter)
        root_element.append(self.parameter(name="linenumbers", value="true"))
        if code and code[-1] != "\n":
            code += "\n"
        root_element.append(self.plain_text_body(code))
        return root_element.render()

    def image(self, alt, url, title=None):
        attributes = {"alt": alt}
        if title:
            attributes["title"] = title

        root_element = ConfluenceTag(name="image", attrib=attributes)
        parsed_source = urlparse.urlparse(url)
        if not parsed_source.netloc:
            # Local file, requires upload
            basename = Path(parsed_source.path).name
            url_tag = ConfluenceTag(
                "attachment", attrib={"filename": basename}, namespace="ri"
            )
            self.attachments.append(urlparse.unquote(parsed_source.path))
        else:
            url_tag = ConfluenceTag("url", attrib={"value": url}, namespace="ri")
        root_element.append(url_tag)

        return root_element.render()
