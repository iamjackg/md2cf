# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased
### Added
- Add option to remove the top level header from the page

## 1.3.1 - 2022-04-30
### Changed
- Upgraded PyYAML to 6.0

## 1.3.0 - 2022-04-25
- Add support for bearer token authentication (thanks @Guuz1)

## 1.2.0 - 2022-04-24
- Add option to ignore SSL certificate validation

## 1.1.2 - 2022-01-25
- Fix a bug that would not match the content hash when another message was present

## 1.1.1 - 2022-01-18
- Fix a bug that prevented uploading directories specified with a relative path

## 1.1.0 - 2022-01-18
- Add feature to only update things that have changed by storing the SHA1 in the update message
- Make attachment updates work on both Confluence Server and Confluence Cloud

## 1.0.4 - 2021-11-25
- Remove mentions of non-existing force-unique parameter
- Bump dependencies
- Fix attachment update function (@timothybonci)

## 1.0.3 - 2021-08-27
- Fix dependency versions

## 1.0.2 - 2020-07-19
- Remove support for Python 3.5

## 1.0.1 - 2020-07-19
- Update README.md to correctly show help output

## 1.0.0 - 2020-07-19
- Add support for image attachments
- Add support for recursive upload of directories
- Skip empty directories
- Collapse empty directories
- Collapse single-document folders
- Support folder title customization
- Remove dependency on BeautifulSoup by finding the title during rendering
- Can now specify text top preface to each uploaded page
- Can now specify a page title in the YAML front matter
- Can now specify a prefix to add to the title of each page
- Existing pages can be moved to a different parent
- Add dry run option

## 0.2.2 - 2019-10-22
- Bump dependencies

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
