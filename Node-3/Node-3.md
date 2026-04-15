# Node 3：小规模精确求解器（MILP 基线）—— 实现与数据配置说明

## 1. 概述

Node 3 的目标是：使用**混合整数线性规划（MILP）** 对极小型 **EVRP‑BSS**（带电池换电站的电动车辆路径问题）实例进行精确求解，获得全局最优路径。该结果将作为后续启发式算法（Node 4‑6）的性能基准。

本文档重点说明 **JSON 配置文件的结构与字段含义**，以及如何调整数据（客户位置、电池容量、换电站数量等）来改变问题难度或调试模型。

---

## 2. JSON 配置文件详解

数据文件应放在 `data/small_instance.json`。以下是一个完整示例：

```json
{
  "depot": {
    "id": 0,
    "x": 0,
    "y": 0
  },
  "customers": [
    { "id": 1, "x": 5, "y": 0, "demand_kg": 100 },
    { "id": 2, "x": 8, "y": 4, "demand_kg": 150 },
    { "id": 3, "x": 2, "y": 7, "demand_kg": 80 }
  ],
  "swap_stations": [
    { "id": 4, "x": 6, "y": 3 },
    { "id": 5, "x": 3, "y": 4 }
  ],
  "vehicle": {
    "battery_capacity_kwh": 40,
    "initial_soc_kwh": 40,
    "energy_per_km": 0.3
  }
}