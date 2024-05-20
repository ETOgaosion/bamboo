FROM whatcanyousee/bamboo-base:latest

ENV PATH=/workspace/bin:$PATH

COPY . /workspace
RUN pip install -v --disable-pip-version-check --no-cache-dir -e /workspace/project_pactum/external/deepspeedei