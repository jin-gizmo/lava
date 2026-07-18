# ------------------------------------------------------------------------------
#  Generic constants. Safe to important multiple times.
# ------------------------------------------------------------------------------

SHELL:=/bin/bash

LAVA_DOCO_URL=https://jin-gizmo.github.io/lava
_URL=\033]8;;$(LAVA_DOCO_URL)\007$(LAVA_DOCO_URL)\033]8;;\007

e=echo -e
# ANSI codes. Upper case are colours. Lower case, effects (italic etc.). _ is reset.
K=\033[30m
R=\033[31m
G=\033[32m
Y=\033[33m
B=\033[34m
M=\033[35m
C=\033[36m
W=\033[37m
# b(old), d(im), i(talic), u(nderline)
b=\033[1m
d=\033[2m
i=\033[3m
u=\033[4m
# Reset
_=\033[0m

