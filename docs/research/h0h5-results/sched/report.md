# H0-H5 transfer experiment: sched

config `48221407c909` · corpus `2571f572ab26` · elapsed 65.2s

excluded builds: 0

## cost + coverage per arm (mean)
- H0: n=6 build=0.04s size=8841B vm=0/0 gate-pass=6/6
- H1: n=6 build=0.02s size=8840B vm=0/0 gate-pass=6/6
- H2: n=6 build=0.01s size=1500B vm=0/0 gate-pass=6/6
- H3: n=6 build=0.00s size=1294B vm=0/0 gate-pass=6/6
- H4: n=6 build=0.00s size=1268B vm=0/0 gate-pass=6/6
- H5: n=6 build=0.02s size=8931B vm=0/0 gate-pass=6/6

## arm: static
- H0: T=['1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00', '1.00'] (control)
- H1 vs H0: p=1.0000 med=1.000/1.000 → FAIL-TO-DISTINGUISH — do not claim transfer resistance
- H2 vs H0: p=1.0000 med=1.000/1.000 → FAIL-TO-DISTINGUISH — do not claim transfer resistance
- H3 vs H0: p=1.0000 med=1.000/1.000 → FAIL-TO-DISTINGUISH — do not claim transfer resistance
- H4 vs H0: p=1.0000 med=1.000/1.000 → FAIL-TO-DISTINGUISH — do not claim transfer resistance
- H5 vs H0: p=1.0000 med=1.000/1.000 → FAIL-TO-DISTINGUISH — do not claim transfer resistance
taxonomy:
  - function: med_h=1.000 med_s=1.000 p=1.0000
  - semantic: med_h=1.000 med_s=1.000 p=1.0000
  - constant: med_h=1.000 med_s=1.000 p=1.0000
  - name: med_h=1.000 med_s=1.000 p=1.0000
  - cfg: UNCOVERED
  - dataflow: UNCOVERED
  - vm: UNCOVERED
