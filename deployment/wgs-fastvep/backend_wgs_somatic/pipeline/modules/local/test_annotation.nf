process TEST_ANNOTATION {
    tag "${meta.id}"
    label 'python'
    input:
    tuple val(meta), path(vcf)
    output:
    tuple val(meta), path("${meta.id}.vep.tsv.gz"), emit: tsv
    script:
    """
    python - '${vcf}' '${meta.id}.vep.tsv.gz' <<'PY'
import gzip, sys
src, dst = sys.argv[1:]
with gzip.open(dst, 'wt') as out:
    out.write('#Uploaded_variation\\tLocation\\tAllele\\tSYMBOL\\tConsequence\\tCLIN_SIG\\tExisting_variation\\n')
    with gzip.open(src, 'rt') as inp:
        for line in inp:
            if line.startswith('#'): continue
            c,p,_,r,a=line.split('\\t',5)[:5]
            out.write(f'{c}_{p}_{r}/{a}\\t{c}:{p}\\t{a}\\t.\\t.\\t.\\t.\\n')
PY
    """
}
