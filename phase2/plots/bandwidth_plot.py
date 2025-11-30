#!/usr/bin/env python3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys

csv = "phase2/results/latency_bandwidth/latency_bandwidth.csv"
df = pd.read_csv(csv, comment='#', names=['type','size','time','bw'], header=None)

lat = df[df['type']=='latency']
bw = df[df['type']=='bandwidth']

fig, ax1 = plt.subplots()
ax1.loglog(lat['size'], lat['time'], marker='o', label='latency (s)')
ax1.set_xlabel('message size (bytes)')
ax1.set_ylabel('latency (s)')
ax1.grid(True, which="both", ls="--")
ax1.legend(loc='upper left')

ax2 = ax1.twinx()
ax2.loglog(bw['size'], bw['bw'], marker='s', label='bandwidth (MB/s)', base=2)
ax2.set_ylabel('bandwidth (MB/s)')
ax2.legend(loc='lower right')

plt.title('MPI latency & bandwidth microbenchmark')
plt.savefig('phase2/results/latency_bandwidth/latency_bandwidth.png', dpi=200)
print("Saved phase2/results/latency_bandwidth/latency_bandwidth.png")
