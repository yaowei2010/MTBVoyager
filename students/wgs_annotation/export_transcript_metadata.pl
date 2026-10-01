#!/usr/bin/env perl
# One-time read-only export of VEP 112 transcript selection metadata.
# Run inside ensemblorg/ensembl-vep:release_112.0; never annotates variants.
use strict;
use warnings;
use Storable qw(fd_retrieve);
use JSON::PP;
use File::Glob qw(bsd_glob);

my ($cache, @chromosomes) = @ARGV;
die "Usage: export_transcript_metadata.pl CACHE_DIR [CHROM ...]\n" unless $cache;
open(my $info, '<', "$cache/info.txt") or die $!;
my %info;
while (<$info>) { chomp; my ($k, $v) = split /\t/, $_, 2; $info{$k} = $v if defined $v; }
die "Only homo_sapiens GRCh38 Ensembl 112 is supported\n"
  unless ($info{species} || '') eq 'homo_sapiens' && ($info{assembly} || '') eq 'GRCh38'
  && $cache =~ /112_GRCh38\/?$/;
@chromosomes = map { s/^.*\///r } grep {-d $_} bsd_glob("$cache/*") unless @chromosomes;
my %seen;
my $encoder = JSON::PP->new->canonical;
for my $chrom (sort @chromosomes) {
  for my $file (sort(bsd_glob("$cache/$chrom/*.gz"))) {
    next unless $file =~ /\/\d+-\d+\.gz$/;
    open(my $fh, '-|', 'gzip', '-dc', $file) or die "Cannot read $file\n";
    my $data = fd_retrieve($fh);
    close($fh) or die "Decompression failed: $file\n";
    for my $transcripts (values %$data) {
      for my $tr (@$transcripts) {
        my $id = $tr->{stable_id};
        next unless $id;
        next if $seen{$id}++;
        my %attrs = map { $_->{code} => $_->{value} } @{$tr->{attributes} || []};
        my $vep = $tr->{_variation_effect_feature_cache} || {};
        my $length = $tr->{translation} ? length($vep->{translateable_seq} || '') : 0;
        if (!$length && $tr->{translation} && $tr->{cdna_coding_end} && $tr->{cdna_coding_start}) {
          $length = $tr->{cdna_coding_end} - $tr->{cdna_coding_start} + 1;
        }
        if (!$length) {
          $length += $_->{end} - $_->{start} + 1 for @{$vep->{sorted_exons} || $tr->{_trans_exon_array} || []};
        }
        my $tsl = ($attrs{TSL} || '') =~ /tsl(\d+)/ ? $1 : '';
        my $appris = $attrs{appris} || '';
        $appris =~ s/principal/P/; $appris =~ s/alternative/A/;
        my $row = {
          Feature => $id, Gene => $tr->{_gene_stable_id} || '', SYMBOL => $tr->{_gene_symbol} || '',
          CANONICAL => $tr->{is_canonical} ? 'YES' : '', BIOTYPE => $tr->{biotype} || '',
          MANE_SELECT => $attrs{MANE_Select} || '', MANE_PLUS_CLINICAL => $attrs{MANE_Plus_Clinical} || '',
          APPRIS => $appris, TSL => $tsl, CCDS => $tr->{_ccds} || '',
          ENSP => $tr->{_protein} || ($tr->{translation} || {})->{stable_id} || '',
          _length => $length, _cache_release => 112, _assembly => 'GRCh38',
        };
        print $encoder->encode($row), "\n";
      }
    }
  }
}
die "No transcripts exported\n" unless keys %seen;
print STDERR scalar(keys %seen), " transcripts exported\n";
