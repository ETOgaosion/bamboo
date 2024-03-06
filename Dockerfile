FROM whatcanyousee/bamboo-base:latest

ENV PATH=/workspace/bin:$PATH

COPY . /workspace
RUN pip install -e /workspace/project_pactum/external/deepspeed