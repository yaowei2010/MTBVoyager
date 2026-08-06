FROM takeshi945/nckumtb:backend-20260701

ARG NEXTFLOW_VERSION=26.04.6
COPY nextflow /usr/local/bin/nextflow
RUN chmod 0755 /usr/local/bin/nextflow && NXF_VER=${NEXTFLOW_VERSION} nextflow -version

COPY wgs_somatic /miRTI/wgs_somatic
COPY pipeline /opt/wgs-somatic-pipeline

ENV WGS_SOMATIC_PIPELINE_SOURCE=/opt/wgs-somatic-pipeline \
    NXF_VER=${NEXTFLOW_VERSION} \
    NXF_ANSI_LOG=false
