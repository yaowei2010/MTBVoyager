FROM takeshi945/nckumtb:backend-20260701

ARG NEXTFLOW_VERSION=26.04.6
COPY nextflow /usr/local/bin/nextflow
RUN chmod 0755 /usr/local/bin/nextflow && NXF_VER=${NEXTFLOW_VERSION} nextflow -version

COPY wgs_germline /miRTI/wgs_germline
COPY uploadfunction/urls.py /miRTI/uploadfunction/urls.py
COPY pipeline /opt/wgs-germline-pipeline

ENV WGS_PIPELINE_SOURCE=/opt/wgs-germline-pipeline \
    NXF_VER=${NEXTFLOW_VERSION} \
    NXF_ANSI_LOG=false

