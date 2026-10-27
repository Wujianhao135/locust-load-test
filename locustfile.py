"""
若依（RuoYi）管理系统性能压测脚本（Locust）
==========================================
压测场景：登录鉴权 + 核心业务接口（用户信息 / 用户列表 / 角色列表）

每个虚拟用户启动时先登录拿到 token，之后按权重访问业务接口；
对每个响应做断言（HTTP 200 且业务 code=200 才算成功），
失败会计入 Locust 的失败统计，避免"请求 200 但业务报错"被当成成功。

运行（headless，需先启动若依并关闭登录验证码）：
    python -m locust -f locustfile.py --headless --host http://localhost \
        -u 50 -r 5 -t 20s --html=reports/report_u50.html --csv=reports/u50
"""

from locust import HttpUser, between, task

# 登录账号（若依默认管理员；如遇单端登录限制，可改为多账号随机取值）
USERNAME = "admin"
PASSWORD = "admin123"


class RuoYiUser(HttpUser):
    """模拟一个登录后访问业务页面的若依用户"""

    # 每个任务之间随机等待 1~3 秒，模拟真实用户操作间隔
    wait_time = between(1, 3)

    def on_start(self):
        """虚拟用户启动：先登录，拿到 token 并加到后续请求头"""
        with self.client.post(
            "/login",
            json={"username": USERNAME, "password": PASSWORD},
            headers={"Content-Type": "application/json"},
            name="01_登录",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200 and resp.json().get("code") == 200:
                token = resp.json().get("token")
                self.client.headers.update({"Authorization": "Bearer " + token})
                resp.success()
            else:
                resp.failure("登录失败: " + resp.text[:200])

    @task(3)
    def user_list(self):
        """用户管理列表（读多写少场景中最常访问）"""
        with self.client.get(
            "/system/user/list?pageNum=1&pageSize=10",
            name="02_用户列表",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200 and resp.json().get("code") == 200:
                resp.success()
            else:
                resp.failure("用户列表异常: " + resp.text[:100])

    @task(2)
    def get_info(self):
        """获取当前登录用户信息与权限（每次进入系统都会调用）"""
        with self.client.get("/getInfo", name="03_获取用户信息", catch_response=True) as resp:
            if resp.status_code == 200 and resp.json().get("code") == 200:
                resp.success()
            else:
                resp.failure("getInfo 异常: " + resp.text[:100])

    @task(1)
    def role_list(self):
        """角色管理列表"""
        with self.client.get(
            "/system/role/list?pageNum=1&pageSize=10",
            name="04_角色列表",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200 and resp.json().get("code") == 200:
                resp.success()
            else:
                resp.failure("角色列表异常: " + resp.text[:100])
