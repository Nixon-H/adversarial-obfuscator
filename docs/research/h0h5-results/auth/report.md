# H0-H5 transfer experiment: auth

config `48221407c909` · corpus `f229091311ee` · elapsed 70.0s

excluded builds: 0

## cost + coverage per arm (mean)
- H0: n=6 build=0.04s size=1959B vm=0/0 gate-pass=6/6
- H1: n=6 build=0.01s size=2232B vm=0/0 gate-pass=6/6
- H2: n=6 build=0.01s size=1075B vm=0/0 gate-pass=6/6
- H3: n=6 build=0.01s size=979B vm=0/0 gate-pass=6/6
- H4: n=6 build=0.00s size=983B vm=0/0 gate-pass=6/6
- H5: n=6 build=0.01s size=2123B vm=0/0 gate-pass=6/6

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
