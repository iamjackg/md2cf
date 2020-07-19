# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased
- Add support for image attachments
- Add support for recursive upload of directories
- Skip empty directories
- Collapse empty directories
- Collapse single-document folders
- Remove dependency on BeautifulSoup by finding the title during rendering
- Can now specify the title in the YAML front matter
- Can now specify a prefix to add to the title of each page
- Existing pages can be moved to a different parent
- Add dry run option

## 0.2.2 - 2019-10-22
- Bump depdendencies

## 0.2.1 - 2019-10-16
- Don't dump arguments to stdout

## 0.2.0 - 2019-10-11
- Can now update by page ID
- Can now specify the page title on the command line

## 0.1.3 - 2019-10-08
- Removed support for Python 3.4

## 0.1.2 - 2019-10-08
- Correctly use filename as page title when there is no top level header

## 0.1.1 - 2019-05-19
- Fixed parameter name in main (@yauhenishaikevich)

## 0.1.0 - 2018-12-11
### Added
- Initial support for converting and uploading documents
- Unit tests
