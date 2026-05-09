# 🔌 史诗之API注册器

> 作者：Mon3tr | 版本：v1.0 | AstrBot >=3.0 | aiocqhttp | 让每位干员用自己的API额度

## 功能介绍

让用户注册自己的API账号，绑定后自动使用自己的API额度和模型，无需每次手动切换。支持LLM请求自动拦截，切换后所有对话无缝使用自定义API。

---

## 使用方法

### 📝 注册API账号

私聊发送 **注册API**，然后按引导一步一步操作：

```
你: 注册API
插件: 🔌 自定义API注册
      可用功能：
        ① 注册API - 绑定你的API账号
        ② 切换自定义API - 切换到已注册账号
        ③ 切换API模型 - 切换当前账号的模型
        ④ 添加模型 - 为当前账号添加模型
        ⑤ 测试API - 测试当前绑定的API连接
        ⑥ 注销API - 注销账号
        ⑦ 恢复默认API - 切回系统默认
        ⑧ API状态 - 查看当前绑定
      
      请输入账号名（发送「取消」可随时退出）：
你: zhangsan
插件: 请输入密码：
你: mypass123
插件: 请输入API Key：
你: sk-xxxxxxxxxxxxxxxx
插件: 请选择API源：
  1. DeepSeek
  2. 智谱GLM
  3. 硅基流动
  4. 阿里百炼
  5. OpenAI
  6. 月之暗面
  7. 零一万物
  8. Groq
  9. Together AI
  10. 自定义（输入完整URL）
  请输入编号或直接输入URL：
你: 1
插件: ✅ 已选择：DeepSeek（https://api.deepseek.com/v1）
  请输入可用模型列表（逗号分隔）：
  例如：deepseek-v4-flash,deepseek-v4-pro
你: deepseek-v4-flash,deepseek-v4-pro
插件: ✅ 注册成功！
  
  账号：zhangsan
  API源：DeepSeek
  模型：
    deepseek-v4-flash
    deepseek-v4-pro
  
  发送「切换自定义API」开始使用
```

### 🔄 切换自定义API

私聊发送 **切换自定义API**，输入账号密码后选择模型即可：

```
你: 切换自定义API
插件: 请输入账号：
你: zhangsan
插件: 请输入密码：
你: mypass123
插件: ✅ 密码正确！API源：DeepSeek
  
  请选择模型：
  1. deepseek-v4-flash
  2. deepseek-v4-pro
  
  请输入编号：
你: 2
插件: ✅ 已切换到自定义API！
  
  账号：zhangsan
  API源：DeepSeek
  模型：deepseek-v4-pro
  
  发送「API状态」查看详情
  发送「恢复默认API」切回系统默认
```

### 🔄 切换API模型

已切换到自定义API后，想换模型无需重新输密码：

```
你: 切换API模型
插件: 🔄 切换模型 - 账号：zhangsan
  
  可用模型：
  1. deepseek-v4-flash
  2. deepseek-v4-pro
  
  请输入编号：
你: 1
插件: ✅ 已切换模型为：deepseek-v4-flash
```

### ➕ 添加模型

给已注册的账号添加更多模型：

```
你: 添加模型
插件: 📝 为账号「zhangsan」添加模型
  
  请输入模型名（多个用逗号分隔）：
  例：deepseek-v4-flash,deepseek-v4-pro
你: deepseek-v4-ultra,deepseek-r1
插件: ✅ 已添加模型：
  deepseek-v4-ultra
  deepseek-r1
  
  发送「切换API模型」选择使用
```

### 🧪 测试API

测试当前绑定的API是否可用：

```
你: 测试API
插件: ⏳ 正在测试API连接，请稍候...
插件: ✅ API连接成功！
  
  API源：DeepSeek
  模型：deepseek-v4-flash
  响应：Hi! How can I help you today?
  耗时：1.23秒
```

测试失败时会返回详细错误信息：

