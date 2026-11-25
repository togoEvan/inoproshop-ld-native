# 新手操作手册：把仓库传到 GitHub

> 你不需要懂 git 命令，也不需要创建 PAT（访问令牌）。
> 只需要：**① 网页上点几下建空仓库 → ② 在弹出的浏览器窗口登录一次**。

---

## 准备工作（确认一件事）

你需要有一个 GitHub 账号。没有的话先注册：https://github.com/signup

---

## 第 1 步：网页上创建空仓库（约 30 秒）

1. 用浏览器打开这个链接（仓库名和可见性已经帮你填好了）：

   **https://github.com/new?name=inoproshop-ld-native&visibility=public**

2. 页面上只需要确认两件事：
   - **Repository name** 是 `inoproshop-ld-native` ✅（链接已填）
   - **Public** 被选中 ✅（链接已填）

3. ⚠️ **重要**：下面这几个勾**一个都不要勾**：
   - ❌ Add a README file
   - ❌ Add .gitignore
   - ❌ Choose a license

   因为我们本地已经有这些文件了，勾了会造成冲突。

4. 点最下面的绿色按钮 **Create repository**

5. 创建成功后，页面会跳到一个"快速设置"页面，显示一堆命令。
   **你什么都不用做，也不用复制任何命令**，直接告诉我「建好了」即可。

---

## 第 2 步：我来推送，你登录一次

你告诉我「建好了」之后，我会在后台执行推送。

这时会**自动弹出一个窗口**（Git Credential Manager 的登录窗），你按下面操作：

1. 窗口里会出现 **Sign in with your browser** 之类的按钮 → 点它
2. 浏览器会自动打开 GitHub 授权页面
3. 点 **Authorize** / **授权** 按钮
4. 浏览器显示 "Authentication Succeeded" 后，可以关掉那个窗口

推送就完成了。

> 这次登录后，凭据会保存在 Windows 凭据管理器里。
> **以后所有推送都不需要再登录**，我直接 `git push` 就行。

---

## 第 3 步：验证

推送完成后，打开你的仓库地址：

**https://github.com/<你的用户名>/inoproshop-ld-native**

应该能看到 README.md 的内容直接显示在页面上，以及 27 个文件。

---

## 常见问题

### Q: 弹出的窗口我没看到 / 关掉了

没关系，告诉我一声，我重新触发一次推送。

### Q: 浏览器授权页面显示 "This application is not authorized"

你的 GitHub 账号可能设置了组织 SSO 限制。在授权页面上找到组织名称旁边的
**Grant** / **授权** 按钮点一下。

### Q: 我点了创建仓库，但页面提示名字已被占用

说明 `inoproshop-ld-native` 这个名字已经被别人用了。告诉我，我换个名字
（比如 `inoproshop-ld-native-toolkit`）重新走一遍。

### Q: 我不想用浏览器登录，还是想用 PAT

可以。告诉我，我给你一份「创建 PAT 的逐步截图式说明」。

---

## 附：为什么不需要 PAT

Git 有一个叫 **Credential Manager**（凭据管理器）的组件，它支持用浏览器
OAuth 的方式登录 GitHub。比手动创建 PAT 简单得多，也更安全（不需要把
一长串字符复制粘贴到聊天里）。

你这台机器上已经装了它，所以直接用就行。
