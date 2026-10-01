# Factorial Design Workbench（两水平筛选试验设计工具）

将二至八个因素的高低水平设置转换为可直接执行的两水平试验顺序，并报告哪些效应因设计而彼此混杂（别名）。仅使用 Python 标准库，**不处理任何试验读数**。

## 调用方式

```bash
python -m factorial_design design.json -o reports/
```

在 `reports/` 下生成三个文件：

- `design_matrix.csv`：标准设计矩阵，含 `point_id`、每个因素的编码列（`coded:名称`，取值 -1/+1）与实际水平列（`actual:名称`）。
- `run_plan.csv`：打乱后的执行计划，列为 `run_order, point_id, replicate, <各因素实际水平>`。
- `diagnostics.json`：定义关系、分辨度与混杂组诊断。

配置非法时程序打印 `配置错误: ...`、以非零状态码退出，且不会生成或覆盖任何报告。

## 输入格式

```json
{
  "factors": [
    {"name": "A", "low": 10, "high": 20, "role": "basic"},
    {"name": "B", "low": 0, "high": 1, "role": "basic"},
    {"name": "C", "low": 100, "high": 200, "role": "basic"},
    {"name": "D", "low": 5, "high": 8, "role": "generated",
     "generator": ["A", "B", "C"], "sign": -1}
  ],
  "replicates": 2,
  "seed": 42
}
```

规则：

- 因素数量 2–8 个；`name` 必须唯一且非空。
- `low`、`high` 必须是有限数值，且 `low < high`。
- `role` 为 `basic`（基本因素）或 `generated`（生成因素），缺省为 `basic`；基本因素至少两个。
- 生成因素的 `generator` 是不少于两个**不同基本因素**名的列表，编码列取这些基本因素编码列的逐行乘积；`sign` 取 `1` 或 `-1`（缺省 `1`）对结果整体取号。
- 拒绝未知引用、同一生成元内的重复引用，以及引用另一个生成因素。
- `replicates` 为正整数（缺省 1），`seed` 为整数（缺省 0）。

## 编码与标准矩阵

- 低水平映射为 `-1`，高水平映射为 `+1`。
- 基本因素按名称排序，枚举其全部 (-1,+1) 组合，并按编码向量的字典序编号（第 1 个点全部为 -1）。
- 生成因素由生成元乘积（可带负号）计算后映射回实际水平，**不能**作为独立枚举的变量；基本因素为 k 个时标准点数恒为 2^k。
- 没有生成因素时得到全因子设计。输入中因素的书写顺序不影响标准设计矩阵，输出因素列同样按名称排序。

## 执行计划

每个标准点执行 `replicates` 次。先生成 `(point_id, replicate)` 的完整列表（点号、重复序号均从 1 开始），再用 `seed` 对应的随机数生成器一次性打乱。同一份输入重复运行得到完全相同的顺序；重复次数只影响执行计划，不影响混杂诊断（诊断始终在未重复的标准设计上进行）。

## 诊断与混杂符号

- 在标准设计上建立截距 `(intercept)`、全部主效应和全部两因素交互作用（交互列为两个因素编码列逐行相乘）。
- 两列**完全相同或互为相反数**即归入同一混杂组；`sign_vs_representative` 为 `+1` 表示与代表列同向，`-1` 表示反向别名。负相关仍是混杂，不是“无关”。
- 代表列按“因素个数升序、名称序列升序”选出；截距排在最前；只有一个成员的效应也单独成组列出；各组按代表列排序。
- 枚举所有非空因素子集，乘积在全部设计点恒为 +1 或 -1 者即为**定义关系**（`word` 带符号，如 `-A*B*C*D`）。分辨度 `resolution` 取最短定义关系的长度；不存在定义关系（全因子）时为 `null`，且 `full_factorial` 为 `true`。
- `main_effect_confounding` 列出主效应之间的混杂对；`main_effect_vs_interaction_confounding` 列出主效应与两因素交互的混杂。

## 测试

```bash
python -m unittest discover -s tests -v
```
