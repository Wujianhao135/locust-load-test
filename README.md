# 性能压测项目 · Locust Load Testing

> 基于 **Locust** 对 [若依 RuoYi](https://gitee.com/y_project/RuoYi-Vue) 后台管理系统进行性能压测，
> 模拟真实用户「登录 → 访问核心业务」，通过 **10 / 50 / 100 三个并发梯度** 量化系统的响应时间、吞吐量与错误率，
> 定位性能瓶颈并给出优化建议。

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Locust](https://img.shields.io/badge/Locust-2.46-green)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 一、压测场景

每个虚拟用户（`RuoYiUser`）：

1. **启动时登录**（`on_start`）：校验 HTTP 200 且业务 `code=200`，拿到 `token` 后注入后续请求头。
2. 登录后按权重访问核心读接口：

| 权重 | 任务 | 接口 |
|---|---|---|
| 3 | 用户列表 | `GET /system/user/list` |
| 2 | 获取用户信息 | `GET /getInfo` |
| 1 | 角色列表 | `GET /system/role/list` |

任务间隔随机 **1~3 秒**，模拟真实用户操作节奏。

### 业务断言（关键）

所有请求都使用 `catch_response` 做**业务级断言**：不仅要求 HTTP 状态码 200，还要求响应体 `code=200`。
这样可以避免「HTTP 200 但业务报错（如未登录、无权限）」被错误地计为成功。

---

## 二、快速开始

### 1. 准备被测系统

- 启动若依 RuoYi（后端 + 前端 + MySQL + Redis），并**关闭登录验证码**。
- 本项目压测直连后端（默认 `http://localhost:8080`），不经过前端 dev server。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行压测

**方式一：一键跑三个梯度（Windows PowerShell）**

```powershell
# 如脚本里的 Python 路径不同，请先修改 run_loadtest.ps1 中的 $py
.\run_loadtest.ps1
```

**方式二：手动指定参数**

```bash
# Web UI
locust -f locustfile.py --host http://localhost:8080

# Headless（无界面）
python -m locust -f locustfile.py --headless --host http://localhost:8080 \
    -u 50 -r 5 -t 20s \
    --html reports/report_u50.html --csv reports/u50
```

参数说明：`-u` 总用户数、`-r` 每秒启动用户数、`-t` 持续时间。

> 注：`locustfile.py` 默认使用若依官方默认账号 `admin/admin123`，仅用于本地测试。
> 若遇单端登录互踢限制，可改为多账号随机取值。

---

## 三、压测结果（真实运行数据）

### 三个并发梯度（聚合）

| 并发用户 | 总请求数 | 失败数 | 错误率 | 中位数 | 平均 | P95 | 最大 | 吞吐量 RPS |
|---|---|---|---|---|---|---|---|---|
| 10  | 75  | 0 | 0% | 21ms | 43ms  | 190ms | 315ms | 5.08 |
| 50  | 323 | 0 | 0% | 21ms | 59ms  | 270ms | 438ms | 22.23 |
| 100 | 661 | 0 | 0% | 15ms | 106ms | 600ms | 836ms | 42.98 |

### 100 并发下各接口明细

| 接口 | 请求数 | 中位数 | 平均 | P95 | 最大 |
|---|---|---|---|---|---|
| POST 登录 | 100 | 530ms | 566ms | 750ms | 836ms |
| GET 用户列表 | 277 | 17ms | 31ms | 100ms | 186ms |
| GET 获取用户信息 | 188 | 5ms | 13ms | 54ms | 145ms |
| GET 角色列表 | 96 | 17ms | 31ms | 96ms | 174ms |

---

## 四、瓶颈分析

1. **登录接口是主要瓶颈**：P95 随并发 310ms → 410ms → 750ms。
   登录需执行 BCrypt 密码哈希校验（CPU 密集）、查询用户/权限、生成 Token，开销显著高于纯查询接口。
2. **读接口性能良好**：用户列表、getInfo、角色列表在 100 并发下 P95 仍 ≤100ms，中位数仅 5~17ms。
3. **稳定性良好**：100 并发全程 0 错误，未出现拒绝连接或 5xx。
4. 整体 P95 在 100 并发时抬升明显，主要被登录接口拉高。

> 口径说明：本次压测任务间隔 1~3 秒、持续 20 秒，RPS 受等待时间限制，
> 测得的是「带用户操作间隔下的响应时间」，并非系统极限吞吐。

---

## 五、优化建议

| 方向 | 措施 |
|---|---|
| 登录接口 | 评估 BCrypt 强度（默认 strength=10，CPU 开销大）；登录加验证码/限流防暴力破解；失败次数缓存 |
| 列表查询 | 热点列表加 Redis 缓存；确认分页字段索引；MyBatis 二级缓存按需开启 |
| 应用层 | Tomcat 工作线程池按并发调优；开启慢接口监控 |
| 数据库 | Druid/HikariCP 连接池大小与并发匹配；开启慢 SQL 监控 |
| 压测补充 | 增加无等待峰值 RPS 测试、阶梯加压确定性能拐点和最大稳定并发数 |

---

## 六、项目结构

```
locust/
├── locustfile.py          # 压测脚本：登录 + 3 个业务接口 + 业务断言
├── run_loadtest.ps1       # 一键跑 10/50/100 三梯度（输出 HTML + CSV）
├── requirements.txt
├── reports/
│   ├── 性能压测报告.md
│   ├── report_u10.html / report_u50.html / report_u100.html
│   └── u10/u50/u100_stats.csv、_stats_history.csv、_failures.csv
└── README.md
```

---

## 七、技术栈

| 类别 | 技术 |
|---|---|
| 压测工具 | Locust 2.46 |
| 语言 | Python 3.10 |
| 被测系统 | 若依 RuoYi-Vue（Spring Boot + Vue + MySQL + Redis） |

## License

[MIT](LICENSE)
