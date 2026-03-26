# JobPilot 上线步骤

代码已在: https://github.com/CherishChenCherish/jobpilot

按顺序做以下 5 步，每步都有具体操作。

---

## 第 1 步：Railway 部署后端（5分钟）

1. 打开 https://railway.app → 用 GitHub 登录
2. 点 **"New Project"** → **"Deploy from GitHub Repo"**
3. 选择 `CherishChenCherish/jobpilot`
4. Railway 会问 root directory → 输入 **`backend`**
5. 等部署完成（约2分钟）
6. 点击部署的 service → **Settings** → **Networking** → **Generate Domain**
7. 复制生成的 URL（类似 `jobpilot-backend-xxx.up.railway.app`）

### Railway 添加 PostgreSQL：
1. 在同一个 project 里点 **"New"** → **"Database"** → **"PostgreSQL"**
2. 等创建完成
3. 点击 PostgreSQL service → **Variables** → 复制 `DATABASE_URL`

### Railway 环境变量（在 backend service 的 Variables 里设置）：

| 变量 | 值 |
|------|---|
| `DATABASE_URL` | 从 PostgreSQL 复制（自动连接的话不用手动填） |
| `ANTHROPIC_API_KEY` | 你的 Anthropic API key（从 console.anthropic.com 获取） |
| `FRONTEND_URL` | 先填 `https://jobpilot.vercel.app`（第2步后会确认） |
| `GOOGLE_CLIENT_ID` | 你的 Google OAuth Client ID |
| `STRIPE_SECRET_KEY` | 第3步获取 |
| `STRIPE_WEBHOOK_SECRET` | 第3步获取 |
| `STRIPE_PRICE_ID` | 第3步获取 |

---

## 第 2 步：Vercel 部署前端（3分钟）

1. 打开 https://vercel.com → 用 GitHub 登录
2. 点 **"Add New Project"** → 导入 `CherishChenCherish/jobpilot`
3. **Root Directory** 设为 **`frontend`**
4. **Framework Preset** 选 **Next.js**
5. 点 **Deploy** → 等完成
6. 复制分配的域名（如 `jobpilot-xxx.vercel.app`）

### Vercel 环境变量（在 Settings → Environment Variables）：

| 变量 | 值 |
|------|---|
| `NEXTAUTH_URL` | `https://你的vercel域名` |
| `NEXTAUTH_SECRET` | 在终端运行 `openssl rand -base64 32` 生成 |
| `GOOGLE_CLIENT_ID` | 你的 Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | 你的 Google OAuth Client Secret |
| `NEXT_PUBLIC_API_URL` | `https://你的railway域名`（第1步获得） |

设好后点 **Redeploy** 让环境变量生效。

---

## 第 3 步：Stripe 创建产品（3分钟）

1. 打开 https://stripe.com → 登录（没账号就注册）
2. **Products** → **Add product**
   - Name: `JobPilot Pro`
   - Price: `$12.00 / month` (Recurring)
   - 点 Save
3. 复制 **Price ID**（以 `price_` 开头）
4. **Developers** → **API Keys** → 复制 **Secret key**（以 `sk_test_` 开头）
5. **Developers** → **Webhooks** → **Add endpoint**
   - URL: `https://你的railway域名/api/stripe/webhook`
   - Events 选择:
     - `checkout.session.completed`
     - `customer.subscription.deleted`
     - `invoice.payment_failed`
   - 点 Add endpoint
6. 复制 **Signing secret**（以 `whsec_` 开头）
7. 把这3个值填回 Railway 的环境变量里

---

## 第 4 步：Google OAuth 加生产域名（2分钟）

1. 打开 https://console.cloud.google.com → APIs → Credentials
2. 点击已有的 OAuth Client (`JobPilot`)
3. 在 **Authorized JavaScript origins** 添加:
   - `https://你的vercel域名`
4. 在 **Authorized redirect URIs** 添加:
   - `https://你的vercel域名/api/auth/callback/google`
5. 保存

---

## 第 5 步：验证上线（3分钟）

在浏览器打开你的 Vercel 域名，按顺序检查：

- [ ] 首页加载，深色背景，文字清晰
- [ ] 粘贴一个 Greenhouse URL 到 demo verifier → 得到结果
- [ ] 点 "Try free" → Google 登录成功
- [ ] 上传简历 → profile 显示正确
- [ ] 点 "Find My Jobs" → 看到 jobs → CL 随后出现
- [ ] 下载 Excel → 打开正常
- [ ] 打开浏览器 DevTools Network tab → 没有 API key 泄露

全部通过 = 上线成功！

---

## 上线后要做的

1. Railway 设置自动部署（默认已开启 — push to GitHub 自动部署）
2. Vercel 同理
3. 考虑买自定义域名（如 jobpilot.app）
4. 在 Product Hunt / Reddit 发布
