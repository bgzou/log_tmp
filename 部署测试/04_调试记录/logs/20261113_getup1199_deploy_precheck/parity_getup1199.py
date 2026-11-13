"""getup1199 C++ replay parity check (fixture vs python reference)."""
import sys

exp = {}
for line in open(sys.argv[1]):  # expected: elapsed, wrapped(12), command(12), blend
    f = [float(x) for x in line.split()]
    exp[round(f[0], 4)] = f[1:]

got = {}
for line in open(sys.argv[2]):  # C++ GETUP1199_TARGET: elapsed, action(12), command(12), blend, h_est, up
    if not line.startswith("GETUP1199_TARGET,"):
        continue
    f = [float(x) for x in line.split(",")[1:]]
    got[round(f[0], 4)] = f[1:]

assert len(exp) == len(got) == 550, (len(exp), len(got))
act_err = com_err = blend_err = 0.
worst = (0, -1, None)
for t in sorted(exp):
    e, g = exp[t], got[t]
    for i in range(12):
        act_err = max(act_err, abs(e[i] - g[i]))
        com_err = max(com_err, abs(e[12 + i] - g[12 + i]))
    blend_err = max(blend_err, abs(e[24] - g[24]))
    if act_err > worst[1]:
        worst = (t, act_err, None)

print(f"frames={len(exp)} action_max_err={act_err:.3e} command_max_err={com_err:.3e} "
      f"blend_max_err={blend_err:.3e}")
print("PARITY", "PASS" if act_err <= 1e-6 and com_err <= 1e-6 else "FAIL")
