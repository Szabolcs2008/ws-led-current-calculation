import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from mpl_toolkits.mplot3d import Axes3D

# Load your data
data = np.loadtxt("data.txt", skiprows=1)

R = data[:,0]
G = data[:,1]
B = data[:,2]
I = data[:,3]

# Unique values (grid)
r_vals = np.unique(R)
g_vals = np.unique(G)
b_vals = np.unique(B)

# Initial B value
b_index = 0
current_b = b_vals[b_index]

# Create meshgrid for R and G
R_grid, G_grid = np.meshgrid(r_vals, g_vals)

def get_surface(b_value):
    Z = np.zeros_like(R_grid)
    for i, r in enumerate(r_vals):
        for j, g in enumerate(g_vals):
            mask = (R == r) & (G == g) & (B == b_value)
            if np.any(mask):
                Z[j, i] = I[mask][0]
            else:
                Z[j, i] = np.nan
    return Z

# Initial surface
Z = get_surface(current_b)

# Plot
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
surf = ax.plot_surface(R_grid, G_grid, Z)

ax.set_xlabel('R')
ax.set_ylabel('G')
ax.set_zlabel('Current (mA)')
ax.set_title(f'B = {current_b}')

# Slider
ax_slider = plt.axes([0.2, 0.02, 0.6, 0.03])
slider = Slider(ax_slider, 'B', 0, len(b_vals)-1, valinit=b_index, valstep=1)

def update(val):
    idx = int(slider.val)
    b_val = b_vals[idx]

    ax.clear()
    Z = get_surface(b_val)
    ax.plot_surface(R_grid, G_grid, Z)

    ax.set_xlabel('R')
    ax.set_ylabel('G')
    ax.set_zlabel('Current (mA)')
    ax.set_title(f'B = {b_val}')
    ax.set_zlim(0, 10)

    fig.canvas.draw_idle()

slider.on_changed(update)

plt.show()