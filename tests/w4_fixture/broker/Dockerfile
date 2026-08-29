FROM python:3.12-alpine
WORKDIR /opt/forge
COPY forge_core /opt/forge/forge_core
COPY tests/w4_fixture/broker /opt/w4-broker
RUN chmod 0755 /opt/w4-broker/entrypoint.py /opt/w4-broker/fake_credential_proxy.py
ENTRYPOINT ["/usr/local/bin/python3", "/opt/w4-broker/entrypoint.py"]
