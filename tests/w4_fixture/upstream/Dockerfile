FROM python:3.12-alpine
COPY tests/w4_fixture/upstream/fake_upstream.py /usr/local/bin/fake-upstream
RUN chmod 0755 /usr/local/bin/fake-upstream
ENTRYPOINT ["/usr/local/bin/python3", "/usr/local/bin/fake-upstream"]
