FROM takeshi945/nckumtb:backend-20260701

ARG NEXTFLOW_VERSION=26.04.6
COPY patch_legacy_somatic_status.py /tmp/patch_legacy_somatic_status.py
RUN python /tmp/patch_legacy_somatic_status.py /miRTI/hw1/views.py \
    && rm /tmp/patch_legacy_somatic_status.py
COPY nextflow /usr/local/bin/nextflow
RUN chmod 0755 /usr/local/bin/nextflow && NXF_VER=${NEXTFLOW_VERSION} nextflow -version

COPY wgs_germline /miRTI/wgs_germline
COPY --from=wgs_somatic wgs_somatic /miRTI/wgs_somatic
COPY uploadfunction/urls.py /miRTI/uploadfunction/urls.py
COPY pipeline /opt/wgs-germline-pipeline
COPY --from=wgs_somatic pipeline /opt/wgs-somatic-pipeline

ENV WGS_PIPELINE_SOURCE=/opt/wgs-germline-pipeline \
    WGS_SOMATIC_PIPELINE_SOURCE=/opt/wgs-somatic-pipeline \
    NXF_VER=${NEXTFLOW_VERSION} \
    NXF_ANSI_LOG=false
