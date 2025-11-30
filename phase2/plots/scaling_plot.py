#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def plot_strong():
    csv = "phase2/results/strong_scaling/strong_scaling.csv"
    df = pd.read_csv(csv)
    p = df['ranks'].values
    t = df['walltime_s'].values.astype(float)
    t0 = t[0] if len(t)>0 else 1.0
    speedup = t0 / t
    eff = speedup / p

    plt.figure()
    plt.plot(p, speedup, marker='o')
    plt.xlabel('ranks')
    plt.ylabel('speedup')
    plt.title('Strong scaling: speedup')
    plt.grid(True)
    plt.savefig('phase2/results/strong_scaling/speedup.png', dpi=200)

    plt.figure()
    plt.plot(p, eff, marker='o')
    plt.xlabel('ranks')
    plt.ylabel('efficiency')
    plt.title('Strong scaling: efficiency')
    plt.grid(True)
    plt.savefig('phase2/results/strong_scaling/efficiency.png', dpi=200)
    print("Saved strong scaling plots.")

def plot_weak():
    csv = "phase2/results/weak_scaling/weak_scaling.csv"
    df = pd.read_csv(csv)
    p = df['ranks'].values
    t = df['walltime_s'].values.astype(float)
    plt.figure()
    plt.plot(p, t, marker='o')
    plt.xlabel('ranks')
    plt.ylabel('walltime (s)')
    plt.title('Weak scaling: walltime vs ranks (constant work per rank)')
    plt.grid(True)
    plt.savefig('phase2/results/weak_scaling/weak_scaling.png', dpi=200)
    print("Saved weak scaling plots.")

if __name__ == "__main__":
    plot_strong()
    plot_weak()
