#!/usr/bin/env bash
# GitHub web upload cannot carry binaries, so the unseen PDF is stored as base64. Run once from the repo root:
for d in unseen_v4/docs runs_v4/unseen_vet_b/docs; do mkdir -p $d; base64 -d unseen_v4/docs/vaccinations_and_invoices.pdf.b64 > $d/vaccinations_and_invoices.pdf; done
echo restored
