"""Quantify low-frequency leg motion in already-captured real-robot logs."""
import csv
from pathlib import Path
import numpy as np

p = Path(__file__).with_name("20261112_r1199_joystick_capture_10ms.csv")
with p.open(encoding="utf-8",newline="") as f:
    rows=list(csv.DictReader(f))
t=np.array([float(r["capture_elapsed_s"]) for r in rows])
q=np.array([[float(r[f"m{i}_q"]) for i in range(12)] for r in rows])
dq=np.array([[float(r[f"m{i}_dq"]) for i in range(12)] for r in rows])
tau=np.array([[float(r[f"m{i}_tau_est"]) for i in range(12)] for r in rows])

def summarize(lo,hi,label):
    sel=(t>=lo)&(t<hi)
    xq,xdq,xtau=q[sel],dq[sel],tau[sel]
    dt=float(np.median(np.diff(t[sel])))
    def highpass(x):
        width=max(3,round(.20/dt))
        smooth=np.array([np.convolve(x[:,i],np.ones(width)/width,mode="same") for i in range(x.shape[1])]).T
        return (x-smooth)[width:-width]
    qhp=highpass(xq); tauhp=highpass(xtau)
    # Spectral peak is descriptive only; 100 Hz state sampling aliases higher vibration.
    freqs=np.fft.rfftfreq(len(tauhp),dt)
    power=np.abs(np.fft.rfft(tauhp,axis=0))**2
    mean_power=power.mean(axis=1)
    band=(freqs>=2)&(freqs<=40)
    dom=float(freqs[band][np.argmax(mean_power[band])])
    print(label,"n",len(xq),"dt",round(dt,4),
          "leg_dq_rms",round(float(np.sqrt(np.mean(xdq**2))),4),
          "leg_dq_peak",round(float(np.max(np.abs(xdq))),4),
          "q_hp_rms",round(float(np.sqrt(np.mean(qhp**2))),5),
          "tau_hp_rms",round(float(np.sqrt(np.mean(tauhp**2))),4),
          "tau_peak",round(float(np.max(np.abs(xtau))),4),
          "tau_spectrum_peak_Hz",round(dom,2))

for a,b,name in [(27,35,"zero_high_pose"),(37,39,"first_push"),
                 (40,48,"short_pulses"),(53,67,"long_forward"),
                 (72,78,"after_release")]:
    summarize(a,b,name)
