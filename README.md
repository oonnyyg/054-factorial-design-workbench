# 两水平筛选试验设计工具 (factorial-design-workbench)

把二至八个因素的水平设置转换为可执行的随机试验顺序，并自动报告效应混杂
（别名）情况。仅使用 Python 标准库，不处理任何试验读数。

## 调用方式

```bash
python -m factorial_design CONFIG.json -o OUTPUT_DIR
python -m factorial_design --output-dir OUTPUT_DIR CONFIG.json
```

在输出目录生成三个文件：

- `design_matrix.csv`：标准（未重复）设计矩阵，包含每个因素的编码列
  （`<因素>.code`，取值 -1 / +1）和实际水平列（`<因素>.level`）。
- `execution_plan.csv`：打乱后的执行计划，列为 `order`（执行序号）、
  `point`（标准点编号）、`replicate`（重复序号）和各因素实际水平。
- `diagnostics.json`：定义关系、分辨度与混杂组诊断。

配置非法时错误定位打印到标准错误，进程以非零状态码退出，且不会写入或
覆盖任何报告文件。

## 输入格式

顶层 JSON 对象：

- `factors`（必填）：2 至 8 个因素，名称唯一且非空。
  - `name`：因素名称。
  - `low` / `high`：有限数值，且 `low < high`。
  - `kind`：`"basic"`（默认，基本因素）或 `"generated"`（生成因素）。
  - 生成因素必须提供 `generator`：
    - `factors`：不少于两个不同因素名的列表，只能引用**基本因素**；
      禁止未知引用、重复引用以及引用另一个生成因素。
    - `sign`：生成列相对乘积的符号，可取 `1` / `-1` 或 `"+"` / `"-"`，
      默认 `1`。即编码列 `D = sign * product(引用列)`。
- `replicates`：正整数，每个标准点的重复次数，默认 1。
- `seed`：整数随机种子，默认 0。

示例见 `examples/`：

```bash
python -m factorial_design examples/full_factorial.json -o build/full
python -m factorial_design examples/half_fraction.json -o build/half
```

## 设计构造与编码

- 基本因素按名称排序，枚举其全部 (-1, +1) 组合；按编码向量字典序从 1
  开始编号（第一个因素变化最慢）。基本因素至少两个。
- 生成因素不是独立枚举变量，而是由所引用基本因素编码列逐点相乘再乘符号
  得到。没有生成因素时即为 2^k 全因子设计。
- 编码 -1 映射到 `low`，+1 映射到 `high`。输入中因素的书写顺序不影响
  标准设计矩阵，输出列一律按因素名排序。
- 执行列表先按“标准点编号、重复序号”形成，再用给定种子调用 Python
  `random.Random(seed).shuffle` 打乱；相同输入永远得到相同顺序。重复次数
  只增加运行数，不影响混杂诊断。

## 混杂诊断如何解读

在未重复的标准设计上建立截距 `I`（恒为 +1）、所有主效应（因素编码列）
和所有两因素交互作用（两个因素列逐行相乘，记作 `A*B`）的编码列。

- `alias_groups`：完全相同或互为相反数的列归入同一混杂组，说明这些效应
  **无法分别识别**。每个成员给出 `sign`：`+1` 表示与代表列相同，`-1`
  表示与代表列相反（负相关仍然是混杂，不是无关）。代表按“因素个数、
  名称序列”选出，截距组排最前；只有一个成员的效应也单独成组列出，
  各组按代表排序。
- `defining_relations`：枚举全部非空因素子集，其乘积列在所有设计点恒为
  +1 或 -1 时即为定义关系（如 `{word: "A*B*C*D", sign: -1}` 表示
  `I = -ABCD`）。
- `resolution`：分辨度，取定义关系中最短的因素个数；不存在任何定义关系
  时为 `null`，且 `full_factorial` 为 `true`。
- `confounding.main_main` 与 `confounding.main_interaction` 分别列出主效应
  之间、主效应与两因素交互之间的混杂及符号。

## 测试

```bash
python -m unittest discover -s tests -v
```
