# md2cf

`md2cf` is a tool and library that allows you to convert Markdown documents to Confluence Storage format and upload them to a Confluence instance.

## Features

- **Convert Markdown documents:** `md2cf` includes a library that implements a [Mistune](https://github.com/lepture/mistune) renderer, which outputs Confluence Storage Format.
- **Talk to the Confluence API:** `md2cf` also features an embedded micro-implementation of the [Confluence Server REST API](https://developer.atlassian.com/server/confluence/confluence-server-rest-api/) with basic support for creating and updating pages and attachments.
- **Automate the upload process:** You can use `md2cf`'s full-featured command line utility to automate the upload process for you.


## Installation

```bash
# Install md2cf via pip
pip install md2cf

# If you only need to use md2cf for uploading documents to Confluence,
# it's recommended to use pipx:
pipx install md2cf
```

## Getting started

To see all available options and parameters, run `md2cf --help`.

To upload a document, you need to provide at least the following five parameters:

- The **URL** of your Confluence instance, including the path to the REST API (e.g., `http://confluence.example.com/rest/api`)
- Either:
    - The **username** and **password** to log in to the instance
    - A **personal access token**
- The **space** in which to publish the page
- The **files or directories** to be uploaded. If none are specified, the contents will be read from standard input.

Example basic usage:

```bash
md2cf --host 'https://confluence.example.com/rest/api' --username foo --password bar --space TEST document.md
```

Or, if using a token:

```bash
md2cf --host 'https://confluence.example.com/rest/api' --token '2104v3ryl0ngt0k3n720' --space TEST document.md
```

> :warning: Avoid entering your password (or token) as a command line parameter, as this is [generally a bad practice](https://unix.stackexchange.com/q/78734). Instead, when running the script interactively, omit the `--password` parameter and securely enter the password when prompted.

> :warning: Note that tokens function differently between [Confluence Cloud](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/) and [self-hosted instances](https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html). When using Confluence Cloud, you should use your token **as your password** with the `--username` and `--password` parameters. With self-hosted instances, use the `--token` parameter instead.

You can also supply the hostname, username, password, token, and space as **environment variables**:

- `CONFLUENCE_HOST`
- `CONFLUENCE_USERNAME`
- `CONFLUENCE_PASSWORD`
- `CONFLUENCE_TOKEN`
- `CONFLUENCE_SPACE`

If you are using self-signed certificates or want to **ignore SSL errors**, use the `--insecure` option.

You can **upload multiple files** or entire folders. If you specify a folder, `md2cf` will traverse it recursively and upload all files that end in `.md`. For more information, see [Uploading Folders](#uploading-folders).

If you would like to preview `md2cf`'s actions without modifying Confluence, use the `--dry-run` option. This will print a list of page data without making any changes.

## Page information arguments

### Page title

The title of the page can be sourced from multiple places, in the following order of priority:
* The `--title` command-line parameter
* A `title` entry in the document's front matter, which is a YAML block delimited by `---` lines at the top of the file:

  ```yaml
  ---
  title: This is a title
  ---
  ```
* The first top-level header found in the document (i.e., the first `#` header)
* The filename, if there are no top-level headers.

Note that if you are reading from standard input, you must either specify the title through the command line or include a title as a header or in the front matter within the content.

To avoid repeating the top level header in the body of the page, pass the `--strip-top-header` parameter to strip it from the document.

When uploading entire folders, consider adding a prefix to each page title to prevent collisions. You can do this by using the `--prefix` parameter.

### Removing extra newlines

If your document uses single newlines to break lines (for example, if it was typeset with a fixed column width), Confluence Cloud might preserve those newlines, resulting in a document that's difficult to read. To fix this, use the `--remove-text-newlines` parameter, which replaces every newline within a paragraph with a space.


<details>
<summary>Example</summary>
For example, this will turn

```text
This is a document
with hardcoded newlines
in its paragraphs.

It's not that nice
to read.
```

into

```text
This is a document with hardcoded newlines in its paragraphs.

It's not that nice to read.
```
</details>

### Adding a preface and/or postface

The `--preface-markdown`, `--preface-file`, `--postface-markdown`, and `--postface-file` commands enable you to add text at the beginning or end of each page. This is especially helpful if you're mirroring documentation to Confluence and want to notify users that it will be automatically updated.

The `--preface-markdown` and `--postface-markdown` options allow you to specify Markdown text directly in the command line. If no text is specified, a default paragraph will be used stating:

> **Contents are auto-generated, do not edit.**

Alternatively, the `--preface-file` and `--postface-file` options allow you to specify a path to a markdown file which will be prepended or appended to every page.

> :warning: Note that preface and postface Markdown is parsed separately and added to the body after the main page has been parsed. Therefore, it will not affect behavior tied to the page contents, such as title or front matter detection.

### Page labels

To add labels to your page, include a `labels` entry in your document's front matter. The front matter is a YAML block delimited by `---` lines at the top of the file. Here's an example:

```yaml
---
labels:
- first label
- second label
---
# Rest of the Markdown document
```

Note that by default, the labels you specify will be added to any existing labels. If you want to replace all existing labels with only the ones you specified, use the `--replace-all-labels` option.

### Parent page

To upload the page under **a specific parent**, you can provide the parent's page ID using the `--parent-id` parameter, or its title using the `--parent-title` parameter.

To move a page to a **top-level page** (i.e. directly under the space's Home Page), use the `--top-level` flag.

### Update message

Optionally, you can provide an **update message** using the `--message` parameter to describe the change you made. If you're using the `--only-changed` option at the same time, the version update message will also include a hash of the page or attachment contents at the end.

### Updating an existing page

If you upload a page with the same title twice, it will update the existing page.

To update a page using its ID, use the `--page-id` option. This allows you to modify the page's title or update a page with a title that is difficult to use as a parameter.

To avoid sending notifications to page watchers, use the `--minor-edit` option. This corresponds to the "Notify watchers" checkbox when editing pages manually.

### Avoiding uploading content that hasn't changed

To avoid re-uploading unchanged content and receiving update emails when there are no changes, consider using the `--only-changed` option. Keep in mind that this option will include a hash of the page or attachment contents in the version update message.

## Linking to other documents (relative links)

By default, support for relative links is disabled. To enable it, pass the `--enable-relative-links` flag. The behavior of relative links is similar to [GitHub relative links](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes#relative-links-and-image-paths-in-readme-files), with the exception that links starting with `/` are **not supported** and will be left unchanged.

Reference to a section from another file is possible using Markdown fragment link navigation:
` [link](./file.md#section-name) // note the dash!`

In file.md:
```
## ...
## section name
```

> :warning: Enabling this function requires two uploads for every page containing relative links. First, a page must be uploaded to Confluence with all internal links replaced by placeholders. Then, once the final Confluence link is known, the placeholders will be replaced with the appropriate links.

By default, relative links that point to non-existent files (or files that are not being uploaded in the current batch) will result in an error. To ignore these errors and keep the links as they are, use the `--ignore-relative-link-errors` flag.

## Directory arguments

### Uploading Folders Recursively

To help you mirror large documentation to Confluence, `md2cf` allows you to upload entire folders. When using this feature, `md2cf` will recursively traverse all subdirectories and upload any `.md` files it encounters.

By default, `md2cf` will respect your `.gitignore` file and skip any files or folders it defines. If you prefer to upload everything in the folder, use the `--no-gitignore` option.

Please note that Confluence can only nest pages under other pages. As a result, folders will be represented by empty pages with the same title as the folder in the final upload. You can customize this behavior using one of the three command line parameters defined in the next sections.

#### Customizing folder names

Folder names like `interesting-subsection` or `dir1` are not particularly nice. If you pass the `--beautify-folders` option, all spaces and hyphens in folder names will be replaced with spaces and the first letter will be capitalized, producing `Interesting subsection` and `Dir1`.

Alternatively, you can create a YAML file called `.pages` with the following format in every folder you wish to rename.
If you pass the `--use-pages-file`, the folder will be given that title.

Folder names like `interesting-subsection` or `dir1` may not be aesthetically pleasing. If you use the `--beautify-folders` option, spaces and hyphens in folder names will be replaced with spaces, and the first letter of each word will be capitalized, resulting in `Interesting Subsection` and `Dir1`.

Alternatively, you can create a YAML file called `.pages` in every folder you want to rename, using the following format, and if you use the `--use-pages-file` option, the folder will be renamed using the title specified in the `.pages` file.

```yaml
title: "This is a fantastic title!"
```

#### Collapse single pages

You can collapse directories that only contain one document by passing the `--collapse-single-pages` parameter.

<details>
<summary>Example</summary>
This means that a folder layout like this:

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
</details>

#### Dealing with empty folders

Passing `--skip-empty` will not create pages for empty folders.

<details>
<summary>Example</summary>
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
</details>

Alternatively, you can specify `--collapse-empty` to merge empty folders together.

<details>
<summary>Example</summary>
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
folder1/folder2/folder3/
  other-document
folderA/
  interesting-document
  folderB/folderC/
    lonely-document
```
</details>

## Terminal output format

By default, `md2cf` produces rich output with animated progress bars that are meant for human consumption. If the output is redirected to a file, the progress bars will not be displayed and only the final result will be written to the file. Error messages are always printed to standard error.

In addition to the default format, `md2cf` also supports two other output formats.

### JSON output

When `--output json` is passed to `md2cf`, the JSON output for each page as returned by Confluence will be printed. Note that normal progress output will not be displayed.

> :warning: Please note that JSON entries will only be printed for page creation/updates. They will not be printed for attachment creation/updates and will not be printed for second-pass updates for [relative links](#linking-to-other-documents-relative-links).


### Minimal output

When passing the `--output minimal` option to `md2cf`, the tool will only print the final Confluence URL for each page, as in versions prior to `2.0.0`. The normal progress output will be omitted.

> :warning: Note that URLs will only be printed for page creation/updates. They will not be printed for attachment creation/updates and will not be printed for second-pass updates for [relative links](#linking-to-other-documents-relative-links).


## Library usage

`md2cf` can of course be used as a Python library. It exposes two useful modules: the renderer and the API wrapper.

### Renderer

Use the `ConfluenceRenderer` class to generate Confluence Storage Format
output from a Markdown document.

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

confluence = MinimalConfluence(host='https://example.com/rest/api', username='foo', password='bar')

confluence.create_page(space='TEST', title='Test page', body='<p>Nothing</p>', update_message='Created page')

page = confluence.get_page(title='Test page', space_key='TEST')
confluence.update_page(page=page, body='New content', update_message='Changed page contents')
```
