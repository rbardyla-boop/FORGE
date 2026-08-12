FROM python:3.12-alpine
COPY tests/w3_fixture/fake_codex.py /usr/local/bin/fake-codex
COPY tests/w3_container/provider_wrapper.py /usr/local/bin/provider-wrapper
RUN chmod 0755 /usr/local/bin/fake-codex /usr/local/bin/provider-wrapper
ENTRYPOINT ["/usr/local/bin/provider-wrapper"]
