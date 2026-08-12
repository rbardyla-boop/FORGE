FROM python:3.12-alpine
COPY tests/w4_fixture/provider/provider.py /usr/local/bin/w4-provider
RUN chmod 0755 /usr/local/bin/w4-provider
ENTRYPOINT ["/usr/local/bin/python3", "/usr/local/bin/w4-provider"]