| 错误码 | 含义 |
|--------|------|
| 401 | API Key无效 |
| 404 | 模型不存在 |
| 429 | 请求过于频繁 |
| 503 | API服务暂不可用 |
| 连接失败 | API地址错误或网络不通 |
| 超时 | API响应超过30秒 |

### 🗑️ 注销API账号

私聊发送 **注销API**，需验证密码并二次确认：

```
你: 注销API
插件: 请输入要注销的账号名：
你: zhangsan
插件: 请输入密码确认身份：
你: mypass123
插件: ⚠️ 确定要注销吗？所有数据将被删除且不可恢复。
  输入「确认注销」继续，输入其他内容取消：
你: 确认注销
插件: ✅ 账号 zhangsan 已注销。已恢复为默认API。
```

### ⏮️ 恢复默认API

私聊发送 **恢复默认API**，直接切回系统默认，无需验证。

### 📊 查看API状态

私聊或群聊发送 **API状态**，查看当前绑定信息（API Key脱敏显示）：

```
🔌 当前API绑定

账号：zhangsan
API源：DeepSeek
模型：deepseek-v4-flash
Key：sk-xx...xxxx

「切换API模型」换模型
「添加模型」加模型
「切换自定义API」换账号
「恢复默认API」切回默认
```

未切换时显示：
```
🔌 当前API绑定

状态：使用系统默认API

「注册API」注册新账号
「切换自定义API」使用自定义
```

---

## 预设API源

| 编号 | 名称 | API Base |
|------|------|----------|
| 1 | DeepSeek | https://api.deepseek.com/v1 |
| 2 | 智谱GLM | https://open.bigmodel.cn/api/paas/v4 |
| 3 | 硅基流动 | https://api.siliconflow.cn/v1 |
| 4 | 阿里百炼 | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| 5 | OpenAI | https://api.openai.com/v1 |
| 6 | 月之暗面 | https://api.moonshot.cn/v1 |
| 7 | 零一万物 | https://api.lingyiwanwu.com/v1 |
| 8 | Groq | https://api.groq.com/openai/v1 |
| 9 | Together AI | https://api.together.xyz/v1 |

> 可通过插件配置 `preset_bases` 添加自定义预设源。

---

## 底层机制

### LLM请求自动拦截

切换自定义API后，插件会自动拦截LLM请求，动态创建临时的Provider实例，将API Key、Base和模型注入到请求中。整个过程对用户透明，无需手动配置。

### 会话状态机

所有引导流程（注册/切换/注销等）使用状态机管理，30分钟无操作自动超时清理，任意步骤可输入「取消」退出。

---

## 安全说明

- ⚠️ 所有操作仅限私聊，群聊不响应
- 🔒 密码使用SHA256哈希存储，不明文保存
- 🔑 API Key脱敏显示（sk-xxxx...xxxx）
- 🚫 全程插件状态机拦截，不经过LLM处理
- 💾 账号信息和绑定状态持久化存储，重启不丢失

---

## 命令速查

| 命令 | 说明 | 场景 |
|------|------|------|
| 注册API | 引导式注册新账号 | 仅私聊 |
| 切换自定义API | 切换到已注册账号 | 仅私聊 |
| 切换API模型 | 切换当前账号的模型 | 仅私聊 |
| 添加模型 | 为当前账号添加模型 | 仅私聊 |
| 测试API | 测试当前绑定的API连接 | 仅私聊 |
| 注销API | 注销并删除账号 | 仅私聊 |
| 恢复默认API | 切回系统默认API | 仅私聊 |
| API状态 | 查看当前绑定状态 | 私聊/群聊 |
| 低功耗模式 | 一键禁用所有插件注入，仅保留人格+用户消息 | 私聊/群聊 |

---

## 注意事项

- 首次使用需重启AstrBot后生效
- 同一账号名不可重复注册
- 注销账号需输入「确认注销」二次确认
- 切换后所有对话自动使用自定义API，无需重复切换
- 密码至少4个字符，账号名至少2个字符
- 引导流程中随时可输入「取消」退出
