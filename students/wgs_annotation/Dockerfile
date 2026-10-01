FROM mtb-fastvep:0.3.0-ac2e2b6 AS fastvep
FROM python:3.12.4-slim
LABEL org.opencontainers.image.title="MTB WGS fastVEP annotation" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.revision="ac2e2b64a9c4c27163a3df16e0a559113af19625"
RUN apt-get update && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pysam==0.23.3 ijson==3.4.0
COPY --from=fastvep /usr/local/bin/fastvep /usr/local/bin/fastvep
COPY fastvep_to_mtb.py /usr/local/bin/fastvep_to_mtb.py
RUN chmod 0755 /usr/local/bin/fastvep_to_mtb.py
ENV PYTHONUNBUFFERED=1
CMD ["fastvep", "--help"]
