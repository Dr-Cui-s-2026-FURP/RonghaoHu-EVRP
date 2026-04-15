# src/energy_model_quadratic.py
import numpy as np
import matplotlib.pyplot as plt

# ==================== 能耗计算函数 ====================
'''
alpha 默认值为 0.03
beta  默认值为 0.15
gamma 默认值为 0.20
——在energy_per_km(计算函数中修改)
vehicle_mass_ton 默认值为1.5(t)
在 energy_consumed中修改
'''

def energy_per_km(cargo_ton, vehicle_mass_ton, alpha=0.03, beta=0.15, gamma=0.20):
    """
    计算每公里能耗 (kWh/km)
    """
    m = vehicle_mass_ton + cargo_ton
    g = alpha * m**2 + beta * m + gamma
    return g

def energy_consumed(distance_km, cargo_ton,vehicle_mass_ton=1.5):
    """计算行驶 distance_km 消耗的总能量 (kWh)"""
    e_per_km = energy_per_km(cargo_ton, vehicle_mass_ton) # cargo_ton :(载重), vehicle_mass_ton :(车原重)
    return distance_km * e_per_km

# ==================== 绘图函数 ====================
# 绘图函数为AI编写，仅供演示
def plot_energy_curves(max_distance=200, cargo_list_ton=[0, 0.2, 0.4, 0.6, 0.8]):
    """
    绘制不同载重下的能耗-距离曲线
    max_distance: 最大距离 (km)
    cargo_list_ton: 载重列表 (吨)
    """
    distances = np.linspace(0, max_distance, 100)   # 100个距离点
    plt.figure(figsize=(10, 6))
    
    for cargo in cargo_list_ton:
        energies = [energy_consumed(d, cargo) for d in distances]
        label = f"Cargo = {cargo*1000:.0f} kg" if cargo > 0 else "Empty (0 kg)"
        plt.plot(distances, energies, label=label, linewidth=2)
    
    plt.xlabel("Distance (km)", fontsize=12)
    plt.ylabel("Energy Consumed (kWh)", fontsize=12)
    plt.title("Battery Depletion with Quadratic Mass Effect", fontsize=14)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    # 保存图片到 assets 文件夹（如果文件夹不存在，先创建）
    import os
    os.makedirs("assets", exist_ok=True)
    plt.savefig("assets/energy_curves_quadratic.png", dpi=150)
    plt.show()

# ==================== 主程序（直接运行） ====================
if __name__ == "__main__":
    plot_energy_curves()