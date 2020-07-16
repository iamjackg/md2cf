# md2cf

[![image](https://img.shields.io/travis/iamjackg/md2cf/master.svg?label=master)](https://travis-ci.org/iamjackg/md2cf)

[![image](https://img.shields.io/travis/iamjackg/md2cf/develop.svg?label=develop)](https://travis-ci.org/iamjackg/md2cf)

A library to convert documents written in Markdown to Confluence Storage
format, and optionally upload them to a Confluence Server instance.

## Features

  - **Convert Markdown documents.** The library implements a
    [Mistune](https://github.com/lepture/mistune) renderer that outputs
    Confluence Storage Format.
  - **Basic Confluence API support.** Embedded micro-implementation of
    the [Confluence Server REST
    API](https://developer.atlassian.com/server/confluence/confluence-server-rest-api/)
    with basic support for creating and updating pages.
  - **Upload automation.** Includes a small script that can automate the
    upload process for you.

## Installation

```bash
pip install md2cf
```

## Upload script

In order to upload a document, you'll need to supply at least the
following five parameters:

  - The **hostname** of your Confluence instance, including the path to
    the REST API (e.g. `http://confluence.example.com/rest/api`)
  - The **username** to use for logging into the instance
  - The corresponding **password**
  - The **space** in which to publish the page
  - The **file(s)** to be uploaded -- or standard input if the list is
    missing

Example basic usage:

```bash
md2cf --host 'https://confluence.example.com/rest/api' --username foo --password bar --space TEST document.md
```

You can specify multiple files and/or entire folders. If you specify a folder, it will be travelled recursively and all files ending in `.md` will be uploaded. The structure of the folder will be recreated using empty pages to represent subdirectories. 

Note that entering the password as a parameter on the command line is
generally a bad idea. If you're running the script interactively, you
can omit the `--password` parameter and the script will prompt for it.

In addition, for the security conscious out there or those who plan on
using this as part of a pipeline, you can also supply the hostname,
username, and password as **environment variables**: `CONFLUENCE_HOST`,
`CONFLUENCE_USERNAME`, and `CONFLUENCE_PASSWORD`.

### Page title

The **title** of the page can come from a few sources, in order of priority from highest to lowest:
* the `--title` command line parameter
* a `title` entry in your document's front matter, i.e. a YAML block delimited by `---` lines at the top of the file
  ```yaml
  ---
  title: This is a title
  ---
  # Rest of the document here
  ``` 
* the first top-level header found in the document (i.e. the first `#` header)
* the filename if there are no top-level headers.

Note that if you're reading from standard input, you must either specify the title through the command line or have a title in the content as a header or in the front matter.

If you're uploading entire folders, you might want to add a prefix to each page title in order to avoid collisions. You can do this using the `--prefix` parameter.

### Parent page

If you want to upload the page under **a specific parent**, you can supply the parent's page ID as the `--parent-id` parameter, or its title through the `--parent-title` parameter. Note 

### Update message

You can also optionally specify an **update message** to describe the
change you just made by using the `--message` parameter.

### Updating an existing page

Uploading a page with the same title twice will update the existing one.

If you want to update a page by page ID, use the `--page-id` option. This allows you to change the page's title, or to update a page with a title that is annoying to use as a parameter.

## Library usage

`md2cf` can of course be used as a Python library. It exposes two useful modules: the renderer and the API wrapper.

### Renderer

Use the `ConfluenceRenderer` class to generate Confluence Storage Format
output from a markdown document.

```python
import mistune
from md2cf.confluence_renderer import ConfluenceRenderer

renderer = ConfluenceRenderer(use_xhtml=True)
confluence_mistune = mistune.Markdown(renderer=renderer)
confluence_body = confluence_mistune(markdown_text)
```

### API

md2cf embeds a teeny-tiny implementation of the Confluence Server REST
API that allows you to create, read, and update pages.

```python
from md2cf.api import MinimalConfluence

confluence = MinimalConfluence(host='http://example.com/rest/api', username='foo', password='bar')

confluence.create_page(space='TEST', title='Test page', body='<p>Nothing</p>', update_message='Created page')

page = confluence.get_page(title='Test page', space_key='TEST')
confluence.update_page(page=page, body='New content', update_message='Changed page contents')
```
