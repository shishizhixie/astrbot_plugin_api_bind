import re
import copy
import json
import hashlib
import logging
import time

from astrbot.api import AstrBotConfig
from astrbot.api.event import filter as event_filter, AstrMessageEvent
from astrbot.api.message_components import Plain
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import ProviderType

logger = logging.getLogger("astrbot")

# 会话超时时间（秒）
SESSION_TIMEOUT = 1800  # 30分钟

PRESET_BASES = [
    ("DeepSeek", "https://api.deepseek.com/v1"),
    ("智谱GLM", "https://open.bigmodel.cn/api/paas/v4"),
    ("硅基流动", "https://api.siliconflow.cn/v1"),
    ("阿里百炼", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    ("OpenAI", "https://api.openai.com/v1"),
    ("月之暗面", "https://api.moonshot.cn/v1"),
    ("零一万物", "https://api.lingyiwanwu.com/v1"),
    ("Groq", "https://api.groq.com/openai/v1"),
    ("Together AI", "https://api.together.xyz/v1"),
]


@register("astrbot_plugin_api_bind", "Mon3tr", "史诗之API注册器 - 用户可注册切换自己的API", "1.0")
class ApiBindPlugin(Star):

    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config or {}
        custom_bases = self.config.get("preset_bases", [])
        self.preset_bases = list(PRESET_BASES)
        for item in custom_bases:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                if item[0] not in [p[0] for p in self.preset_bases]:
                    self.preset_bases.append((item[0], item[1]))
        self._sessions = {}

    def _uid(self, event):
        """用用户ID代替session_id，私聊切换群聊也能用"""
        return str(event.get_sender_id())

    def _sid(self, event):
        return str(event.session_id)

    def _is_private(self, event):
        return event.is_private_chat()

    def _hash_pwd(self, pwd):
        return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

    def _mask_key(self, key):
        if len(key) <= 8:
            return "***"
        return key[:4] + "..." + key[-4:]

    # ---- 持久化 ----
    async def _get_accounts(self):
        data = await self.get_kv_data("api_accounts", {})
        return data if isinstance(data, dict) else {}

    async def _save_accounts(self, accounts):
        await self.put_kv_data("api_accounts", accounts)

    async def _get_bind(self, event):
        return await self.get_kv_data(f"user_bind_{self._sid(event)}", None)

    async def _save_bind(self, event, info):
        if info is None:
            await self.delete_kv_data(f"user_bind_{self._sid(event)}")
        else:
            await self.put_kv_data(f"user_bind_{self._sid(event)}", info)

    # ---- 会话状态机（带超时清理） ----
    def _set_step(self, event, step, data=None):
        sid = self._sid(event)
        self._sessions[sid] = {"step": step, "data": data or {}, "ts": time.time()}

    def _get_step(self, event):
        self._clean_expired()
        return self._sessions.get(self._sid(event))

    def _clear_step(self, event):
        self._sessions.pop(self._sid(event), None)

    def _clean_expired(self):
        now = time.time()
        expired = [sid for sid, s in self._sessions.items()
                   if now - s.get("ts", 0) > SESSION_TIMEOUT]
        for sid in expired:
            self._sessions.pop(sid, None)

    # ==================== 注册API流程 ====================
    @event_filter.command("注册API")
    async def cmd_register(self, event: AstrMessageEvent):
        if not self._is_private(event):
            yield event.plain_result("❌ 请在私聊中使用此命令。")
            return
        self._set_step(event, "reg_username")
        yield event.plain_result(
                "🔌 自定义API注册\n\n"
                "可用功能：\n"
                "  ① 注册API - 绑定你的API账号\n"
                "  ② 切换自定义API - 切换到已注册账号\n"
                "  ③ 切换API模型 - 切换当前账号的模型\n"
                "  ④ 添加模型 - 为当前账号添加模型\n"
                "  ⑤ 测试API - 测试当前绑定的API连接\n"
                "  ⑥ 注销API - 注销账号\n"
                "  ⑦ 恢复默认API - 切回系统默认\n"
                "  ⑧ API状态 - 查看当前绑定\n\n"
                "请输入账号名（发送「取消」可随时退出）："
            )

    async def _handle_register(self, event, text):
        step = self._get_step(event)
        if not step:
            return None
        s = step["step"]
        d = step["data"]

        if s == "reg_username":
            name = text.strip()
            if len(name) < 2:
                return "账号名至少2个字符，请重新输入："
            accts = await self._get_accounts()
            if name in accts:
                self._clear_step(event)
                return f"❌ 账号「{name}」已存在。"
            d["name"] = name
            self._set_step(event, "reg_password", d)
            return "请输入密码："

        if s == "reg_password":
            pwd = text.strip()
            if len(pwd) < 4:
                return "密码至少4个字符，请重新输入："
            d["pwd_hash"] = self._hash_pwd(pwd)
            self._set_step(event, "reg_apikey", d)
            return "请输入API Key："

        if s == "reg_apikey":
            key = text.strip()
            if not key:
                return "API Key不能为空，请重新输入："
            d["api_key"] = key
            self._set_step(event, "reg_apibase", d)
            opts = "请选择API源：\n"
            items = self.preset_bases
            for i, (name, url) in enumerate(items, 1):
                opts += f"  {i}. {name}\n"
            opts += f"  {len(items)+1}. 自定义（输入完整URL）\n\n请输入编号或直接输入URL："
            return opts

        if s == "reg_apibase" or s == "reg_apibase_custom":
            choice = text.strip()
            items = self.preset_bases

            if s == "reg_apibase_custom":
                if not choice.startswith("http"):
                    return "URL格式不正确，请输入以http开头的完整URL："
                d["api_base"] = choice
                d["base_name"] = "自定义"
                self._set_step(event, "reg_models", d)
                return f"✅ 已设置：{choice}\n\n请输入可用模型（逗号分隔）：\n例：deepseek-v4-flash,deepseek-v4-pro"

            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(items):
                    name, url = items[idx - 1]
                    d["api_base"] = url
                    d["base_name"] = name
                    self._set_step(event, "reg_models", d)
                    return f"✅ 已选择：{name}（{url}）\n\n请输入可用模型（逗号分隔）：\n例：deepseek-v4-flash,deepseek-v4-pro"
                elif idx == len(items) + 1:
                    self._set_step(event, "reg_apibase_custom", d)
                    return "请输入完整的API Base URL："
            elif choice.startswith("http"):
                d["api_base"] = choice
                d["base_name"] = "自定义"
                self._set_step(event, "reg_models", d)
                return f"✅ 已设置：{choice}\n\n请输入可用模型（逗号分隔）："
            return "请输入编号或完整URL："

        if s == "reg_models":
            models = [m.strip() for m in text.split(",") if m.strip()]
            if not models:
                return "请至少输入一个模型："
            d["models"] = models
            accts = await self._get_accounts()
            accts[d["name"]] = {
                "pwd_hash": d["pwd_hash"],
                "api_key": d["api_key"],
                "api_base": d["api_base"],
                "base_name": d.get("base_name", "自定义"),
                "models": models,
            }
            await self._save_accounts(accts)
            self._clear_step(event)
            ml = "\n  ".join(models)
            return (
                f"✅ 注册成功！\n\n"
                f"账号：{d['name']}\n"
                f"API源：{d.get('base_name', '自定义')}\n"
                f"模型：\n  {ml}\n\n"
                "发送「切换自定义API」开始使用"
            )

        return None

    # ==================== 切换API流程 ====================
    @event_filter.command("切换自定义API")
    async def cmd_switch(self, event: AstrMessageEvent):
        if not self._is_private(event):
            yield event.plain_result("❌ 请在私聊中使用此命令。")
            return
        self._set_step(event, "sw_username")
        yield event.plain_result("🔌 切换自定义API\n\n请输入账号（发送「取消」可随时退出）：")

    async def _handle_switch(self, event, text):
        step = self._get_step(event)
        if not step:
            return None
        s = step["step"]
        d = step["data"]

        if s == "sw_username":
            name = text.strip()
            accts = await self._get_accounts()
            if name not in accts:
                self._clear_step(event)
                return f"❌ 账号「{name}」不存在。"
            d["name"] = name
            self._set_step(event, "sw_password", d)
            return "请输入密码："

        if s == "sw_password":
            pwd = text.strip()
            accts = await self._get_accounts()
            a = accts[d["name"]]
            if self._hash_pwd(pwd) != a["pwd_hash"]:
                self._clear_step(event)
                return "❌ 密码错误。"
            d["account"] = a
            models = a.get("models", [])
            if not models:
                self._clear_step(event)
                return "❌ 该账号无可用模型。"
            ml = "\n".join(f"  {i+1}. {m}" for i, m in enumerate(models))
            bn = a.get("base_name", "自定义")
            self._set_step(event, "sw_model", d)
            return f"✅ 密码正确！API源：{bn}\n\n请选择模型：\n{ml}\n\n请输入编号："

        if s == "sw_model":
            if not text.isdigit():
                return "请输入数字编号："
            idx = int(text) - 1
            models = d["account"].get("models", [])
            if idx < 0 or idx >= len(models):
                return f"编号无效，请输入1-{len(models)}："
            model = models[idx]
            a = d["account"]
            await self._save_bind(event, {
                "name": d["name"],
                "api_key": a["api_key"],
                "api_base": a["api_base"],
                "base_name": a.get("base_name", "自定义"),
                "model": model,
            })
            self._clear_step(event)
            return (
                f"✅ 已切换到自定义API！\n\n"
                f"账号：{d['name']}\n"
                f"API源：{a.get('base_name', '自定义')}\n"
                f"模型：{model}\n\n"
                "发送「API状态」查看详情\n"
                "发送「恢复默认API」切回系统默认"
            )

        return None

    # ==================== 注销API流程 ====================
    # ==================== 测试API连接 ====================
    @event_filter.command("测试API")
    async def cmd_test_api(self, event: AstrMessageEvent):
        if not self._is_private(event):
            yield event.plain_result("❌ 请在私聊中使用此命令。")
            return
        bind = await self._get_bind(event)
        if not bind:
            yield event.plain_result("❌ 你还没有切换到自定义API，先发送「切换自定义API」吧。")
            return
        
        yield event.plain_result("⏳ 正在测试API连接，请稍候...")
        
        api_key = bind.get("api_key", "")
        api_base = bind.get("api_base", "").rstrip("/")
        model = bind.get("model", "")
        
        if not api_key or not api_base or not model:
            yield event.plain_result("❌ 绑定信息不完整，请重新注册。")
            return
        
        try:
            import httpx
            import time
            url = f"{api_base}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
                "stream": False
            }
            async with httpx.AsyncClient(timeout=30) as client:
                t1 = time.time()
                resp = await client.post(url, json=payload, headers=headers)
                t2 = time.time()
                elapsed = round(t2 - t1, 2)
                if resp.status_code == 200:
                    data = resp.json()
                    yield event.plain_result(
                        f"✅ API连接成功！\n\n"
                        f"API源：{bind.get('base_name','?')}\n"
                        f"模型：{model}\n"
                        f"响应：{data['choices'][0]['message']['content'][:50]}\n"
                        f"耗时：{elapsed}秒"
                    )
                elif resp.status_code == 401:
                    yield event.plain_result(f"❌ API Key无效（401），请检查Key是否正确。")
                elif resp.status_code == 404:
                    yield event.plain_result(f"❌ 模型「{model}」不存在（404），请检查模型名。")
                elif resp.status_code == 429:
                    yield event.plain_result(f"❌ 请求过于频繁（429），请稍后再试。")
                elif resp.status_code == 503:
                    yield event.plain_result(f"❌ API服务暂时不可用（503），可能是限流或维护中。")
                else:
                    body = await resp.aread()
                    yield event.plain_result(f"❌ API返回错误（{resp.status_code}）：{body.decode()[:200]}")
        except httpx.ConnectError:
            yield event.plain_result(f"❌ 无法连接到 {api_base}，请检查API地址是否正确。")
        except httpx.TimeoutException:
            yield event.plain_result(f"❌ 连接超时（30秒），API可能响应过慢。")
        except Exception as e:
            yield event.plain_result(f"❌ 测试失败：{str(e)[:100]}")

    @event_filter.command("注销API")
    async def cmd_unregister(self, event: AstrMessageEvent):
        if not self._is_private(event):
            yield event.plain_result("❌ 请在私聊中使用此命令。")
            return
        self._set_step(event, "un_name")
        yield event.plain_result("🔌 注销API账号\n\n请输入要注销的账号名（发送「取消」可随时退出）：")

    async def _handle_unregister(self, event, text):
        step = self._get_step(event)
        if not step:
            return None
        s = step["step"]
        d = step["data"]

        if s == "un_name":
            name = text.strip()
            accts = await self._get_accounts()
            if name not in accts:
                self._clear_step(event)
                return f"❌ 账号「{name}」不存在。"
            d["name"] = name
            self._set_step(event, "un_pwd", d)
            return "请输入密码确认："

        if s == "un_pwd":
            pwd = text.strip()
            accts = await self._get_accounts()
            if self._hash_pwd(pwd) != accts[d["name"]]["pwd_hash"]:
                self._clear_step(event)
                return "❌ 密码错误。"
            self._set_step(event, "un_confirm", d)
            return "⚠️ 确认注销？所有数据不可恢复。\n\n输入「确认注销」继续，其他取消："

        if s == "un_confirm":
            if text.strip() != "确认注销":
                self._clear_step(event)
                return "❌ 已取消。"
            accts = await self._get_accounts()
            del accts[d["name"]]
            await self._save_accounts(accts)
            bind = await self._get_bind(event)
            if bind and bind.get("name") == d["name"]:
                await self._save_bind(event, None)
            self._clear_step(event)
            return f"✅ 账号「{d['name']}」已注销。"

        return None

    # ==================== 恢复默认 & 状态 ====================
    @event_filter.command("恢复默认API")
    async def cmd_restore(self, event: AstrMessageEvent):
        await self._save_bind(event, None)
        self._clear_step(event)
        yield event.plain_result("✅ 已恢复为系统默认API。")
    # ==================== 切换模型（不重新输密码） ====================
    @event_filter.command("切换API模型")
    async def cmd_switch_model(self, event: AstrMessageEvent):
        if not self._is_private(event):
            yield event.plain_result("❌ 请在私聊中使用此命令。")
            return
        bind = await self._get_bind(event)
        if not bind:
            yield event.plain_result("❌ 你还没有切换到自定义API，先发送「切换自定义API」吧。")
            return
        name = bind.get("name", "")
        accts = await self._get_accounts()
        if name not in accts:
            yield event.plain_result(f"❌ 账号「{name}」不存在，请重新注册。")
            return
        models = accts[name].get("models", [])
        if not models:
            yield event.plain_result("❌ 该账号没有可用模型，请先「添加模型」。")
            return
        self._set_step(event, "cm_switch_model", {"name": name, "models": models})
        ml = "\n".join(f"  {i+1}. {m}" for i, m in enumerate(models))
        yield event.plain_result(
            f"🔄 切换模型 - 账号：{name}\n\n"
            f"可用模型：\n{ml}\n\n"
            "请输入编号："
        )

    async def _handle_cm_switch_model(self, event, text, step):
        d = step["data"]
        models = d["models"]
        if not text.isdigit():
            return "请输入数字编号："
        idx = int(text) - 1
        if idx < 0 or idx >= len(models):
            return f"编号无效，请输入1-{len(models)}："
        model = models[idx]
        bind = await self._get_bind(event)
        if not bind:
            self._clear_step(event)
            return "❌ 绑定已失效，请重新切换。"
        bind["model"] = model
        await self._save_bind(event, bind)
        self._clear_step(event)
        return f"✅ 已切换模型为：{model}"

    # ==================== 添加模型到已有账号 ====================
    @event_filter.command("添加模型")
    async def cmd_add_model(self, event: AstrMessageEvent):
        if not self._is_private(event):
            yield event.plain_result("❌ 请在私聊中使用此命令。")
            return
        bind = await self._get_bind(event)
        if not bind:
            yield event.plain_result("❌ 你还没有切换到自定义API，先发送「切换自定义API」吧。")
            return
        name = bind.get("name", "")
        accts = await self._get_accounts()
        if name not in accts:
            yield event.plain_result(f"❌ 账号「{name}」不存在。")
            return
        self._set_step(event, "cm_add_model", {"name": name})
        yield event.plain_result(
            f"📝 为账号「{name}」添加模型\n\n"
            "请输入模型名（多个用逗号分隔）：\n"
            "例：deepseek-v4-flash,deepseek-v4-pro"
        )

    async def _handle_cm_add_model(self, event, text, step):
        d = step["data"]
        name = d["name"]
        new_models = [m.strip() for m in text.split(",") if m.strip()]
        if not new_models:
            return "请至少输入一个模型："
        accts = await self._get_accounts()
        if name not in accts:
            self._clear_step(event)
            return f"❌ 账号「{name}」已不存在。"
        existing = accts[name].get("models", [])
        added = []
        for m in new_models:
            if m not in existing:
                existing.append(m)
                added.append(m)
        accts[name]["models"] = existing
        await self._save_accounts(accts)
        # 如果当前正绑定这个账号，也更新bind的model
        bind = await self._get_bind(event)
        if bind and bind.get("name") == name and not added:
            pass  # 没加新模型
        self._clear_step(event)
        if added:
            return f"✅ 已添加模型：\n  " + "\n  ".join(added) + "\n\n发送「切换API模型」选择使用"
        else:
            return "ℹ️ 这些模型已存在，无需重复添加。"



    @event_filter.command("API状态")
    async def cmd_status(self, event: AstrMessageEvent):
        bind = await self._get_bind(event)
        if bind:
            yield event.plain_result(
                f"🔌 当前API绑定\n\n"
                f"账号：{bind.get('name','?')}\n"
                f"API源：{bind.get('base_name','?')}\n"
                f"模型：{bind.get('model','?')}\n"
                f"Key：{self._mask_key(bind.get('api_key',''))}\n\n"
                "「切换API模型」换模型\n"
                "「添加模型」加模型\n"
                "「切换自定义API」换账号\n"
                "「恢复默认API」切回默认"
            )
        else:
            yield event.plain_result(
                "🔌 当前API绑定\n\n"
                "状态：使用系统默认API\n\n"
                "「注册API」注册新账号\n"
                "「切换自定义API」使用自定义"
            )

    # ==================== 消息拦截器 ====================
    @event_filter.event_message_type(event_filter.EventMessageType.ALL, priority=3)
    async def handle_interactive(self, event: AstrMessageEvent):
        step = self._get_step(event)
        if not step:
            return
        text = event.message_str.strip()
        if not text:
            return

        # 取消操作：任何时候输入"取消"都退出引导流程
        if text == "取消":
            self._clear_step(event)
            yield event.plain_result("✅ 已取消当前操作，恢复默认对话。")
            event.stop_event()
            return

        s = step["step"]
        result = None
        if s.startswith("reg_"):
            result = await self._handle_register(event, text)
        elif s.startswith("sw_"):
            result = await self._handle_switch(event, text)
        elif s.startswith("un_"):
            result = await self._handle_unregister(event, text)
        elif s == "cm_switch_model":
            result = await self._handle_cm_switch_model(event, text, step)
        elif s == "cm_add_model":
            result = await self._handle_cm_add_model(event, text, step)
        if result:
            yield event.plain_result(result)
            event.stop_event()

    # ==================== LLM请求拦截 ====================
    @event_filter.on_llm_request(priority=10)
    async def on_llm_request(self, event, req):
        bind = await self._get_bind(event)
        if not bind:
            return

        pm = getattr(self.context, "provider_manager", None)
        if not pm:
            return

        pid = f"custom_api_{bind.get('name','')}"

        # 判断provider是否已注册
        provider_exists = pid in pm.inst_map and pm.inst_map[pid] is not None

        # 如果provider还没注册 → 尝试创建
        if not provider_exists:
            dp = pm.curr_provider_inst
            if not dp:
                return
            try:
                nc = self._safe_copy_config(dp.provider_config, pid, bind)
                if nc:
                    pt = type(dp)
                    np = pt(provider_config=nc, provider_settings=dp.provider_settings)
                    m = bind.get("model", "")
                    if m:
                        try:
                            np.set_model(m)
                        except Exception:
                            pass
                    pm.inst_map[pid] = np
                    pm.provider_insts.append(np)
                    provider_exists = True

                    # ✅ 首次创建时才持久化到KV（避免每条消息都写库+广播事件）
                    try:
                        await pm.set_provider(pid, ProviderType.CHAT_COMPLETION, event.unified_msg_origin)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"创建自定义provider失败: {e}")

        # ✅ 设 selected_provider（前提是provider确实在inst_map里）
        # 如果不在inst_map里就不设，让 _select_provider 走 get_using_provider 兜底
        if provider_exists:
            event.set_extra("selected_provider", pid)
            if bind.get("model"):
                req.model = bind["model"]
        # ❌ 不调 stop_event()！让框架继续走完LLM调用流程

    def _safe_copy_config(self, provider_config, pid, bind):
        """安全复制config，兼容dict和非dict"""
        try:
            if isinstance(provider_config, dict):
                nc = copy.deepcopy(provider_config)
            elif hasattr(provider_config, "__dict__"):
                nc = copy.deepcopy(provider_config.__dict__)
            else:
                return None
            nc["id"] = pid
            nc["key"] = [bind.get("api_key", "")]
            nc["api_base"] = bind.get("api_base", "")
            return nc
        except Exception:
            return None

    async def _modify_curr_provider(self, bind, req, provider):
        """兜底：直接在当前provider上改"""
        try:
            cfg = provider.provider_config
            if isinstance(cfg, dict):
                cfg["key"] = [bind.get("api_key", "")]
                cfg["api_base"] = bind.get("api_base", "")
            m = bind.get("model", "")
            if m:
                try:
                    provider.set_model(m)
                except Exception:
                    pass
                req.model = m
            logger.info(f"直接修改当前provider: {bind.get('name','')}")
        except Exception as e:
            logger.error(f"修改当前provider失败: {e}")
