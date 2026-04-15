# src/exact_solver.py
import pulp
import json
import math

def distance(coord1, coord2):
    """欧氏距离"""
    return math.hypot(coord1['x'] - coord2['x'], coord1['y'] - coord2['y'])

def solve_evrp_bss_exact(instance_path):
    # 读取数据
    with open(instance_path, 'r') as f:
        data = json.load(f)
    
    depot = data['depot']
    customers = data['customers']
    stations = data['swap_stations']
    B = data['vehicle']['battery_capacity_kwh']
    e_per_km = data['vehicle']['energy_per_km']
    
    # 所有节点：车库 + 客户 + 换电站
    nodes = [depot] + customers + stations
    node_ids = [n['id'] for n in nodes]
    cust_ids = [c['id'] for c in customers]
    station_ids = [s['id'] for s in stations]
    
    # 距离矩阵
    dist = {}
    for i in nodes:
        for j in nodes:
            if i['id'] != j['id']:
                dist[(i['id'], j['id'])] = distance(i, j)
    
    # ---------- 定义 PuLP 问题 ----------
    model = pulp.LpProblem("EVRP_BSS_Exact", pulp.LpMinimize)
    
    # 决策变量：x[i][j] 是否从 i 到 j (二进制)
    x = pulp.LpVariable.dicts("x", (node_ids, node_ids), cat='Binary')
    
    # 决策变量：剩余电量到达节点 i 时（kWh）
    u = pulp.LpVariable.dicts("u", node_ids, lowBound=0, upBound=B, cat='Continuous')
    
    # 辅助变量：消除子回路 (Miller–Tucker–Zemlin 方式)
    # 但 MTZ 对 VRP 需要额外的顺序变量，这里改用简单方式：流守恒 + 电量约束已能消除大多数回路
    # 更严谨的方法是用 MTZ，但对于小规模实例，我们增加一个顺序变量 t (可选)
    # 为了简洁，先不加入 MTZ，因为电量约束 + 流守恒通常能避免子回路（如果所有距离 >0）
    # 但稳妥起见，我们加入一个简单的顺序变量 t，强制从 depot 开始递增
    t = pulp.LpVariable.dicts("t", node_ids, lowBound=0, upBound=len(node_ids), cat='Integer')
    
    # ---------- 目标函数：最小化总距离 ----------
    model += pulp.lpSum(dist[i_id, j_id] * x[i_id][j_id] 
                        for i_id in node_ids for j_id in node_ids if i_id != j_id)
    
    # ---------- 约束 ----------
    # 1. 每个客户被访问恰好一次
    for c in cust_ids:
        model += pulp.lpSum(x[i][c] for i in node_ids if i != c) == 1
        model += pulp.lpSum(x[c][j] for j in node_ids if j != c) == 1
    
    # 2. 车库：出发一次，返回一次
    depot_id = depot['id']
    model += pulp.lpSum(x[depot_id][j] for j in node_ids if j != depot_id) == 1
    model += pulp.lpSum(x[i][depot_id] for i in node_ids if i != depot_id) == 1
    
    # 3. 换电站：可以被访问零次或多次（这里简单起见，允许最多访问一次）
    for s in station_ids:
        # 进入和离开平衡（如果进入则必须离开）
        model += pulp.lpSum(x[i][s] for i in node_ids if i != s) == pulp.lpSum(x[s][j] for j in node_ids if j != s)
        # 限制每个换电站最多访问一次（可选）
        model += pulp.lpSum(x[i][s] for i in node_ids if i != s) <= 1
    
    # 4. 电量约束（核心）
    # 对于每条弧 (i, j)，如果选择，则到达 j 的电量 <= 到达 i 的电量 - 能耗
    M = B  # 一个大数，设为电池容量即可
    for i in node_ids:
        for j in node_ids:
            if i != j:
                model += u[j] <= u[i] - e_per_km * dist[(i, j)] + M * (1 - x[i][j])
                model += u[j] >= u[i] - e_per_km * dist[(i, j)] - M * (1 - x[i][j])
    
    # 5. 起始点电量等于满电
    model += u[depot_id] == B
    
    # 6. 换电站：到达换电站后，电量可以重置为满电（相当于换电）
    # 方法：如果车辆从 i 到 s，那么 u[s] 可以重新赋值，但上面的约束已经限制了 u[s] <= u[i] - energy
    # 为了让换电站起到“充电”作用，我们需要允许 u[s] 被设为 B。可以通过添加松弛变量，或者简单让 u[s] 可以取任意值，
    # 但更精确的做法：为换电站单独处理，加上约束：如果 x[i][s]=1，则 u[s] <= B 且 u[s] >= B - (1 - x[i][s])*M ？不对。
    # 标准方法：将换电站复制成两个节点（到达和离开），但会复杂。简化：我们允许车辆在换电站“免费”把电量加到 B，
    # 所以我们需要修改电量约束：对于从 s 出发的弧，u[s] 可以重新赋值为 B，而不受之前电量限制。
    # 这里采用更简单的技巧：对于换电站 s，我们不限制 u[s] 的上限（除了电池容量 B），并且允许从 i 到 s 时，能耗扣减后可以低于 0，
    # 然后强制 u[s] 被设为 B。但我们直接加约束：如果 x[i][s]=1，则 u[s] = B（这会导致线性不可分）。
    # 因此，对于换电站，我们单独加约束：对于任何进入换电站的弧，到达后的电量强制等于 B。
    # 使用大M法：
    for s in station_ids:
        # 到达 s 时电量等于 B（如果 s 被访问）
        # 即 u[s] >= B - M * (1 - sum_in) 且 u[s] <= B + M * (1 - sum_in)
        sum_in = pulp.lpSum(x[i][s] for i in node_ids if i != s)
        model += u[s] >= B - M * (1 - sum_in)
        model += u[s] <= B + M * (1 - sum_in)  # 由于 u[s] <= B，实际上这个约束强制 u[s]=B 如果 sum_in>=1
        # 但上面可能有问题，更稳妥：
        # 实际上 u[s] <= B 已经存在，所以只需要下界约束：
        # model += u[s] >= B - M * (1 - sum_in)
        # 修改为：
    # 重新实现换电站约束：
    for s in station_ids:
        sum_in = pulp.lpSum(x[i][s] for i in node_ids if i != s)
        # 如果 sum_in >= 1，则 u[s] = B
        model += u[s] >= B - M * (1 - sum_in)
        model += u[s] <= B + M * (1 - sum_in)  # 结合 u[s]<=B 得到 u[s]=B
    
    # 7. 避免子回路：MTZ 约束
    # 对于所有 i != depot, j != depot
    N = len(node_ids)
    for i in node_ids:
        if i == depot_id: continue
        for j in node_ids:
            if j == depot_id or i == j: continue
            model += t[i] - t[j] + 1 <= (N-1) * (1 - x[i][j])
    for i in node_ids:
        if i != depot_id:
            model += t[i] >= 1
            model += t[i] <= N-1
    
    # ---------- 求解 ----------
    solver = pulp.PULP_CBC_CMD(msg=True)
    model.solve(solver)
    
    # ---------- 输出结果 ----------
    status = pulp.LpStatus[model.status]
    total_dist = pulp.value(model.objective)
    print(f"求解状态: {status}")
    if status == 'Optimal':
        print(f"最优总距离: {total_dist:.2f} km")
        
        # 提取路径
        route = [depot_id]
        current = depot_id
        while True:
            next_node = None
            for j in node_ids:
                if j != current and pulp.value(x[current][j]) > 0.5:
                    next_node = j
                    break
            if next_node is None or next_node == depot_id:
                break
            route.append(next_node)
            current = next_node
        route.append(depot_id)
        print("路径顺序:", " -> ".join(str(node) for node in route))
        
        # 打印各节点电量
        print("\n到达各节点时的剩余电量 (kWh):")
        for node in node_ids:
            val = pulp.value(u[node])
            print(f"  节点 {node}: {val:.2f}" if val else f"  节点 {node}: 未访问")
    else:
        print("未找到最优解，请检查约束或实例可行性")
    
    return model

if __name__ == "__main__":
    solve_evrp_bss_exact("data/small_instance.json")