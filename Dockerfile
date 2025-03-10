FROM whatcanyousee/bamboo-base:latest

ENV PATH=/workspace/bin:$PATH

COPY . /workspace
RUN DS_BUILD_FUSED_ADAM=1 pip install -e /workspace/project_pactum/external/deepspeed
RUN mkdir -p /root/.cache/torch_extensions
RUN mv /workspace/.cache/torch_extensions/py38_cu116 /root/.cache/torch_extensions/
RUN chmod a=r -R /root/.cache/torch_extensions/py38_cu116