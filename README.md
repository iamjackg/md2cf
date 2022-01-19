# md2cf

[![image](https://img.shields.io/travis/iamjackg/md2cf/master.svg?label=master)](https://travis-ci.org/iamjackg/md2cf)

[![image](https://img.shields.io/travis/iamjackg/md2cf/develop.svg?label=develop)](https://travis-ci.org/iamjackg/md2cf)

A tool and library to convert documents written in Markdown to Confluence Storage
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

```text
usage: md2cf [-h] [-o HOST] [-u USERNAME] [-p PASSWORD] -s SPACE
             [-a PARENT_TITLE | -A PARENT_ID] [-t TITLE] [-m MESSAGE]
             [-i PAGE_ID] [--prefix PREFIX]
             [--preface-markdown [PREFACE_MARKDOWN] | --preface-file
             PREFACE_FILE] [--collapse-single-pages]
             [--beautify-folders | --use-pages-file]
             [--collapse-empty | --skip-empty] [--dry-run] [--only-changed]
             [file_list [file_list ...]]
```

In order to upload a document, you'll need to supply at least the
following five parameters:

  - The **hostname** of your Confluence instance, including the path to
    the REST API (e.g. `http://confluence.example.com/rest/api`)
  - The **username** to use for logging into the instance
  - The corresponding **password**
  - The **space** in which to publish the page
  - The **files or directories** to be uploaded -- or standard input if the list is
    missing

Example basic usage:

```bash
md2cf --host 'https://confluence.example.com/rest/api' --username foo --password bar --space TEST document.md
```

Note that entering the password as a parameter on the command line is
generally a bad idea. If you're running the script interactively, you
can omit the `--password` parameter and the script will prompt for it.

For the security conscious out there or those who plan on
using this as part of a pipeline, you can also supply the hostname,
username, and password as **environment variables**: `CONFLUENCE_HOST`,
`CONFLUENCE_USERNAME`, and `CONFLUENCE_PASSWORD`.

You can specify multiple files and/or entire folders. If you specify a folder, it will be traversed recursively and all files ending in `.md` will be uploaded. See [Uploading folders](#uploading-folders) for more information.

If you just want to get a preview of what `md2cf` would try to upload, the `--dry-run` option will print a list of page data but leave Confluence untouched.

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

### Adding a preface

The `--preface-markdown` and `--preface-file` commands allow you to add some text at the top of each page. This is useful
if you're mirroring documentation to Confluence and want people to know that it's going to be overwritten in an automated
fashion.

The first option allows you to specify markdown text right on the command line, and defaults to a paragraph saying

**Contents are auto-generated, do not edit.**

The second option takes a path to a markdown file and will prepend its contents to every page. Note that this is parsed
separately and added to the body after the main page has been parsed, so it won't influence behaviour tied to the page
contents such as title or front matter detection. 

### Parent page

If you want to upload the page under **a specific parent**, you can supply the parent's page ID as the `--parent-id` parameter, or its title through the `--parent-title` parameter. Note 

### Update message

You can also optionally specify an **update message** to describe the
change you just made by using the `--message` parameter. Note that if you're using the `--only-changed` option there will also be a hash of the page/attachment contents at the end of the version update message.

### Updating an existing page

Uploading a page with the same title twice will update the existing one.

If you want to update a page by page ID, use the `--page-id` option. This allows you to change the page's title, or to update a page with a title that is annoying to use as a parameter.

### Avoiding uploading content that hasn't changed

If you want to avoid redundant uploads (and the corresponding update emails) when your content hasn't changed, you can add the `--only-changed` option. Note that this will store a hash of the page/attachment contents at the end of the version update message.

### Uploading folders

`md2cf` can upload entire folders for you. This can be useful if you want to mirror some in-repo documentation to Confluence.

When uploading entire folders, `md2cf` will recursively traverse all subdirectories and upload any `.md` file it encounters. Folders will be represented by empty pages in the final upload, since Confluence can only nest pages under other pages. You can modify this behaviour through three command line parameters.

#### Customizing folder names

Folder names like `interesting-subsection` or `dir1` are not particularly nice. If you pass the `--beautify-folders` option,
all spaces and hyphens in folder names will be replaced with spaces and the first letter will be capitalized, producing
`Interesting subsection` and `Dir1`.

Alternatively, you can create a YAML file called `.pages` with the following format in every folder you wish to rename.
If you pass the `--use-pages-file`, the folder will be given that title.

```yaml
title: "This is a fantastic title!"
```

#### Collapse single pages

You can collapse directories that only contain one document by passing the `--collapse-single-pages` parameter. This means that a folder layout like this:

```text
document.md
folder1/
  documentA.md
  documentB.md
folder2/
  other-document.md
```

will be uploaded to Confluence like this:

```text
document
folder1/
  documentA
  documentB
other-document
```

#### Dealing with empty folders

You can also modify the behaviour for empty folders. If you specify `--skip-empty`, this tree layout:

```text
document.md
folder1/
  folder2/
    folder3/
      other-document.md
folderA/
  interesting-document.md
    folderB/
      folderC/
        lonely-document.md
```

will be uploaded as:

```text
document
folder3/
  other-document
folderA/
  interesting-document
  folderC/
    lonely-document
```

Alternatively, you can specify `--collapse-empty` to merge empty folders together with the following result:

```text
document
folder1/folder2/folder3/
  other-document
folderA/
  interesting-document
  folderB/folderC/
    lonely-document
```

## Library usage

`md2cf` can of course be used as a Python library. It exposes two useful modules: the renderer and the API wrapper.

### Renderer

Use the `ConfluenceRenderer` class to generate Confluence Storage Format
output from a markdown document.

```python
import mistune
from md2cf.confluence_renderer import ConfluenceRenderer

markdown_text = "# Page title\n\nInteresting *content* here!"

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
