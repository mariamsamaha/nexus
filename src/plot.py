import matplotlib.pyplot as plt

threads = [1, 2, 4, 8]
speedup = [0.89469, 1.84056, 0.98113, 1.30491]
efficiency = [0.89469, 0.92028, 0.24528, 0.16311]

plt.figure()
plt.plot(threads, speedup, 'o-', label='Speedup')
plt.plot(threads, threads, '--', label='Ideal Speedup')
plt.xlabel('Threads')
plt.ylabel('Speedup')
plt.legend()
plt.grid(True)
plt.show()

plt.figure()
plt.plot(threads, efficiency, 'o-', color='orange', label='Efficiency')
plt.xlabel('Threads')
plt.ylabel('Efficiency')
plt.grid(True)
plt.legend()
plt.show()
