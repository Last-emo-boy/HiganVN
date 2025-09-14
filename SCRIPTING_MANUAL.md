# HiganVN 内置脚本引擎（安全子集）手册

本手册介绍如何在 .vns 文本中嵌入一小段“安全的 Python 子集”以驱动变量与分支逻辑。
该子集在沙箱中执行，仅允许非常有限的语法和内置函数，侧重简单、可控、可回放。

适用场景：
- 复杂分支前的临时变量运算（循环、条件）
- 统计/计分汇总
- 小范围的流程控制，不涉及 I/O 与外部依赖

注意：这不是完整 Python。请勿尝试导入模块、文件 I/O、网络等操作。

---

## 一、如何在 .vns 中写脚本

支持两种写法：

1) 单行内联：
```
> SCRIPT x = (x if 'x' in vars() else 0) + 1
```

2) 多行块：在行首写 `> SCRIPT`，随后用“缩进行”作为脚本体（空行也可以）。
遇到下一条非缩进的语句/标签/命令时结束该块。
```
> SCRIPT
  total = 0
  for i in range(3):
      total += i
  if total >= 3:
      flag = True
```

执行作用域：
- 变量环境为引擎的 `vars` 字典，执行结果会回写到存档并参与回放。

---

## 二、允许的语法与内置

允许的语法元素（严格受限）：
- 赋值：`x = 1`、`x += 2`
- 表达式：数值、布尔、字符串运算；一元/二元/布尔运算；比较表达式
- 分支：`if ...:` / `elif ...:` / `else:`
- 循环：`while`、`for i in range(n):`
- 流程语句：`break`、`continue`、`pass`

禁止：
- import、with、try/except、lambda、def/class、属性访问（obj.attr）、下标（a[0]）、函数定义与调用未知对象等

允许调用的内置函数（白名单）：
- `abs`、`min`、`max`、`int`、`float`、`str`、`len`、`range`、`round`、`bool`

---

## 三、与 VNS 指令的关系

- `> SET x = expr`：适合简单表达式赋值；
- `> IF cond -> label`：单条件跳转；
- `> SCRIPT ...`：当逻辑更复杂（多语句、循环）时使用；写入的变量与 SET/IF 共享同一 `vars` 环境。

组合示例：
```
> SET score = 0
> SCRIPT
  for i in range(5):
      score += i
  if score > 6:
      bonus = True
> IF bonus == True -> get_reward
```

---

## 四、调试与回放

- 执行过程中若脚本语法或越权被拒绝，在严格模式下会抛错；在非严格模式下会忽略该错误继续运行。
- 存档包含 `vars` 字典，快速读档/槽位读档会恢复变量并通过“快速回放”重建界面状态，保证可重现。
- 综合示例可参考仓库内 `scripts/demo.vns`（含 SET/IF、SWITCH、内联与多行 SCRIPT 的组合用法）。

---

## 五、最佳实践

- 仅用来写小段逻辑；把可视演出交给 VNS 指令（EF/FADE/BG 等）。
- 变量命名简洁统一（如 favor、score、flag_x）。
- 慎用 while，保证可终止；循环步数不宜过大。
- 如需跨 label 复用逻辑，推荐配合 `> CALL label` 与 `> RETURN`。

---

## 六、常见问题

- 问：能不能用列表/字典？
  - 暂不允许下标与属性访问；如确需复杂结构，建议拆分成多个标量变量。
- 问：能不能打印/日志？
  - 暂不支持 I/O；可通过变量在 UI 层显示或导出到调试窗口（未来增强）。
- 问：如何在多脚本间共享变量？
  - `vars` 随引擎与存档存在，默认同一次运行/读档内是共享的；跨剧本文件请自行初始化。

---

## 七、文本变量插值与控制流补充

1) 文本插值
- 在对白或旁白文本中可使用 `{var}` 插值，显示时会用 `vars` 中的值替换；
- 未定义的变量占位将保留为原样（例如 `{unknown}`）。

示例：
```
> SET score = 10
: 当前分数：{score}
```

2) 条件链语法糖：ELSEIF / ELSE（配合 IF 使用）
- `> IF cond -> label`
- `> ELSEIF cond -> label`
- `> ELSE -> label`
说明：一次 IF 开始的条件链中，命中任一分支后后续 ELSEIF/ELSE 将被忽略；目标必须是已存在的 label。

3) 开关分支：SWITCH / CASE / DEFAULT / ENDSWITCH
- `> SWITCH expr`
- `> CASE value -> label`
- `> DEFAULT -> label`
- `> ENDSWITCH`
说明：从上至下匹配第一个 `CASE` 值等于 `expr` 的分支并跳转；若无匹配且存在 DEFAULT，则跳转 DEFAULT；`ENDSWITCH` 用于显式结束开关块（遇到非相关命令也会自动结束）。

4) 示例脚本
- 可直接运行 `scripts/demo.vns` 体验：包含 `SCRIPT`（内联与多行）、`{var}` 插值、`IF/ELSE`、`SWITCH/CASE/DEFAULT` 的综合用法。
