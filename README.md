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

TBD

## Basic Usage

### Renderer

Use the `ConfluenceRenderer` class to generate Confluence Storage Format
output from a markdown document.

``` sourceCode python
import mistune
from md2cf.confluence_renderer import ConfluenceRenderer

renderer = ConfluenceRenderer(use_xhtml=True)
confluence_mistune = mistune.Markdown(renderer=renderer)
confluence_body = confluence_mistune(markdown_data)
```

### API

md2cf embeds a teeny-tiny implementation of the Confluence Server REST
API that allows you to create, read, and update pages.

``` sourceCode python
from md2cf.api import MinimalConfluence

confluence = MinimalConfluence(host='http://example.com/rest/api', username='foo', password='bar')

confluence.create_page(space='TEST', title='Test page', body='<p>Nothing</p>', message='Created page')

page = confluence.get_page(title='Test page', space_key='TEST')
confluence.update_page(page=page, body='New content', message='Changed page contents')
```

### Upload script

In order to upload a document, you'll need to supply at least the
following five parameters:

  - The **hostname** of your Confluence instance, including the path to
    the REST API (e.g. `http://confluence.example.com/rest/api`)
  - The **username** to use for logging into the instance
  - The corresponding **password**
  - The **space** on which to upload the page
  - The **file(s)** to be uploaded -- or standard input if the list is
    missing

Example basic
    usage:

    md2cf --host 'https://confluence.example.com/rest/api' --username foo --password bar --space TEST document.md

Note that entering the password as a parameter on the command line is
generally a bad idea. If you're running the script interactively, you
can omit the `--password` parameter and the script will prompt for it.

In addition, for the security conscious out there or those who plan on
using this as part of a pipeline, you can also supply the hostname,
username, and password as **environment variables**: `CONFLUENCE_HOST`,
`CONFLUENCE_USERNAME`, and `CONFLUENCE_PASSWORD`.

The **title** of the page will be the first top-level header found in
the document (i.e. the first `#` header), or the filename if there are
no top-level headers.

If you want to upload the page under **a specific parent**, supply the
parent's page ID as the `--parent` parameter.

You can also optionally specify an **update message** to describe the
change you just made by using the `--message` parameter.
