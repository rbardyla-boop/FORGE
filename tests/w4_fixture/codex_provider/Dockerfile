FROM python:3.12-alpine
COPY tests/w4_fixture/codex_provider/fake_codex_brokered.py /usr/local/bin/w4-codex-fixture
RUN chmod 0755 /usr/local/bin/w4-codex-fixture
ENTRYPOINT ["/usr/local/bin/python3", "/usr/local/bin/w4-codex-fixture"]
