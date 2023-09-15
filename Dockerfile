FROM python:3-alpine
ARG VERSION

RUN mkdir -p /content && \
    pip install md2cf==${VERSION}

WORKDIR /content
ENTRYPOINT ["/usr/local/bin/md2cf"]
CMD ["--parent-id ${CONFLUENCE_PARENT_ID} --minor-edit --preface-markdown --only-changed --skip-empty --beautify-folders --collapse-single-pages /content"]
